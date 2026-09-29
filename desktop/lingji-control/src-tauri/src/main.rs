#![cfg_attr(not(debug_assertions), windows_subsystem = "windows")]

mod runtime_bootstrap;
mod runtime_manager;

use runtime_bootstrap::RuntimeBootstrapStatus;
use runtime_manager::{owner_data_root, RuntimeManager, RuntimeStatus};
use serde::Serialize;
use std::{env, fs, path::PathBuf};
use tauri::{AppHandle, Manager, State};

#[derive(Serialize)]
struct ControlCredentials {
    base_url: String,
    token: String,
}

#[derive(Serialize)]
struct ReleaseMetadata {
    product_name: &'static str,
    version: &'static str,
    commit: &'static str,
    build_time_utc: &'static str,
    channel: &'static str,
    target: &'static str,
    installer_format: &'static str,
    signed: bool,
}

fn prepare_platform_environment() {
    #[cfg(target_os = "macos")]
    {
        if env::var_os("LOCALAPPDATA").is_none() {
            if let Some(home) = env::var_os("HOME") {
                let app_support = PathBuf::from(home).join("Library").join("Application Support");
                env::set_var("LOCALAPPDATA", app_support);
            }
        }
    }
}

fn installer_format() -> &'static str {
    #[cfg(target_os = "windows")]
    {
        return "nsis";
    }
    #[cfg(target_os = "macos")]
    {
        return "dmg";
    }
    #[cfg(not(any(target_os = "windows", target_os = "macos")))]
    {
        "unknown"
    }
}

#[tauri::command]
fn control_credentials() -> Result<ControlCredentials, String> {
    runtime_bootstrap::require_configured()?;
    let base_url = env::var("LINGJI_CONTROL_BASE_URL")
        .unwrap_or_else(|_| "http://127.0.0.1:8766".to_string());
    let mut candidates = Vec::new();
    if let Ok(value) = env::var("LINGJI_CONTROL_TOKEN_FILE") {
        let path = PathBuf::from(value);
        if path.is_absolute() {
            candidates.push(path);
        }
    }
    candidates.push(owner_data_root()?.join("storage").join("control_api_token"));

    for path in candidates {
        if let Ok(value) = fs::read_to_string(&path) {
            let token = value.trim().to_string();
            if !token.is_empty() {
                return Ok(ControlCredentials { base_url, token });
            }
        }
    }
    Ok(ControlCredentials {
        base_url,
        token: String::new(),
    })
}

/// 托盘菜单直接调用本机控制 API（如暂停/恢复自动整理）。
/// 复用 control_credentials 的凭据解析；curl 是系统自带工具，避免为一次
/// POST 引入 HTTP 依赖。失败只写 stderr，不弹窗打扰主人。
fn post_control_action(handle: &tauri::AppHandle, path: &str) {
    let _ = handle;
    let credentials = (|| {
        runtime_bootstrap::require_configured().ok()?;
        let base_url = env::var("LINGJI_CONTROL_BASE_URL")
            .unwrap_or_else(|_| "http://127.0.0.1:8766".to_string());
        let mut candidates = Vec::new();
        if let Ok(value) = env::var("LINGJI_CONTROL_TOKEN_FILE") {
            let path = PathBuf::from(value);
            if path.is_absolute() {
                candidates.push(path);
            }
        }
        candidates.push(owner_data_root().ok()?.join("storage").join("control_api_token"));
        for path in candidates {
            if let Ok(value) = fs::read_to_string(&path) {
                let token = value.trim().to_string();
                if !token.is_empty() {
                    return Some((base_url, token));
                }
            }
        }
        None
    })();
    let Some((base_url, token)) = credentials else {
        eprintln!("lingji tray action {path}: control credentials unavailable");
        return;
    };
    let url = format!("{base_url}{path}");
    let status = std::process::Command::new("curl")
        .args(["-s", "-o", "/dev/null", "-w", "%{http_code}", "-m", "10", "-X", "POST", "-H", &format!("X-LingJi-Token: {token}"), "-H", "Content-Type: application/json", "-d", "{}", &url])
        .output();
    match status {
        Ok(output) if String::from_utf8_lossy(&output.stdout).trim() == "200" => {}
        Ok(output) => eprintln!(
            "lingji tray action {path}: unexpected response {:?}",
            String::from_utf8_lossy(&output.stdout).trim()
        ),
        Err(error) => eprintln!("lingji tray action {path}: {error}"),
    }
}

/// 后台托盘路径只调 window.show/set_focus 时，macOS 可能拒绝后台应用激活，
/// WKWebView 的 document.hidden 不翻转会让前端所有轮询保持暂停（首页数据冻结）。
/// 必须先做 App 级 show，再显示并聚焦窗口。
fn show_main_window(handle: &AppHandle) {
    #[cfg(target_os = "macos")]
    let _ = handle.show();
    if let Some(window) = handle.get_webview_window("main") {
        let _ = window.show();
        let _ = window.set_focus();
    }
}

#[tauri::command]
fn release_metadata() -> ReleaseMetadata {    ReleaseMetadata {
        product_name: "灵机",
        version: env!("CARGO_PKG_VERSION"),
        commit: env!("LINGJI_BUILD_COMMIT"),
        build_time_utc: env!("LINGJI_BUILD_TIME_UTC"),
        channel: env!("LINGJI_BUILD_CHANNEL"),
        target: env!("LINGJI_BUILD_TARGET"),
        installer_format: installer_format(),
        signed: env!("LINGJI_BUILD_SIGNED").eq_ignore_ascii_case("true"),
    }
}

#[tauri::command]
fn runtime_bootstrap_status() -> RuntimeBootstrapStatus {
    runtime_bootstrap::current_status()
}

#[tauri::command]
fn runtime_configure(
    base_data_root: String,
    workspace: String,
) -> Result<RuntimeBootstrapStatus, String> {
    runtime_bootstrap::configure(base_data_root, workspace)
}

async fn run_runtime<F>(operation: F) -> Result<RuntimeStatus, String>
where
    F: FnOnce() -> Result<RuntimeStatus, String> + Send + 'static,
{
    tauri::async_runtime::spawn_blocking(operation)
        .await
        .map_err(|error| format!("Runtime manager task failed: {error}"))?
}

#[tauri::command]
async fn guarded_runtime_status(
    app: AppHandle,
    manager: State<'_, RuntimeManager>,
) -> Result<RuntimeStatus, String> {
    runtime_bootstrap::require_configured()?;
    let manager = manager.inner().clone();
    run_runtime(move || manager.status(&app)).await
}

#[tauri::command]
async fn guarded_runtime_ensure(
    app: AppHandle,
    manager: State<'_, RuntimeManager>,
) -> Result<RuntimeStatus, String> {
    runtime_bootstrap::require_configured()?;
    let manager = manager.inner().clone();
    run_runtime(move || manager.ensure(&app)).await
}

#[tauri::command]
async fn guarded_runtime_stop(
    app: AppHandle,
    manager: State<'_, RuntimeManager>,
) -> Result<RuntimeStatus, String> {
    runtime_bootstrap::require_configured()?;
    let manager = manager.inner().clone();
    run_runtime(move || manager.stop(&app)).await
}

#[tauri::command]
async fn guarded_runtime_restart(
    app: AppHandle,
    manager: State<'_, RuntimeManager>,
) -> Result<RuntimeStatus, String> {
    runtime_bootstrap::require_configured()?;
    let manager = manager.inner().clone();
    run_runtime(move || manager.restart(&app)).await
}

fn main() -> tauri::Result<()> {
    prepare_platform_environment();
    runtime_bootstrap::quarantine_inherited_environment();
    let _ = runtime_bootstrap::apply_saved_environment();
    let app = tauri::Builder::default()
        .plugin(tauri_plugin_dialog::init())
        .plugin(tauri_plugin_opener::init())
        .manage(RuntimeManager::default())
        .invoke_handler(tauri::generate_handler![
            control_credentials,
            release_metadata,
            runtime_bootstrap_status,
            runtime_configure,
            guarded_runtime_status,
            guarded_runtime_ensure,
            guarded_runtime_stop,
            guarded_runtime_restart
        ])
        .setup(|handle| {
            // 关窗 = 隐藏到菜单栏（灵机继续后台整理记忆），真正退出走托盘菜单。
            use tauri::{
                menu::{Menu, MenuItem},
                tray::{MouseButton, MouseButtonState, TrayIconBuilder, TrayIconEvent},
                Manager,
            };

            if let Some(main_window) = handle.get_webview_window("main") {
                let window_for_close = main_window.clone();
                main_window.on_window_event(move |event| {
                    if let tauri::WindowEvent::CloseRequested { api, .. } = event {
                        // 拦截关闭：只隐藏窗口，进程与后台整理继续
                        api.prevent_close();
                        let _ = window_for_close.hide();
                    }
                });
            }

            let show = MenuItem::with_id(handle, "open", "打开灵机", true, None::<&str>)?;
            let pause = MenuItem::with_id(handle, "pause", "暂停自动整理", true, None::<&str>)?;
            let resume = MenuItem::with_id(handle, "resume", "恢复自动整理", true, None::<&str>)?;
            let quit = MenuItem::with_id(handle, "quit", "退出灵机（停止后台整理）", true, None::<&str>)?;
            let menu = Menu::with_items(handle, &[&show, &pause, &resume, &quit])?;
            let _tray = TrayIconBuilder::with_id("lingji-tray")
                .icon(handle.default_window_icon().cloned().unwrap_or_else(|| {
                    tauri::image::Image::from_bytes(include_bytes!("../icons/32x32.png"))
                        .expect("bundled icon")
                }))
                .tooltip("灵机 · 后台自动整理记忆中")
                .menu(&menu)
                .show_menu_on_left_click(false)
                .on_menu_event(|handle, event| {
                    match event.id().as_ref() {
                        "open" => show_main_window(handle),
                        "pause" => {
                            post_control_action(handle, "/api/automatic-memory/pause-runtime");
                            if let Some(tray) = handle.tray_by_id("lingji-tray") {
                                let _ = tray.set_tooltip(Some("灵机 · 已暂停自动整理（托盘菜单可恢复）"));
                            }
                        }
                        "resume" => {
                            post_control_action(handle, "/api/automatic-memory/resume-runtime");
                            if let Some(tray) = handle.tray_by_id("lingji-tray") {
                                let _ = tray.set_tooltip(Some("灵机 · 后台自动整理记忆中"));
                            }
                        }
                        "quit" => {
                            handle.exit(0);
                        }
                        _ => {}
                    }
                })
                .on_tray_icon_event(|tray, event| {
                    // 左键单击托盘图标 = 显示主窗口
                    if matches!(event, TrayIconEvent::Click { button: MouseButton::Left, button_state: MouseButtonState::Up, .. }) {
                        show_main_window(tray.app_handle());
                    }
                })
                .build(handle)?;
            Ok(())
        })
        .build(tauri::generate_context!())
        .expect("error while building LingJi control center");

    app.run(|app_handle, event| match event {
        // 主窗口隐藏期间 macOS 可能仍发出退出请求：一律拒绝，
        // 只允许托盘菜单 quit 触发的 Exit 走真正退出。
        tauri::RunEvent::ExitRequested { api, code, .. } => {
            if code.is_none() {
                api.prevent_exit();
            }
        }
        // 主窗口点关闭 = 隐藏到托盘（不销毁），否则窗口没了只能重启 App。
        tauri::RunEvent::WindowEvent {
            label,
            event: tauri::WindowEvent::CloseRequested { api, .. },
            ..
        } if label == "main" => {
            if let Some(window) = app_handle.get_webview_window("main") {
                let _ = window.hide();
            }
            api.prevent_close();
        }
        // macOS Dock 图标点击 / open -a 灵机：把主窗口带回来（2026-09-28：
        // 之前关闭后无法唤回，主人以为 App 坏了）。
        tauri::RunEvent::Reopen { .. } => {
            show_main_window(app_handle);
        }
        tauri::RunEvent::Exit => {
            app_handle.state::<RuntimeManager>().shutdown();
        }
        _ => {}
    });
    Ok(())
}
