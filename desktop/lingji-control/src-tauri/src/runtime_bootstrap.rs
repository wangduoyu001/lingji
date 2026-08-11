use serde::{Deserialize, Serialize};
use std::{
    env,
    fs,
    io::Write,
    net::{IpAddr, Ipv4Addr, SocketAddr, TcpStream},
    path::{Path, PathBuf},
    sync::OnceLock,
    time::Duration,
};

const BOOTSTRAP_SCHEMA_VERSION: u32 = 2;
const CONTROL_PORT: u16 = 8766;
const SUPPORTED_WORKSPACES: [&str; 2] = ["production", "acceptance"];
const OWNER_DATA_ROOT_ENV: &str = "LINGJI_OWNER_DATA_ROOT";
const WORKSPACE_ENV: &str = "LINGJI_WORKSPACE";
const ACCEPTANCE_DATA_ROOT_ENV: &str = "LINGJI_ACCEPTANCE_DATA_ROOT";

static INHERITED_ENVIRONMENT_IGNORED: OnceLock<bool> = OnceLock::new();

#[derive(Clone, Debug, Deserialize, Serialize)]
struct RuntimeBootstrapConfig {
    schema_version: u32,
    base_data_root: String,
    active_workspace: String,
    #[serde(default)]
    owner_confirmed: bool,
    #[serde(default)]
    auto_selected: bool,
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
    pub inherited_environment_ignored: bool,
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
    #[cfg(target_os = "macos")]
    {
        return "$HOME/Library/Application Support/LingJi/desktop-bootstrap.json".to_string();
    }
    #[cfg(target_os = "windows")]
    {
        return "%LOCALAPPDATA%\\LingJi\\desktop-bootstrap.json".to_string();
    }
    #[cfg(not(any(target_os = "windows", target_os = "macos")))]
    {
        "LingJi/desktop-bootstrap.json".to_string()
    }
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

fn validate_base_root(value: &str, probe_write: bool) -> Result<PathBuf, String> {
    let trimmed = value.trim();
    if trimmed.is_empty() {
        return Err("A data directory is required".to_string());
    }
    let path = PathBuf::from(trimmed);
    if looks_like_windows_system_drive(&path) {
        return Err(
            "LingJi databases, vectors, logs and generated data may not use the Windows C: drive"
                .to_string(),
        );
    }
    if !path.is_absolute() {
        return Err("The LingJi data directory must be an absolute path".to_string());
    }
    if path.parent().is_none() {
        return Err("The LingJi data directory cannot be a filesystem root".to_string());
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

fn acceptance_override_value() -> Option<String> {
    env::var(ACCEPTANCE_DATA_ROOT_ENV)
        .ok()
        .map(|value| value.trim().to_string())
        .filter(|value| !value.is_empty())
}

fn acceptance_override_status(probe_write: bool) -> Result<Option<RuntimeBootstrapStatus>, String> {
    let Some(value) = acceptance_override_value() else {
        return Ok(None);
    };
    let root = validate_base_root(&value, probe_write)?;
    Ok(Some(RuntimeBootstrapStatus {
        configured: true,
        active_workspace: Some("acceptance".to_string()),
        base_data_root_display: root.parent().map(|path| path.display().to_string()),
        data_root_display: Some(root.display().to_string()),
        config_path_display: config_path_display(),
        source: "acceptance_override".to_string(),
        c_drive_write_detected: looks_like_windows_system_drive(&root),
        inherited_environment_ignored: inherited_environment_ignored(),
        last_error: None,
    }))
}

fn inherited_environment_present() -> bool {
    [OWNER_DATA_ROOT_ENV, WORKSPACE_ENV].iter().any(|name| {
        env::var(name)
            .ok()
            .is_some_and(|value| !value.trim().is_empty())
    })
}

pub fn quarantine_inherited_environment() -> bool {
    if let Some(value) = INHERITED_ENVIRONMENT_IGNORED.get() {
        return *value;
    }
    let detected = inherited_environment_present();
    env::remove_var(OWNER_DATA_ROOT_ENV);
    env::remove_var(WORKSPACE_ENV);
    let _ = INHERITED_ENVIRONMENT_IGNORED.set(detected);
    detected
}

fn inherited_environment_ignored() -> bool {
    *INHERITED_ENVIRONMENT_IGNORED.get_or_init(|| false)
}

fn validate_config_contract(config: &RuntimeBootstrapConfig) -> Result<(), String> {
    if config.schema_version != BOOTSTRAP_SCHEMA_VERSION {
        return Err(
            "LingJi data directory configuration must be prepared again by the installed UI"
                .to_string(),
        );
    }
    if !config.owner_confirmed && !config.auto_selected {
        return Err(
            "LingJi data directory configuration has neither an automatic safe selection nor owner confirmation"
                .to_string(),
        );
    }
    Ok(())
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
    validate_config_contract(&config)?;
    if config.active_workspace.eq_ignore_ascii_case("acceptance") && acceptance_override_value().is_none() {
        return Err(
            "A persisted acceptance workspace is never reused by a normal LingJi launch; an explicit task-scoped acceptance override is required"
                .to_string(),
        );
    }
    Ok(config)
}

fn status_from_config(
    config: RuntimeBootstrapConfig,
    source: &str,
) -> Result<RuntimeBootstrapStatus, String> {
    validate_config_contract(&config)?;
    let workspace = validate_workspace(&config.active_workspace)?;
    let base = validate_base_root(&config.base_data_root, false)?;
    let effective = effective_data_root(&base, &workspace);
    Ok(RuntimeBootstrapStatus {
        configured: true,
        active_workspace: Some(workspace),
        base_data_root_display: Some(base.display().to_string()),
        data_root_display: Some(effective.display().to_string()),
        config_path_display: config_path_display(),
        source: source.to_string(),
        c_drive_write_detected: looks_like_windows_system_drive(&effective),
        inherited_environment_ignored: inherited_environment_ignored(),
        last_error: None,
    })
}

fn unconfigured_status(error: String) -> RuntimeBootstrapStatus {
    let source = if error.contains("prepared again") || error.contains("neither an automatic") {
        "reconfirmation_required"
    } else if error.contains("acceptance workspace") {
        "acceptance_isolation_required"
    } else {
        "unconfigured"
    };
    RuntimeBootstrapStatus {
        configured: false,
        active_workspace: None,
        base_data_root_display: None,
        data_root_display: None,
        config_path_display: config_path_display(),
        source: source.to_string(),
        c_drive_write_detected: false,
        inherited_environment_ignored: inherited_environment_ignored(),
        last_error: Some(error),
    }
}

pub fn current_status() -> RuntimeBootstrapStatus {
    quarantine_inherited_environment();
    match acceptance_override_status(false) {
        Ok(Some(status)) => status,
        Ok(None) => match read_saved_config().and_then(|config| status_from_config(config, "bootstrap_file")) {
            Ok(status) => status,
            Err(error) => unconfigured_status(error),
        },
        Err(error) => unconfigured_status(error),
    }
}

pub fn apply_saved_environment() -> Result<RuntimeBootstrapStatus, String> {
    quarantine_inherited_environment();
    let status = if let Some(status) = acceptance_override_status(false)? {
        status
    } else {
        let config = read_saved_config()?;
        status_from_config(config, "bootstrap_file")?
    };
    let workspace = status
        .active_workspace
        .as_deref()
        .ok_or_else(|| "LingJi workspace is unavailable".to_string())?;
    let data_root = status
        .data_root_display
        .as_deref()
        .ok_or_else(|| "LingJi data directory is unavailable".to_string())?;
    env::set_var(OWNER_DATA_ROOT_ENV, data_root);
    env::set_var(WORKSPACE_ENV, workspace);
    Ok(status)
}

pub fn require_configured() -> Result<RuntimeBootstrapStatus, String> {
    let status = apply_saved_environment()?;
    if !status.configured || status.c_drive_write_detected {
        return Err("LingJi requires a safe configured data directory".to_string());
    }
    Ok(status)
}

fn default_base_root() -> Result<PathBuf, String> {
    #[cfg(target_os = "macos")]
    {
        if let Ok(value) = env::var("LOCALAPPDATA") {
            let root = PathBuf::from(value);
            if root.is_absolute() {
                return Ok(root.join("LingJiData"));
            }
        }
        if let Ok(value) = env::var("HOME") {
            let root = PathBuf::from(value)
                .join("Library")
                .join("Application Support")
                .join("LingJiData");
            return Ok(root);
        }
        return Err("LingJi could not resolve the macOS Application Support directory".to_string());
    }
    #[cfg(target_os = "linux")]
    {
        if let Ok(value) = env::var("XDG_DATA_HOME") {
            let root = PathBuf::from(value);
            if root.is_absolute() {
                return Ok(root.join("LingJi"));
            }
        }
        if let Ok(value) = env::var("HOME") {
            return Ok(PathBuf::from(value).join(".local").join("share").join("LingJi"));
        }
        return Err("LingJi could not resolve a Linux user data directory".to_string());
    }
    #[cfg(target_os = "windows")]
    {
        Err("LingJi did not find a safe automatic non-system-drive location on Windows".to_string())
    }
    #[cfg(not(any(target_os = "windows", target_os = "macos", target_os = "linux")))]
    {
        Err("Automatic LingJi data directory selection is unavailable on this platform".to_string())
    }
}

fn control_port_in_use() -> bool {
    let address = SocketAddr::new(IpAddr::V4(Ipv4Addr::LOCALHOST), CONTROL_PORT);
    TcpStream::connect_timeout(&address, Duration::from_millis(250)).is_ok()
}

fn write_saved_config(path: &Path, config: &RuntimeBootstrapConfig) -> Result<(), String> {
    let parent = path
        .parent()
        .ok_or_else(|| "Invalid LingJi Desktop bootstrap configuration path".to_string())?;
    fs::create_dir_all(parent)
        .map_err(|error| format!("Unable to create the Desktop bootstrap directory: {error}"))?;

    let temporary = path.with_extension("json.tmp");
    let backup = path.with_extension("json.bak");
    let payload = serde_json::to_vec_pretty(config)
        .map_err(|error| format!("Unable to encode LingJi Desktop bootstrap configuration: {error}"))?;
    fs::write(&temporary, payload)
        .map_err(|error| format!("Unable to write LingJi Desktop bootstrap configuration: {error}"))?;

    let had_existing = path.exists();
    if had_existing {
        let _ = fs::remove_file(&backup);
        fs::rename(path, &backup)
            .map_err(|error| format!("Unable to stage the previous Desktop bootstrap configuration: {error}"))?;
    }

    if let Err(error) = fs::rename(&temporary, path) {
        if had_existing {
            let _ = fs::rename(&backup, path);
        }
        let _ = fs::remove_file(&temporary);
        return Err(format!(
            "Unable to activate LingJi Desktop bootstrap configuration: {error}"
        ));
    }

    if had_existing {
        let _ = fs::remove_file(&backup);
    }
    Ok(())
}

pub fn configure_default() -> Result<RuntimeBootstrapStatus, String> {
    quarantine_inherited_environment();
    if let Some(status) = acceptance_override_status(true)? {
        let data_root = status
            .data_root_display
            .as_deref()
            .ok_or_else(|| "Acceptance data directory is unavailable".to_string())?;
        env::set_var(OWNER_DATA_ROOT_ENV, data_root);
        env::set_var(WORKSPACE_ENV, "acceptance");
        return Ok(status);
    }
    if let Ok(status) = apply_saved_environment() {
        return Ok(status);
    }
    if control_port_in_use() {
        return Err("Stop the current LingJi runtime before preparing a new data directory".to_string());
    }

    let workspace = "production".to_string();
    let base = default_base_root()?;
    let base = validate_base_root(base.to_string_lossy().as_ref(), true)?;
    let effective = effective_data_root(&base, &workspace);
    validate_base_root(effective.to_string_lossy().as_ref(), true)?;

    let config = RuntimeBootstrapConfig {
        schema_version: BOOTSTRAP_SCHEMA_VERSION,
        base_data_root: base.display().to_string(),
        active_workspace: workspace.clone(),
        owner_confirmed: false,
        auto_selected: true,
    };
    write_saved_config(&config_path()?, &config)?;
    env::set_var(OWNER_DATA_ROOT_ENV, &effective);
    env::set_var(WORKSPACE_ENV, &workspace);
    status_from_config(config, "automatic_default")
}

pub fn configure(
    base_data_root: String,
    workspace: String,
) -> Result<RuntimeBootstrapStatus, String> {
    quarantine_inherited_environment();
    if control_port_in_use() {
        return Err("Stop the current LingJi runtime before changing its data directory".to_string());
    }
    let workspace = validate_workspace(&workspace)?;
    if workspace == "acceptance" && acceptance_override_value().is_none() {
        return Err(
            "Acceptance workspace is task-scoped and must use LINGJI_ACCEPTANCE_DATA_ROOT rather than a persisted owner setting"
                .to_string(),
        );
    }
    let base = validate_base_root(&base_data_root, true)?;
    let effective = effective_data_root(&base, &workspace);
    validate_base_root(effective.to_string_lossy().as_ref(), true)?;

    let config = RuntimeBootstrapConfig {
        schema_version: BOOTSTRAP_SCHEMA_VERSION,
        base_data_root: base.display().to_string(),
        active_workspace: workspace.clone(),
        owner_confirmed: true,
        auto_selected: false,
    };
    write_saved_config(&config_path()?, &config)?;

    env::set_var(OWNER_DATA_ROOT_ENV, &effective);
    env::set_var(WORKSPACE_ENV, &workspace);
    status_from_config(config, "owner_selected")
}

#[cfg(test)]
mod tests {
    use super::*;

    fn config(schema_version: u32, owner_confirmed: bool, auto_selected: bool) -> RuntimeBootstrapConfig {
        RuntimeBootstrapConfig {
            schema_version,
            base_data_root: "unused".to_string(),
            active_workspace: "production".to_string(),
            owner_confirmed,
            auto_selected,
        }
    }

    #[test]
    fn rejects_windows_system_drive_without_touching_it() {
        let error = validate_base_root(r"C:\LingJiData", false).unwrap_err();
        assert!(error.contains("C: drive"));
    }

    #[test]
    fn workspace_is_part_of_the_effective_data_root() {
        let base = PathBuf::from("data-root");
        assert_eq!(
            effective_data_root(&base, "acceptance"),
            base.join("acceptance")
        );
    }

    #[test]
    fn only_known_workspaces_are_allowed() {
        assert_eq!(validate_workspace("ACCEPTANCE").unwrap(), "acceptance");
        assert!(validate_workspace("shared").is_err());
    }

    #[test]
    fn legacy_bootstrap_requires_repreparation() {
        let error = validate_config_contract(&config(1, false, false)).unwrap_err();
        assert!(error.contains("prepared again"));
    }

    #[test]
    fn current_bootstrap_rejects_untrusted_selection() {
        let error = validate_config_contract(&config(BOOTSTRAP_SCHEMA_VERSION, false, false)).unwrap_err();
        assert!(error.contains("neither an automatic"));
    }

    #[test]
    fn current_owner_confirmed_bootstrap_is_accepted() {
        validate_config_contract(&config(BOOTSTRAP_SCHEMA_VERSION, true, false)).unwrap();
    }

    #[test]
    fn current_automatic_bootstrap_is_accepted() {
        validate_config_contract(&config(BOOTSTRAP_SCHEMA_VERSION, false, true)).unwrap();
    }
}
