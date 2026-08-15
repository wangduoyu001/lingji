#![cfg_attr(not(debug_assertions), windows_subsystem = "windows")]

mod runtime_bootstrap;
mod runtime_manager;

use runtime_bootstrap::RuntimeBootstrapStatus;
use runtime_manager::{owner_data_root, RuntimeManager, RuntimeStatus};
use serde::Serialize;
use std::{env, fs, path::PathBuf};
use tauri::menu::{MenuBuilder, MenuItemBuilder, SubmenuBuilder};
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

fn release_metadata_output_path() -> Option<PathBuf> {
    let mut arguments = env::args_os();
    while let Some(argument) = arguments.next() {
        if argument == "--release-metadata-output" {
            return arguments.next().map(PathBuf::from);
        }
    }
    None
}

fn recover_main_window(app: &AppHandle) {
    if let Some(window) = app.get_webview_window("main") {
        let _ = window.unminimize();
        let _ = window.show();
        let _ = window.center();
        let _ = window.set_focus();
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

#[tauri::command]
fn release_metadata() -> ReleaseMetadata {
    ReleaseMetadata {
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
fn runtime_autoconfigure() -> Result<RuntimeBootstrapStatus, String> {
    runtime_bootstrap::configure_default()
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

fn main() {
    prepare_platform_environment();
    if let Some(path) = release_metadata_output_path() {
        let payload = match serde_json::to_vec_pretty(&release_metadata()) {
            Ok(payload) => payload,
            Err(error) => {
                eprintln!("Unable to encode LingJi release metadata: {error}");
                std::process::exit(2);
            }
        };
        if let Err(error) = fs::write(path, payload) {
            eprintln!("Unable to write LingJi release metadata: {error}");
            std::process::exit(2);
        }
        return;
    }
    runtime_bootstrap::quarantine_inherited_environment();
    let _ = runtime_bootstrap::apply_saved_environment()
        .or_else(|_| runtime_bootstrap::configure_default());

    let app = tauri::Builder::default()
        .plugin(tauri_plugin_dialog::init())
        .manage(RuntimeManager::default())
        .invoke_handler(tauri::generate_handler![
            control_credentials,
            release_metadata,
            runtime_bootstrap_status,
            runtime_autoconfigure,
            runtime_configure,
            guarded_runtime_status,
            guarded_runtime_ensure,
            guarded_runtime_stop,
            guarded_runtime_restart
        ])
        .build(tauri::generate_context!())
        .expect("error while building LingJi control center");

    let recover_item = MenuItemBuilder::with_id("recover-main-window", "将灵机带到当前屏幕")
        .accelerator("CmdOrCtrl+Shift+L")
        .build(&app)
        .expect("error while building LingJi recovery menu item");
    let window_menu = SubmenuBuilder::new(&app, "窗口")
        .item(&recover_item)
        .build()
        .expect("error while building LingJi window submenu");
    let menu = MenuBuilder::new(&app)
        .item(&window_menu)
        .build()
        .expect("error while building LingJi window menu");
    app.set_menu(menu)
        .expect("error while setting LingJi window menu");
    app.on_menu_event(|app_handle, event| {
        if event.id().0 == "recover-main-window" {
            recover_main_window(app_handle);
        }
    });

    app.run(|app_handle, event| match event {
        #[cfg(target_os = "macos")]
        tauri::RunEvent::Reopen { .. } => {
            recover_main_window(app_handle);
        }
        tauri::RunEvent::ExitRequested { .. } | tauri::RunEvent::Exit => {
            app_handle.state::<RuntimeManager>().shutdown();
        }
        _ => {}
    });
}
