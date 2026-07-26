mod runtime_manager;

use runtime_manager::{
    owner_data_root, runtime_ensure, runtime_restart, runtime_status, runtime_stop, RuntimeManager,
};
use serde::Serialize;
use std::{env, fs, path::PathBuf};
use tauri::Manager;

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

fn push_env_path(candidates: &mut Vec<PathBuf>, variable: &str, suffix: &[&str]) {
    if let Ok(root) = env::var(variable) {
        let mut path = PathBuf::from(root);
        for part in suffix {
            path.push(part);
        }
        candidates.push(path);
    }
}

#[tauri::command]
fn control_credentials() -> Result<ControlCredentials, String> {
    let base_url = env::var("LINGJI_CONTROL_BASE_URL")
        .unwrap_or_else(|_| "http://127.0.0.1:8766".to_string());
    let explicit = env::var("LINGJI_CONTROL_TOKEN_FILE").ok().map(PathBuf::from);
    let mut candidates = Vec::new();
    if let Some(path) = explicit {
        candidates.push(path);
    }
    if let Ok(root) = owner_data_root() {
        candidates.push(root.join("storage").join("control_api_token"));
    }

    push_env_path(
        &mut candidates,
        "LOCALAPPDATA",
        &["LingJi", "storage", "control_api_token"],
    );
    push_env_path(
        &mut candidates,
        "APPDATA",
        &["LingJi", "storage", "control_api_token"],
    );
    push_env_path(
        &mut candidates,
        "USERPROFILE",
        &[".lingji", "storage", "control_api_token"],
    );

    if let Ok(current) = env::current_dir() {
        candidates.push(current.join("storage").join("control_api_token"));
        candidates.push(current.join("..").join("storage").join("control_api_token"));
        candidates.push(current.join("..").join("..").join("storage").join("control_api_token"));
    }
    if let Ok(executable) = env::current_exe() {
        if let Some(parent) = executable.parent() {
            candidates.push(parent.join("storage").join("control_api_token"));
            candidates.push(parent.join("..").join("storage").join("control_api_token"));
        }
    }
    for path in candidates {
        if let Ok(value) = fs::read_to_string(&path) {
            let token = value.trim().to_string();
            if !token.is_empty() {
                return Ok(ControlCredentials { base_url, token });
            }
        }
    }
    Ok(ControlCredentials { base_url, token: String::new() })
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

fn main() {
    let app = tauri::Builder::default()
        .plugin(tauri_plugin_dialog::init())
        .manage(RuntimeManager::default())
        .invoke_handler(tauri::generate_handler![
            control_credentials,
            release_metadata,
            runtime_status,
            runtime_ensure,
            runtime_stop,
            runtime_restart
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
