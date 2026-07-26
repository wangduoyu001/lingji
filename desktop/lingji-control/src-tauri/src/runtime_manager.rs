use serde::{Deserialize, Serialize};
use std::{
    env,
    fs::{self, File, OpenOptions},
    io::{Read, Write},
    net::{IpAddr, Ipv4Addr, SocketAddr, TcpStream},
    path::{Path, PathBuf},
    process::{Child, Command, Stdio},
    sync::{Arc, Mutex},
    thread,
    time::{Duration, SystemTime, UNIX_EPOCH},
};
use tauri::{AppHandle, Manager, State};

#[cfg(target_os = "windows")]
use std::os::windows::process::CommandExt;

#[cfg(target_os = "windows")]
const CREATE_NO_WINDOW: u32 = 0x0800_0000;
const CONTROL_PORT: u16 = 8766;
const STARTUP_ATTEMPTS: u32 = 3;
const STARTUP_POLLS: usize = 80;
const STARTUP_POLL_DELAY: Duration = Duration::from_millis(250);
const ADOPTION_GRACE_MS: u128 = 30_000;
const STOP_POLLS: usize = 50;
const STOP_POLL_DELAY: Duration = Duration::from_millis(100);

#[derive(Clone, Debug, Serialize)]
pub struct RuntimeStatus {
    pub state: String,
    pub healthy: bool,
    pub managed: bool,
    pub pid: Option<u32>,
    pub started_at_ms: Option<u128>,
    pub restart_count: u32,
    pub last_exit_code: Option<i32>,
    pub last_error: Option<String>,
    pub binary_available: bool,
    pub data_root_display: String,
    pub log_path_display: String,
    pub host: String,
    pub port: u16,
}

#[derive(Clone, Debug, Deserialize)]
struct PackagedRuntimeIdentity {
    schema_version: u32,
    mode: String,
    pid: u32,
    instance_id: String,
    started_at_ms: u128,
    host: String,
    port: u16,
}

#[derive(Serialize)]
struct StopRequest<'a> {
    schema_version: u32,
    instance_id: &'a str,
    requested_at_ms: u128,
}

struct RuntimeInner {
    child: Option<Child>,
    instance_id: Option<String>,
    state: String,
    managed: bool,
    pid: Option<u32>,
    started_at_ms: Option<u128>,
    restart_count: u32,
    last_exit_code: Option<i32>,
    last_error: Option<String>,
}

impl Default for RuntimeInner {
    fn default() -> Self {
        Self {
            child: None,
            instance_id: None,
            state: "stopped".to_string(),
            managed: false,
            pid: None,
            started_at_ms: None,
            restart_count: 0,
            last_exit_code: None,
            last_error: None,
        }
    }
}

#[derive(Clone, Default)]
pub struct RuntimeManager {
    inner: Arc<Mutex<RuntimeInner>>,
}

pub fn owner_data_root() -> Result<PathBuf, String> {
    if let Ok(value) = env::var("LINGJI_OWNER_DATA_ROOT") {
        let path = PathBuf::from(value);
        if path.is_absolute() {
            return Ok(path);
        }
    }
    for variable in ["LOCALAPPDATA", "APPDATA"] {
        if let Ok(value) = env::var(variable) {
            let path = PathBuf::from(value).join("LingJi");
            if path.is_absolute() {
                return Ok(path);
            }
        }
    }
    if let Ok(value) = env::var("USERPROFILE") {
        let path = PathBuf::from(value).join(".lingji");
        if path.is_absolute() {
            return Ok(path);
        }
    }
    Err("Unable to resolve the owner-local LingJi data directory".to_string())
}

fn now_ms() -> u128 {
    SystemTime::now()
        .duration_since(UNIX_EPOCH)
        .unwrap_or_default()
        .as_millis()
}

fn display_paths(root: &Path) -> (String, String) {
    let display_root = if env::var("LOCALAPPDATA")
        .ok()
        .is_some_and(|value| root.starts_with(PathBuf::from(value)))
    {
        "%LOCALAPPDATA%\\LingJi".to_string()
    } else if env::var("APPDATA")
        .ok()
        .is_some_and(|value| root.starts_with(PathBuf::from(value)))
    {
        "%APPDATA%\\LingJi".to_string()
    } else {
        "owner-local LingJi data".to_string()
    };
    let log = format!("{}\\logs\\runtime-sidecar.log", display_root);
    (display_root, log)
}

fn runtime_binary_candidates(app: &AppHandle) -> Vec<PathBuf> {
    let mut candidates = Vec::new();
    #[cfg(debug_assertions)]
    if let Ok(explicit) = env::var("LINGJI_RUNTIME_BINARY") {
        candidates.push(PathBuf::from(explicit));
    }
    if let Ok(resource_dir) = app.path().resource_dir() {
        candidates.push(resource_dir.join("lingji-core.exe"));
        candidates.push(resource_dir.join("binaries").join("lingji-core.exe"));
    }
    if let Ok(executable) = env::current_exe() {
        if let Some(parent) = executable.parent() {
            candidates.push(parent.join("lingji-core.exe"));
            candidates.push(parent.join("resources").join("lingji-core.exe"));
        }
    }
    candidates
}

fn runtime_binary(app: &AppHandle) -> Option<PathBuf> {
    runtime_binary_candidates(app).into_iter().find(|candidate| {
        candidate.is_file()
            && candidate
                .parent()
                .is_some_and(|parent| parent.join("lingji_core_lib").is_dir())
    })
}

fn token_path(root: &Path) -> PathBuf {
    root.join("storage").join("control_api_token")
}

fn runtime_dir(root: &Path) -> PathBuf {
    root.join("runtime")
}

fn identity_path(root: &Path) -> PathBuf {
    runtime_dir(root).join("sidecar-state.json")
}

fn stop_request_path(root: &Path) -> PathBuf {
    runtime_dir(root).join("sidecar-stop-request.json")
}

fn read_identity(root: &Path) -> Option<PackagedRuntimeIdentity> {
    let bytes = fs::read(identity_path(root)).ok()?;
    let identity: PackagedRuntimeIdentity = serde_json::from_slice(&bytes).ok()?;
    if identity.schema_version != 1
        || identity.mode != "packaged_sidecar"
        || identity.pid == 0
        || identity.instance_id.trim().is_empty()
        || identity.host != "127.0.0.1"
        || identity.port != CONTROL_PORT
    {
        return None;
    }
    Some(identity)
}

fn write_stop_request(root: &Path, instance_id: &str) -> Result<(), String> {
    let directory = runtime_dir(root);
    fs::create_dir_all(&directory)
        .map_err(|error| format!("Unable to create runtime directory: {error}"))?;
    let path = stop_request_path(root);
    let temporary = path.with_extension("json.tmp");
    let payload = serde_json::to_vec(&StopRequest {
        schema_version: 1,
        instance_id,
        requested_at_ms: now_ms(),
    })
    .map_err(|error| format!("Unable to encode runtime stop request: {error}"))?;
    fs::write(&temporary, payload)
        .map_err(|error| format!("Unable to write runtime stop request: {error}"))?;
    fs::rename(&temporary, &path)
        .map_err(|error| format!("Unable to activate runtime stop request: {error}"))?;
    Ok(())
}

fn clear_lifecycle_files(root: &Path, expected_instance: Option<&str>) {
    if let Some(expected) = expected_instance {
        if read_identity(root)
            .as_ref()
            .is_some_and(|identity| identity.instance_id != expected)
        {
            return;
        }
    }
    let _ = fs::remove_file(identity_path(root));
    let _ = fs::remove_file(stop_request_path(root));
}

fn identity_is_recent(identity: &PackagedRuntimeIdentity) -> bool {
    now_ms().saturating_sub(identity.started_at_ms) <= ADOPTION_GRACE_MS
}

fn open_runtime_log(root: &Path) -> Result<File, String> {
    let log_dir = root.join("logs");
    fs::create_dir_all(&log_dir).map_err(|error| format!("Unable to create runtime log directory: {error}"))?;
    OpenOptions::new()
        .create(true)
        .append(true)
        .open(log_dir.join("runtime-sidecar.log"))
        .map_err(|error| format!("Unable to open runtime log: {error}"))
}

fn authenticated_health(root: &Path) -> bool {
    let token = match fs::read_to_string(token_path(root)) {
        Ok(value) if !value.trim().is_empty() => value.trim().to_string(),
        _ => return false,
    };
    let address = SocketAddr::new(IpAddr::V4(Ipv4Addr::LOCALHOST), CONTROL_PORT);
    let mut stream = match TcpStream::connect_timeout(&address, Duration::from_millis(450)) {
        Ok(stream) => stream,
        Err(_) => return false,
    };
    let _ = stream.set_read_timeout(Some(Duration::from_millis(650)));
    let _ = stream.set_write_timeout(Some(Duration::from_millis(650)));
    let request = format!(
        "GET /api/runtime/ping HTTP/1.1\r\nHost: 127.0.0.1:{CONTROL_PORT}\r\nX-LingJi-Token: {token}\r\nConnection: close\r\n\r\n"
    );
    if stream.write_all(request.as_bytes()).is_err() {
        return false;
    }
    let mut response = [0_u8; 512];
    let count = match stream.read(&mut response) {
        Ok(count) => count,
        Err(_) => return false,
    };
    let status = String::from_utf8_lossy(&response[..count]);
    status.starts_with("HTTP/1.1 200") || status.starts_with("HTTP/1.0 200")
}

fn force_kill_pid(pid: u32) {
    #[cfg(target_os = "windows")]
    {
        let mut command = Command::new("taskkill");
        command
            .args(["/PID", &pid.to_string(), "/T", "/F"])
            .creation_flags(CREATE_NO_WINDOW);
        let _ = command.status();
    }
    #[cfg(not(target_os = "windows"))]
    {
        let _ = Command::new("kill")
            .args(["-TERM", &pid.to_string()])
            .status();
    }
}

impl RuntimeManager {
    fn snapshot(&self, app: &AppHandle, root: &Path, healthy: bool) -> RuntimeStatus {
        let binary_available = runtime_binary(app).is_some();
        let (data_root_display, log_path_display) = display_paths(root);
        let inner = self.inner.lock().unwrap_or_else(|poisoned| poisoned.into_inner());
        RuntimeStatus {
            state: inner.state.clone(),
            healthy,
            managed: inner.managed,
            pid: inner.pid,
            started_at_ms: inner.started_at_ms,
            restart_count: inner.restart_count,
            last_exit_code: inner.last_exit_code,
            last_error: inner.last_error.clone(),
            binary_available,
            data_root_display,
            log_path_display,
            host: "127.0.0.1".to_string(),
            port: CONTROL_PORT,
        }
    }

    fn refresh_child(&self) {
        let mut inner = self.inner.lock().unwrap_or_else(|poisoned| poisoned.into_inner());
        let exit = inner
            .child
            .as_mut()
            .and_then(|child| child.try_wait().ok().flatten());
        if let Some(status) = exit {
            inner.child = None;
            inner.pid = None;
            inner.instance_id = None;
            inner.managed = false;
            inner.last_exit_code = status.code();
            if inner.state != "stopped" && inner.state != "stopping" {
                inner.state = "failed".to_string();
                inner.last_error = Some(format!(
                    "LingJi runtime exited with code {}",
                    status.code().map_or_else(|| "unknown".to_string(), |code| code.to_string())
                ));
            }
        }
    }

    fn adopt_identity(inner: &mut RuntimeInner, identity: &PackagedRuntimeIdentity, state: &str) {
        inner.state = state.to_string();
        inner.managed = true;
        inner.pid = Some(identity.pid);
        inner.started_at_ms = Some(identity.started_at_ms);
        inner.instance_id = Some(identity.instance_id.clone());
    }

    pub fn status(&self, app: &AppHandle) -> Result<RuntimeStatus, String> {
        let root = owner_data_root()?;
        self.refresh_child();
        let healthy = authenticated_health(&root);
        let identity = read_identity(&root);
        {
            let mut inner = self.inner.lock().unwrap_or_else(|poisoned| poisoned.into_inner());
            if healthy {
                if let Some(identity) = identity.as_ref() {
                    Self::adopt_identity(&mut inner, identity, "healthy");
                } else if inner.child.is_some() {
                    inner.state = "healthy".to_string();
                    inner.managed = true;
                } else {
                    inner.state = "external".to_string();
                    inner.managed = false;
                    inner.pid = None;
                    inner.started_at_ms = None;
                    inner.instance_id = None;
                }
                inner.last_error = None;
            } else if inner.child.is_some() {
                if inner.state == "healthy" {
                    inner.state = "unhealthy".to_string();
                }
            } else if let Some(identity) = identity.as_ref() {
                if inner.state != "failed" && identity_is_recent(identity) {
                    Self::adopt_identity(&mut inner, identity, "starting");
                } else {
                    clear_lifecycle_files(&root, Some(&identity.instance_id));
                    if inner.state != "failed" {
                        inner.state = "stopped".to_string();
                        inner.last_error = None;
                    }
                    inner.managed = false;
                    inner.pid = None;
                    inner.started_at_ms = None;
                    inner.instance_id = None;
                }
            } else if inner.state != "failed" {
                inner.state = "stopped".to_string();
                inner.managed = false;
                inner.pid = None;
                inner.started_at_ms = None;
                inner.instance_id = None;
            }
        }
        Ok(self.snapshot(app, &root, healthy))
    }

    fn wait_for_health(&self, app: &AppHandle, root: &Path) -> Result<RuntimeStatus, String> {
        for _ in 0..STARTUP_POLLS {
            thread::sleep(STARTUP_POLL_DELAY);
            self.refresh_child();
            if authenticated_health(root) {
                return self.status(app);
            }
            let managed_process_exists = {
                let inner = self.inner.lock().unwrap_or_else(|poisoned| poisoned.into_inner());
                inner.child.is_some() || read_identity(root).is_some()
            };
            if !managed_process_exists {
                return self.status(app);
            }
        }
        self.stop_managed_process(root);
        let mut inner = self.inner.lock().unwrap_or_else(|poisoned| poisoned.into_inner());
        inner.state = "failed".to_string();
        inner.last_error = Some("LingJi runtime did not become healthy within 20 seconds".to_string());
        drop(inner);
        Ok(self.snapshot(app, root, false))
    }

    fn spawn_once(&self, app: &AppHandle) -> Result<RuntimeStatus, String> {
        let root = owner_data_root()?;
        fs::create_dir_all(&root).map_err(|error| format!("Unable to create LingJi data root: {error}"))?;
        let current = self.status(app)?;
        if current.healthy {
            return Ok(current);
        }
        if current.managed && current.state == "starting" {
            return self.wait_for_health(app, &root);
        }
        let has_child = {
            self.inner
                .lock()
                .unwrap_or_else(|poisoned| poisoned.into_inner())
                .child
                .is_some()
        };
        if has_child {
            return Ok(self.snapshot(app, &root, false));
        }

        clear_lifecycle_files(&root, None);
        let binary = runtime_binary(app).ok_or_else(|| {
            "Packaged LingJi runtime is unavailable. Install a Sidecar-enabled Desktop build.".to_string()
        })?;
        let log = open_runtime_log(&root)?;
        let stderr = log
            .try_clone()
            .map_err(|error| format!("Unable to clone runtime log handle: {error}"))?;
        let port = CONTROL_PORT.to_string();
        let mut command = Command::new(&binary);
        command
            .arg("--data-root")
            .arg(root.as_os_str())
            .arg("--host")
            .arg("127.0.0.1")
            .arg("--port")
            .arg(&port)
            .current_dir(&root)
            .env("LINGJI_OWNER_DATA_ROOT", &root)
            .stdout(Stdio::from(log))
            .stderr(Stdio::from(stderr));
        #[cfg(target_os = "windows")]
        command.creation_flags(CREATE_NO_WINDOW);

        let child = command
            .spawn()
            .map_err(|error| format!("Unable to start packaged LingJi runtime: {error}"))?;
        let pid = child.id();
        {
            let mut inner = self.inner.lock().unwrap_or_else(|poisoned| poisoned.into_inner());
            inner.child = Some(child);
            inner.state = "starting".to_string();
            inner.managed = true;
            inner.pid = Some(pid);
            inner.started_at_ms = Some(now_ms());
            inner.instance_id = None;
            inner.last_exit_code = None;
            inner.last_error = None;
        }
        self.wait_for_health(app, &root)
    }

    pub fn ensure(&self, app: &AppHandle) -> Result<RuntimeStatus, String> {
        let mut last = self.status(app)?;
        if last.healthy {
            return Ok(last);
        }
        if !last.binary_available {
            return Ok(last);
        }
        if last.managed && last.state == "starting" {
            last = self.wait_for_health(app, &owner_data_root()?)?;
            if last.healthy {
                return Ok(last);
            }
        }
        for attempt in 0..STARTUP_ATTEMPTS {
            if attempt > 0 {
                {
                    let mut inner = self.inner.lock().unwrap_or_else(|poisoned| poisoned.into_inner());
                    inner.restart_count = inner.restart_count.saturating_add(1);
                }
                thread::sleep(Duration::from_millis(500 * u64::from(attempt)));
            }
            last = self.spawn_once(app)?;
            if last.healthy {
                return Ok(last);
            }
        }
        Ok(last)
    }

    fn stop_managed_process(&self, root: &Path) {
        let (mut child, pid, instance_id, managed) = {
            let mut inner = self.inner.lock().unwrap_or_else(|poisoned| poisoned.into_inner());
            inner.state = "stopping".to_string();
            (
                inner.child.take(),
                inner.pid,
                inner.instance_id.clone().or_else(|| read_identity(root).map(|value| value.instance_id)),
                inner.managed,
            )
        };
        if !managed {
            return;
        }

        if let Some(instance_id) = instance_id.as_deref() {
            let _ = write_stop_request(root, instance_id);
        }

        let mut stopped = false;
        for _ in 0..STOP_POLLS {
            if let Some(process) = child.as_mut() {
                if let Ok(Some(status)) = process.try_wait() {
                    let mut inner = self.inner.lock().unwrap_or_else(|poisoned| poisoned.into_inner());
                    inner.last_exit_code = status.code();
                    stopped = true;
                    break;
                }
            }
            if !authenticated_health(root) && read_identity(root).is_none() {
                stopped = true;
                break;
            }
            thread::sleep(STOP_POLL_DELAY);
        }

        if !stopped {
            if let Some(process) = child.as_mut() {
                let _ = process.kill();
                let status = process.wait().ok();
                let mut inner = self.inner.lock().unwrap_or_else(|poisoned| poisoned.into_inner());
                inner.last_exit_code = status.and_then(|value| value.code());
            } else if let Some(pid) = pid {
                force_kill_pid(pid);
            }
        } else if let Some(process) = child.as_mut() {
            let _ = process.wait();
        }

        clear_lifecycle_files(root, instance_id.as_deref());
        let mut inner = self.inner.lock().unwrap_or_else(|poisoned| poisoned.into_inner());
        inner.child = None;
        inner.pid = None;
        inner.instance_id = None;
        inner.managed = false;
        inner.started_at_ms = None;
    }

    pub fn stop(&self, app: &AppHandle) -> Result<RuntimeStatus, String> {
        let root = owner_data_root()?;
        let status = self.status(app)?;
        if status.healthy && !status.managed {
            return Err("The healthy 8766 service was started outside this Desktop and will not be stopped.".to_string());
        }
        self.stop_managed_process(&root);
        {
            let mut inner = self.inner.lock().unwrap_or_else(|poisoned| poisoned.into_inner());
            inner.state = "stopped".to_string();
            inner.last_error = None;
        }
        Ok(self.snapshot(app, &root, false))
    }

    pub fn restart(&self, app: &AppHandle) -> Result<RuntimeStatus, String> {
        let root = owner_data_root()?;
        let current = self.status(app)?;
        if current.healthy && !current.managed {
            return Err("The healthy 8766 service is external and cannot be restarted by this Desktop.".to_string());
        }
        self.stop_managed_process(&root);
        {
            let mut inner = self.inner.lock().unwrap_or_else(|poisoned| poisoned.into_inner());
            inner.state = "stopped".to_string();
            inner.restart_count = inner.restart_count.saturating_add(1);
        }
        self.spawn_once(app)
    }

    pub fn shutdown(&self) {
        let managed = self
            .inner
            .lock()
            .unwrap_or_else(|poisoned| poisoned.into_inner())
            .managed;
        if managed {
            if let Ok(root) = owner_data_root() {
                self.stop_managed_process(&root);
            }
        }
    }
}

async fn run_blocking<F>(operation: F) -> Result<RuntimeStatus, String>
where
    F: FnOnce() -> Result<RuntimeStatus, String> + Send + 'static,
{
    tauri::async_runtime::spawn_blocking(operation)
        .await
        .map_err(|error| format!("Runtime manager task failed: {error}"))?
}

#[tauri::command]
pub async fn runtime_status(
    app: AppHandle,
    manager: State<'_, RuntimeManager>,
) -> Result<RuntimeStatus, String> {
    let manager = manager.inner().clone();
    run_blocking(move || manager.status(&app)).await
}

#[tauri::command]
pub async fn runtime_ensure(
    app: AppHandle,
    manager: State<'_, RuntimeManager>,
) -> Result<RuntimeStatus, String> {
    let manager = manager.inner().clone();
    run_blocking(move || manager.ensure(&app)).await
}

#[tauri::command]
pub async fn runtime_stop(
    app: AppHandle,
    manager: State<'_, RuntimeManager>,
) -> Result<RuntimeStatus, String> {
    let manager = manager.inner().clone();
    run_blocking(move || manager.stop(&app)).await
}

#[tauri::command]
pub async fn runtime_restart(
    app: AppHandle,
    manager: State<'_, RuntimeManager>,
) -> Result<RuntimeStatus, String> {
    let manager = manager.inner().clone();
    run_blocking(move || manager.restart(&app)).await
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn display_paths_do_not_expose_owner_name() {
        let root = PathBuf::from(r"C:\Users\Owner\AppData\Local\LingJi");
        let (display, log) = display_paths(&root);
        assert!(!display.contains("Owner"));
        assert!(!log.contains("Owner"));
    }

    #[test]
    fn token_path_stays_under_storage() {
        let root = PathBuf::from(r"C:\Data\LingJi");
        assert_eq!(token_path(&root), root.join("storage").join("control_api_token"));
    }

    #[test]
    fn packaged_identity_requires_fixed_mode_and_loopback() {
        let identity = PackagedRuntimeIdentity {
            schema_version: 1,
            mode: "packaged_sidecar".to_string(),
            pid: 123,
            instance_id: "instance".to_string(),
            started_at_ms: now_ms(),
            host: "127.0.0.1".to_string(),
            port: CONTROL_PORT,
        };
        assert!(identity_is_recent(&identity));
        assert_eq!(identity.mode, "packaged_sidecar");
        assert_eq!(identity.host, "127.0.0.1");
    }
}
