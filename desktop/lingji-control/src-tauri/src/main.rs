use serde::Serialize;
use std::{env, fs, path::PathBuf};

#[derive(Serialize)]
struct ControlCredentials {
    base_url: String,
    token: String,
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

fn main() {
    tauri::Builder::default()
        .plugin(tauri_plugin_dialog::init())
        .invoke_handler(tauri::generate_handler![control_credentials])
        .run(tauri::generate_context!())
        .expect("error while running LingJi control center");
}
