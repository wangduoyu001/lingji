#![cfg_attr(not(debug_assertions), windows_subsystem = "windows")]

mod runtime_bootstrap;
mod runtime_manager;

use runtime_bootstrap::{RuntimeBindingVerification, RuntimeBootstrapStatus};
use runtime_manager::{RuntimeManager, RuntimeStatus};
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

#[tauri::command]
fn control_credentials() -> Result<ControlCredentials, String> {
    let bootstrap = runtime_bootstrap::require_configured()?;
    runtime_bootstrap::require_verified_runtime()?;
    let base_url = env::var("LINGJI_CONTROL_BASE_URL")
        .unwrap_or_else(|_| "http://127.0.0.1:8766".to_string());
    let mut candidates = Vec::new();
    if let Ok(value) = env::var("LINGJI_CONTROL_TOKEN_FILE") {
        let path = PathBuf::from(value);
        if path.is_absolute() {
            candidates.push(path);
        }
    }
    if let Some(root) = bootstrap.data_root_display {
        candidates.push(PathBuf::from(root).join("storage").join("control_api_token"));
    }

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
        installer_format: "nsis",
        signed: env!("LINGJI_BUILD_SIGNED").eq_ignore_ascii_case("true"),
    }
}

#[tauri::command]
fn runtime_bootstrap_status() -> RuntimeBootstrapStatus {
    runtime_bootstrap::current_status()
}

#[tauri::command]
fn runtime_binding_verification() -> RuntimeBindingVerification {
    runtime_bootstrap::verify_runtime_binding()
}

#[tauri::command]
fn runtime_configure(
    base_data_root: String,
    workspace: String,
) -> Result<RuntimeBootstrapStatus, String> {
    runtime_bootstrap::configure(base_data_root, workspace)
}

#[tauri::command]
fn runtime_auto_configure() -> Result<RuntimeBootstrapStatus, String> {
    runtime_bootstrap::auto_configure()
}

async fn run_runtime<F>(operation: F) -> Result<RuntimeStatus, String>
where
    F: FnOnce() -> Result<RuntimeStatus, String> + Send + 'static,
{
    tauri::async_runtime::spawn_blocking(operation)
        .await
        .map_err(|error| format!("Runtime manager task failed: {error}"))?
}

async fn verify_or_stop(
    app: AppHandle,
    manager: RuntimeManager,
    status: RuntimeStatus,
) -> Result<RuntimeStatus, String> {
    if !status.healthy {
        return Ok(status);
    }
    let verification = runtime_bootstrap::verify_runtime_binding();
    if verification.verified && status.managed {
        return Ok(status);
    }

    if status.managed {
        let stop_manager = manager.clone();
        let stop_app = app.clone();
        let _ = run_runtime(move || stop_manager.stop(&stop_app)).await;
    }
    if !verification.verified {
        return Err(verification.error.unwrap_or_else(|| {
            "LingJi Runtime responded from an unverified DataRoot; Desktop refused to adopt it"
                .to_string()
        }));
    }
    Err("LingJi found an external Runtime and refused to adopt an unmanaged process".to_string())
}

#[tauri::command]
async fn guarded_runtime_status(
    app: AppHandle,
    manager: State<'_, RuntimeManager>,
) -> Result<RuntimeStatus, String> {
    runtime_bootstrap::require_configured()?;
    let manager = manager.inner().clone();
    let operation_manager = manager.clone();
    let operation_app = app.clone();
    let status = run_runtime(move || operation_manager.status(&operation_app)).await?;
    verify_or_stop(app, manager, status).await
}

#[tauri::command]
async fn guarded_runtime_ensure(
    app: AppHandle,
    manager: State<'_, RuntimeManager>,
) -> Result<RuntimeStatus, String> {
    runtime_bootstrap::require_configured()?;
    let manager = manager.inner().clone();
    let operation_manager = manager.clone();
    let operation_app = app.clone();
    let status = run_runtime(move || operation_manager.ensure(&operation_app)).await?;
    verify_or_stop(app, manager, status).await
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
    let operation_manager = manager.clone();
    let operation_app = app.clone();
    let status = run_runtime(move || operation_manager.restart(&operation_app)).await?;
    verify_or_stop(app, manager, status).await
}

fn initialize_runtime_binding() {
    runtime_bootstrap::quarantine_inherited_environment();
    if runtime_bootstrap::startup_contract_requested() {
        // A declared startup contract is authoritative. Any parse, path,
        // workspace, port or write-probe failure remains visible as a blocking
        // contract error. It must never fall back to a previous global bootstrap.
        let _ = runtime_bootstrap::apply_startup_contract();
    } else {
        let _ = runtime_bootstrap::apply_saved_environment();
    }
}

fn main() {
    initialize_runtime_binding();
    let app = tauri::Builder::default()
        .plugin(tauri_plugin_dialog::init())
        .manage(RuntimeManager::default())
        .invoke_handler(tauri::generate_handler![
            control_credentials,
            release_metadata,
            runtime_bootstrap_status,
            runtime_binding_verification,
            runtime_configure,
            runtime_auto_configure,
            guarded_runtime_status,
            guarded_runtime_ensure,
            guarded_runtime_stop,
            guarded_runtime_restart
        ])
        .build(tauri::generate_context!())
        .expect("error while building LingJi control center");

    app.run(|app_handle, event| match event {
        tauri::RunEvent::ExitRequested { .. } | tauri::RunEvent::Exit => {
            app_handle.state::<RuntimeManager>().shutdown();
        }
        _ => {}
    });
}
