use crate::runtime_manager::{owner_data_root, RuntimeManager, RuntimeStatus};
use serde::Serialize;
use std::{
    collections::{BTreeMap, BTreeSet},
    fs,
    process,
    sync::atomic::{AtomicBool, Ordering},
    thread,
    time::{Duration, SystemTime, UNIX_EPOCH},
};
use tauri::AppHandle;

const OBSERVATION_SECONDS: u64 = 60;
const SAMPLE_INTERVAL: Duration = Duration::from_millis(250);
const FORBIDDEN_SHELLS: [&str; 4] = ["powershell.exe", "pwsh.exe", "cmd.exe", "conhost.exe"];
static ACCEPTANCE_RUNNING: AtomicBool = AtomicBool::new(false);

#[derive(Clone, Debug)]
struct ProcessRecord {
    pid: u32,
    parent_pid: u32,
    name: String,
}

#[derive(Clone, Debug, Serialize, PartialEq, Eq, PartialOrd, Ord)]
pub struct ProcessObservation {
    pub pid: u32,
    pub parent_pid: u32,
    pub name: String,
    pub relation: String,
}

#[derive(Clone, Debug, Serialize)]
pub struct AcceptancePhase {
    pub name: String,
    pub duration_seconds: u64,
    pub runtime_pid: Option<u32>,
    pub authenticated: bool,
    pub forbidden_descendant_count: usize,
    pub external_shell_count: usize,
}

#[derive(Clone, Debug, Serialize)]
pub struct WindowlessAcceptanceReport {
    pub schema_version: u32,
    pub started_at_ms: u128,
    pub finished_at_ms: u128,
    pub passed: bool,
    pub desktop_pid: u32,
    pub initial_runtime_pid: Option<u32>,
    pub restarted_runtime_pid: Option<u32>,
    pub authenticated_before: bool,
    pub authenticated_after: bool,
    pub forbidden_descendants: Vec<ProcessObservation>,
    pub external_shell_processes: Vec<ProcessObservation>,
    pub phases: Vec<AcceptancePhase>,
    pub failure: Option<String>,
    pub report_path: String,
}

struct RunningGuard;

impl RunningGuard {
    fn acquire() -> Result<Self, String> {
        ACCEPTANCE_RUNNING
            .compare_exchange(false, true, Ordering::AcqRel, Ordering::Acquire)
            .map_err(|_| "桌面零 Shell 验收正在运行，请等待当前验收结束".to_string())?;
        Ok(Self)
    }
}

impl Drop for RunningGuard {
    fn drop(&mut self) {
        ACCEPTANCE_RUNNING.store(false, Ordering::Release);
    }
}

fn now_ms() -> u128 {
    SystemTime::now()
        .duration_since(UNIX_EPOCH)
        .unwrap_or_default()
        .as_millis()
}

fn normalized_process_name(value: &str) -> String {
    value.trim().to_ascii_lowercase()
}

fn is_forbidden_shell(value: &str) -> bool {
    let name = normalized_process_name(value);
    FORBIDDEN_SHELLS.contains(&name.as_str())
}

fn is_descendant_of(pid: u32, ancestor: u32, processes: &BTreeMap<u32, ProcessRecord>) -> bool {
    let mut current = pid;
    let mut visited = BTreeSet::new();
    while let Some(process) = processes.get(&current) {
        if !visited.insert(current) {
            return false;
        }
        if process.parent_pid == ancestor {
            return true;
        }
        if process.parent_pid == 0 || process.parent_pid == current {
            return false;
        }
        current = process.parent_pid;
    }
    false
}

#[cfg(target_os = "windows")]
fn process_snapshot() -> Result<BTreeMap<u32, ProcessRecord>, String> {
    use std::{ffi::c_void, mem::size_of};

    const TH32CS_SNAPPROCESS: u32 = 0x0000_0002;
    const INVALID_HANDLE_VALUE: *mut c_void = -1_isize as *mut c_void;

    #[repr(C)]
    struct ProcessEntry32W {
        size: u32,
        usage: u32,
        process_id: u32,
        default_heap_id: usize,
        module_id: u32,
        threads: u32,
        parent_process_id: u32,
        priority_class_base: i32,
        flags: u32,
        executable: [u16; 260],
    }

    #[link(name = "Kernel32")]
    extern "system" {
        fn CreateToolhelp32Snapshot(flags: u32, process_id: u32) -> *mut c_void;
        fn Process32FirstW(snapshot: *mut c_void, entry: *mut ProcessEntry32W) -> i32;
        fn Process32NextW(snapshot: *mut c_void, entry: *mut ProcessEntry32W) -> i32;
        fn CloseHandle(handle: *mut c_void) -> i32;
    }

    let snapshot = unsafe { CreateToolhelp32Snapshot(TH32CS_SNAPPROCESS, 0) };
    if snapshot == INVALID_HANDLE_VALUE {
        return Err("无法读取 Windows 进程快照".to_string());
    }

    let mut entry = ProcessEntry32W {
        size: size_of::<ProcessEntry32W>() as u32,
        usage: 0,
        process_id: 0,
        default_heap_id: 0,
        module_id: 0,
        threads: 0,
        parent_process_id: 0,
        priority_class_base: 0,
        flags: 0,
        executable: [0; 260],
    };
    let mut records = BTreeMap::new();
    let mut available = unsafe { Process32FirstW(snapshot, &mut entry) } != 0;
    while available {
        let end = entry
            .executable
            .iter()
            .position(|value| *value == 0)
            .unwrap_or(entry.executable.len());
        let name = String::from_utf16_lossy(&entry.executable[..end]);
        records.insert(
            entry.process_id,
            ProcessRecord {
                pid: entry.process_id,
                parent_pid: entry.parent_process_id,
                name,
            },
        );
        available = unsafe { Process32NextW(snapshot, &mut entry) } != 0;
    }
    unsafe {
        CloseHandle(snapshot);
    }
    Ok(records)
}

#[cfg(not(target_os = "windows"))]
fn process_snapshot() -> Result<BTreeMap<u32, ProcessRecord>, String> {
    Err("桌面零 Shell 验收仅支持 Windows 安装版".to_string())
}

fn sample_processes(
    desktop_pid: u32,
    forbidden_descendants: &mut BTreeSet<ProcessObservation>,
    external_shells: &mut BTreeSet<ProcessObservation>,
) -> Result<(), String> {
    let processes = process_snapshot()?;
    for process in processes.values().filter(|item| is_forbidden_shell(&item.name)) {
        let descendant = is_descendant_of(process.pid, desktop_pid, &processes);
        let observation = ProcessObservation {
            pid: process.pid,
            parent_pid: process.parent_pid,
            name: normalized_process_name(&process.name),
            relation: if descendant {
                "lingji_descendant".to_string()
            } else {
                "external".to_string()
            },
        };
        if descendant {
            forbidden_descendants.insert(observation);
        } else {
            external_shells.insert(observation);
        }
    }
    Ok(())
}

fn observe_phase(
    name: &str,
    runtime: &RuntimeStatus,
    desktop_pid: u32,
    forbidden_descendants: &mut BTreeSet<ProcessObservation>,
    external_shells: &mut BTreeSet<ProcessObservation>,
) -> Result<AcceptancePhase, String> {
    let started = now_ms();
    while now_ms().saturating_sub(started) < u128::from(OBSERVATION_SECONDS * 1000) {
        sample_processes(desktop_pid, forbidden_descendants, external_shells)?;
        thread::sleep(SAMPLE_INTERVAL);
    }
    Ok(AcceptancePhase {
        name: name.to_string(),
        duration_seconds: OBSERVATION_SECONDS,
        runtime_pid: runtime.pid,
        authenticated: runtime.healthy,
        forbidden_descendant_count: forbidden_descendants.len(),
        external_shell_count: external_shells.len(),
    })
}

fn persist_report(report: &WindowlessAcceptanceReport) -> Result<String, String> {
    let root = owner_data_root()?;
    let directory = root.join("reports").join("desktop-acceptance");
    fs::create_dir_all(&directory)
        .map_err(|error| format!("无法创建桌面验收报告目录：{error}"))?;
    let path = directory.join(format!("zero-shell-{}.json", report.started_at_ms));
    let payload = serde_json::to_vec_pretty(report)
        .map_err(|error| format!("无法生成桌面验收报告：{error}"))?;
    fs::write(&path, payload).map_err(|error| format!("无法保存桌面验收报告：{error}"))?;
    Ok(path.display().to_string())
}

pub fn run(app: &AppHandle, manager: &RuntimeManager) -> Result<WindowlessAcceptanceReport, String> {
    let _guard = RunningGuard::acquire()?;
    let started_at_ms = now_ms();
    let desktop_pid = process::id();
    let initial = manager.status(app)?;
    if !initial.healthy || !initial.managed {
        return Err("运行零 Shell 验收前，必须先让受管 LingJi Core 处于认证健康状态".to_string());
    }

    let mut forbidden_descendants = BTreeSet::new();
    let mut external_shells = BTreeSet::new();
    let mut phases = Vec::new();
    phases.push(observe_phase(
        "启动后静置观察",
        &initial,
        desktop_pid,
        &mut forbidden_descendants,
        &mut external_shells,
    )?);

    let restarted = manager.restart(app)?;
    let mut failure = None;
    if !restarted.healthy || !restarted.managed {
        failure = Some("Core 重启后未恢复到受管认证健康状态".to_string());
    }
    phases.push(observe_phase(
        "Core 重启后观察",
        &restarted,
        desktop_pid,
        &mut forbidden_descendants,
        &mut external_shells,
    )?);

    let final_status = manager.status(app)?;
    if !final_status.healthy || !final_status.managed {
        failure = Some("验收结束时 Core 不是受管认证健康状态".to_string());
    }
    if !forbidden_descendants.is_empty() {
        failure = Some("LingJi 进程树中检测到 PowerShell、CMD 或 Console Host".to_string());
    }

    let mut report = WindowlessAcceptanceReport {
        schema_version: 1,
        started_at_ms,
        finished_at_ms: now_ms(),
        passed: failure.is_none(),
        desktop_pid,
        initial_runtime_pid: initial.pid,
        restarted_runtime_pid: restarted.pid,
        authenticated_before: initial.healthy,
        authenticated_after: final_status.healthy,
        forbidden_descendants: forbidden_descendants.into_iter().collect(),
        external_shell_processes: external_shells.into_iter().collect(),
        phases,
        failure,
        report_path: String::new(),
    };
    report.report_path = persist_report(&report)?;
    Ok(report)
}

#[cfg(test)]
mod tests {
    use super::*;

    fn record(pid: u32, parent_pid: u32, name: &str) -> ProcessRecord {
        ProcessRecord {
            pid,
            parent_pid,
            name: name.to_string(),
        }
    }

    #[test]
    fn detects_nested_descendants_without_cycles() {
        let processes = BTreeMap::from([
            (10, record(10, 1, "LingJi.exe")),
            (20, record(20, 10, "lingji-core.exe")),
            (30, record(30, 20, "powershell.exe")),
        ]);
        assert!(is_descendant_of(30, 10, &processes));
        assert!(!is_descendant_of(10, 10, &processes));
    }

    #[test]
    fn recognizes_only_forbidden_shell_names() {
        assert!(is_forbidden_shell("PowerShell.EXE"));
        assert!(is_forbidden_shell("conhost.exe"));
        assert!(!is_forbidden_shell("lingji-core.exe"));
        assert!(!is_forbidden_shell("taskkill.exe"));
    }
}
