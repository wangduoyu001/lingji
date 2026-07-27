use serde::{Deserialize, Serialize};
use std::{
    env,
    fs,
    io::Write,
    net::{IpAddr, Ipv4Addr, SocketAddr, TcpStream},
    path::{Path, PathBuf},
    time::Duration,
};

const BOOTSTRAP_SCHEMA_VERSION: u32 = 1;
const CONTROL_PORT: u16 = 8766;
const SUPPORTED_WORKSPACES: [&str; 2] = ["production", "acceptance"];

#[derive(Clone, Debug, Deserialize, Serialize)]
struct RuntimeBootstrapConfig {
    schema_version: u32,
    base_data_root: String,
    active_workspace: String,
}

#[derive(Clone, Debug, Serialize)]
pub struct RuntimeBootstrapStatus {
    pub configured: bool,
    pub active_workspace: Option<String>,
    pub base_data_root_display: Option<String>,
    pub data_root_display: Option<String>,
    pub config_path_display: String,
    pub source: String,
    pub c_drive_write_detected: bool,
    pub last_error: Option<String>,
}

fn config_path() -> Result<PathBuf, String> {
    for variable in ["LOCALAPPDATA", "APPDATA"] {
        if let Ok(value) = env::var(variable) {
            let root = PathBuf::from(value);
            if root.is_absolute() {
                return Ok(root.join("LingJi").join("desktop-bootstrap.json"));
            }
        }
    }
    Err("Unable to resolve the small Desktop bootstrap configuration directory".to_string())
}

fn config_path_display() -> String {
    "%LOCALAPPDATA%\\LingJi\\desktop-bootstrap.json".to_string()
}

fn validate_workspace(value: &str) -> Result<String, String> {
    let normalized = value.trim().to_lowercase();
    if SUPPORTED_WORKSPACES.contains(&normalized.as_str()) {
        Ok(normalized)
    } else {
        Err("Workspace must be either production or acceptance".to_string())
    }
}

fn looks_like_windows_system_drive(path: &Path) -> bool {
    let normalized = path.to_string_lossy().replace('/', "\\").to_lowercase();
    normalized == "c:" || normalized.starts_with("c:\\")
}

fn validate_base_root(value: &str, *, probe_write: bool) -> Result<PathBuf, String> {
    let trimmed = value.trim();
    if trimmed.is_empty() {
        return Err("A data directory is required".to_string());
    }
    let path = PathBuf::from(trimmed);
    if !path.is_absolute() {
        return Err("The LingJi data directory must be an absolute path".to_string());
    }
    if path.parent().is_none() {
        return Err("The LingJi data directory cannot be a filesystem root".to_string());
    }
    if looks_like_windows_system_drive(&path) {
        return Err("LingJi databases, vectors, logs and generated data may not use the Windows C: drive".to_string());
    }

    if probe_write {
        fs::create_dir_all(&path)
            .map_err(|error| format!("Unable to create LingJi data directory: {error}"))?;
        let probe = path.join(".lingji-desktop-write-test");
        let mut file = fs::File::create(&probe)
            .map_err(|error| format!("LingJi data directory is not writable: {error}"))?;
        file.write_all(b"ok")
            .map_err(|error| format!("LingJi data directory is not writable: {error}"))?;
        drop(file);
        fs::remove_file(&probe)
            .map_err(|error| format!("Unable to clean the LingJi write probe: {error}"))?;
    }
    Ok(path)
}

fn effective_data_root(base: &Path, workspace: &str) -> PathBuf {
    base.join(workspace)
}

fn read_saved_config() -> Result<RuntimeBootstrapConfig, String> {
    let path = config_path()?;
    let bytes = fs::read(&path).map_err(|error| {
        if error.kind() == std::io::ErrorKind::NotFound {
            "LingJi data directory has not been configured".to_string()
        } else {
            format!("Unable to read LingJi Desktop bootstrap configuration: {error}")
        }
    })?;
    let config: RuntimeBootstrapConfig = serde_json::from_slice(&bytes)
        .map_err(|error| format!("Invalid LingJi Desktop bootstrap configuration: {error}"))?;
    if config.schema_version != BOOTSTRAP_SCHEMA_VERSION {
        return Err("Unsupported LingJi Desktop bootstrap configuration version".to_string());
    }
    Ok(config)
}

fn status_from_config(config: RuntimeBootstrapConfig, source: &str) -> Result<RuntimeBootstrapStatus, String> {
    let workspace = validate_workspace(&config.active_workspace)?;
    let base = validate_base_root(&config.base_data_root, probe_write: false)?;
    let effective = effective_data_root(&base, &workspace);
    Ok(RuntimeBootstrapStatus {
        configured: true,
        active_workspace: Some(workspace),
        base_data_root_display: Some(base.display().to_string()),
        data_root_display: Some(effective.display().to_string()),
        config_path_display: config_path_display(),
        source: source.to_string(),
        c_drive_write_detected: looks_like_windows_system_drive(&effective),
        last_error: None,
    })
}

fn environment_status() -> Result<Option<RuntimeBootstrapStatus>, String> {
    let explicit = match env::var("LINGJI_OWNER_DATA_ROOT") {
        Ok(value) if !value.trim().is_empty() => value,
        _ => return Ok(None),
    };
    let workspace = validate_workspace(
        &env::var("LINGJI_WORKSPACE").unwrap_or_else(|_| "production".to_string()),
    )?;
    let effective = validate_base_root(&explicit, probe_write: false)?;
    let base = effective
        .parent()
        .map(Path::to_path_buf)
        .unwrap_or_else(|| effective.clone());
    Ok(Some(RuntimeBootstrapStatus {
        configured: true,
        active_workspace: Some(workspace),
        base_data_root_display: Some(base.display().to_string()),
        data_root_display: Some(effective.display().to_string()),
        config_path_display: config_path_display(),
        source: "environment".to_string(),
        c_drive_write_detected: looks_like_windows_system_drive(&effective),
        last_error: None,
    }))
}

pub fn current_status() -> RuntimeBootstrapStatus {
    match environment_status() {
        Ok(Some(status)) => status,
        Ok(None) => match read_saved_config().and_then(|config| status_from_config(config, "bootstrap_file")) {
            Ok(status) => status,
            Err(error) => RuntimeBootstrapStatus {
                configured: false,
                active_workspace: None,
                base_data_root_display: None,
                data_root_display: None,
                config_path_display: config_path_display(),
                source: "unconfigured".to_string(),
                c_drive_write_detected: false,
                last_error: Some(error),
            },
        },
        Err(error) => RuntimeBootstrapStatus {
            configured: false,
            active_workspace: None,
            base_data_root_display: None,
            data_root_display: None,
            config_path_display: config_path_display(),
            source: "invalid_environment".to_string(),
            c_drive_write_detected: false,
            last_error: Some(error),
        },
    }
}

pub fn apply_saved_environment() -> Result<RuntimeBootstrapStatus, String> {
    if let Some(status) = environment_status()? {
        return Ok(status);
    }
    let config = read_saved_config()?;
    let status = status_from_config(config, "bootstrap_file")?;
    let workspace = status
        .active_workspace
        .as_deref()
        .ok_or_else(|| "LingJi workspace is unavailable".to_string())?;
    let data_root = status
        .data_root_display
        .as_deref()
        .ok_or_else(|| "LingJi data directory is unavailable".to_string())?;
    env::set_var("LINGJI_OWNER_DATA_ROOT", data_root);
    env::set_var("LINGJI_WORKSPACE", workspace);
    Ok(status)
}

pub fn require_configured() -> Result<RuntimeBootstrapStatus, String> {
    let status = apply_saved_environment()?;
    if !status.configured || status.c_drive_write_detected {
        return Err("LingJi requires an explicitly configured non-C: data directory".to_string());
    }
    Ok(status)
}

fn control_port_in_use() -> bool {
    let address = SocketAddr::new(IpAddr::V4(Ipv4Addr::LOCALHOST), CONTROL_PORT);
    TcpStream::connect_timeout(&address, Duration::from_millis(250)).is_ok()
}

pub fn configure(base_data_root: String, workspace: String) -> Result<RuntimeBootstrapStatus, String> {
    if control_port_in_use() {
        return Err("Stop the current LingJi runtime before changing its data directory".to_string());
    }
    let workspace = validate_workspace(&workspace)?;
    let base = validate_base_root(&base_data_root, probe_write: true)?;
    let effective = effective_data_root(&base, &workspace);
    validate_base_root(&effective.to_string_lossy(), probe_write: true)?;

    let config = RuntimeBootstrapConfig {
        schema_version: BOOTSTRAP_SCHEMA_VERSION,
        base_data_root: base.display().to_string(),
        active_workspace: workspace.clone(),
    };
    let path = config_path()?;
    let parent = path
        .parent()
        .ok_or_else(|| "Invalid LingJi Desktop bootstrap configuration path".to_string())?;
    fs::create_dir_all(parent)
        .map_err(|error| format!("Unable to create the Desktop bootstrap directory: {error}"))?;
    let temporary = path.with_extension("json.tmp");
    let payload = serde_json::to_vec_pretty(&config)
        .map_err(|error| format!("Unable to encode LingJi Desktop bootstrap configuration: {error}"))?;
    fs::write(&temporary, payload)
        .map_err(|error| format!("Unable to write LingJi Desktop bootstrap configuration: {error}"))?;
    fs::rename(&temporary, &path)
        .map_err(|error| format!("Unable to activate LingJi Desktop bootstrap configuration: {error}"))?;

    env::set_var("LINGJI_OWNER_DATA_ROOT", &effective);
    env::set_var("LINGJI_WORKSPACE", &workspace);
    status_from_config(config, "bootstrap_file")
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn rejects_windows_system_drive_without_touching_it() {
        let error = validate_base_root(r"C:\LingJiData", probe_write: false).unwrap_err();
        assert!(error.contains("C: drive"));
    }

    #[test]
    fn workspace_is_part_of_the_effective_data_root() {
        let base = PathBuf::from(r"D:\LingJiData");
        assert_eq!(
            effective_data_root(&base, "acceptance"),
            PathBuf::from(r"D:\LingJiData\acceptance")
        );
    }

    #[test]
    fn only_known_workspaces_are_allowed() {
        assert_eq!(validate_workspace("ACCEPTANCE").unwrap(), "acceptance");
        assert!(validate_workspace("shared").is_err());
    }
}
