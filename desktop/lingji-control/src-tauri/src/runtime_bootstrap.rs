use serde::{Deserialize, Serialize};
use std::{
    env,
    fs,
    io::{Read, Write},
    net::{IpAddr, Ipv4Addr, SocketAddr, TcpStream},
    path::{Path, PathBuf},
    sync::{Mutex, OnceLock},
    time::Duration,
};

const BOOTSTRAP_SCHEMA_VERSION: u32 = 3;
const LEGACY_BOOTSTRAP_SCHEMA_VERSION: u32 = 2;
const STARTUP_CONTRACT_SCHEMA_VERSION: u32 = 1;
const CONTROL_PORT: u16 = 8766;
const SUPPORTED_WORKSPACES: [&str; 2] = ["production", "acceptance"];
const OWNER_DATA_ROOT_ENV: &str = "LINGJI_OWNER_DATA_ROOT";
const WORKSPACE_ENV: &str = "LINGJI_WORKSPACE";
const STARTUP_CONTRACT_ENV: &str = "LINGJI_BOOTSTRAP_CONTRACT_FILE";

static INHERITED_ENVIRONMENT_IGNORED: OnceLock<bool> = OnceLock::new();
static STARTUP_CONTRACT_ERROR: OnceLock<Mutex<Option<String>>> = OnceLock::new();

fn default_binding_source() -> String {
    "owner_selection".to_string()
}

#[derive(Clone, Debug, Deserialize, Serialize)]
struct RuntimeBootstrapConfig {
    schema_version: u32,
    base_data_root: String,
    active_workspace: String,
    #[serde(default)]
    owner_confirmed: bool,
    #[serde(default)]
    effective_data_root: Option<String>,
    #[serde(default)]
    binding_id: String,
    #[serde(default = "default_binding_source")]
    binding_source: String,
    #[serde(default)]
    binding_locked: bool,
}

#[derive(Clone, Debug, Deserialize)]
struct RuntimeBindingContract {
    schema_version: u32,
    binding_id: String,
    data_root: String,
    workspace: String,
}

#[derive(Clone, Debug, Deserialize)]
struct RuntimePing {
    status: String,
    data_root: String,
    workspace: String,
}

#[derive(Clone, Debug, Serialize)]
pub struct RuntimeBootstrapStatus {
    pub configured: bool,
    pub active_workspace: Option<String>,
    pub base_data_root_display: Option<String>,
    pub data_root_display: Option<String>,
    pub config_path_display: String,
    pub source: String,
    pub binding_id: Option<String>,
    pub binding_locked: bool,
    pub c_drive_write_detected: bool,
    pub inherited_environment_ignored: bool,
    pub startup_contract_detected: bool,
    pub last_error: Option<String>,
}

#[derive(Clone, Debug, Serialize)]
pub struct RuntimeBindingVerification {
    pub verified: bool,
    pub expected_data_root: Option<String>,
    pub actual_data_root: Option<String>,
    pub expected_workspace: Option<String>,
    pub actual_workspace: Option<String>,
    pub source: String,
    pub binding_id: Option<String>,
    pub binding_locked: bool,
    pub error: Option<String>,
}

fn startup_error_slot() -> &'static Mutex<Option<String>> {
    STARTUP_CONTRACT_ERROR.get_or_init(|| Mutex::new(None))
}

fn set_startup_contract_error(error: Option<String>) {
    let mut value = startup_error_slot()
        .lock()
        .unwrap_or_else(|poisoned| poisoned.into_inner());
    *value = error;
}

fn startup_contract_error() -> Option<String> {
    startup_error_slot()
        .lock()
        .unwrap_or_else(|poisoned| poisoned.into_inner())
        .clone()
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

fn effective_data_root(config: &RuntimeBootstrapConfig, base: &Path, workspace: &str) -> PathBuf {
    config
        .effective_data_root
        .as_deref()
        .map(PathBuf::from)
        .unwrap_or_else(|| base.join(workspace))
}

fn normalized_identity(path: &Path) -> String {
    let resolved = fs::canonicalize(path).unwrap_or_else(|_| path.to_path_buf());
    resolved
        .to_string_lossy()
        .replace('/', "\\")
        .trim_end_matches('\\')
        .to_lowercase()
}

fn valid_binding_id(value: &str) -> bool {
    let trimmed = value.trim();
    !trimmed.is_empty()
        && trimmed.len() <= 128
        && trimmed
            .chars()
            .all(|character| character.is_ascii_alphanumeric() || "-_.:".contains(character))
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
    if ![LEGACY_BOOTSTRAP_SCHEMA_VERSION, BOOTSTRAP_SCHEMA_VERSION]
        .contains(&config.schema_version)
    {
        return Err(
            "LingJi data directory configuration must be confirmed again in the installed UI"
                .to_string(),
        );
    }
    if !config.owner_confirmed {
        return Err(
            "LingJi data directory configuration is missing an approved activation policy"
                .to_string(),
        );
    }
    if config.binding_locked && !valid_binding_id(&config.binding_id) {
        return Err("Locked LingJi runtime binding is missing a valid binding id".to_string());
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
    Ok(config)
}

fn status_from_config(config: RuntimeBootstrapConfig) -> Result<RuntimeBootstrapStatus, String> {
    validate_config_contract(&config)?;
    let workspace = validate_workspace(&config.active_workspace)?;
    let base = validate_base_root(&config.base_data_root, false)?;
    let effective = effective_data_root(&config, &base, &workspace);
    validate_base_root(effective.to_string_lossy().as_ref(), false)?;
    Ok(RuntimeBootstrapStatus {
        configured: true,
        active_workspace: Some(workspace),
        base_data_root_display: Some(base.display().to_string()),
        data_root_display: Some(effective.display().to_string()),
        config_path_display: config_path_display(),
        source: config.binding_source.clone(),
        binding_id: (!config.binding_id.trim().is_empty()).then_some(config.binding_id),
        binding_locked: config.binding_locked,
        c_drive_write_detected: looks_like_windows_system_drive(&effective),
        inherited_environment_ignored: inherited_environment_ignored(),
        startup_contract_detected: env::var(STARTUP_CONTRACT_ENV)
            .ok()
            .is_some_and(|value| !value.trim().is_empty()),
        last_error: startup_contract_error(),
    })
}

fn unconfigured_status(error: String) -> RuntimeBootstrapStatus {
    let source = if error.contains("confirmed again") || error.contains("activation policy") {
        "reconfirmation_required"
    } else if startup_contract_error().is_some() {
        "startup_contract_error"
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
        binding_id: None,
        binding_locked: false,
        c_drive_write_detected: false,
        inherited_environment_ignored: inherited_environment_ignored(),
        startup_contract_detected: env::var(STARTUP_CONTRACT_ENV)
            .ok()
            .is_some_and(|value| !value.trim().is_empty()),
        last_error: startup_contract_error().or(Some(error)),
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

fn activate_config(config: RuntimeBootstrapConfig) -> Result<RuntimeBootstrapStatus, String> {
    write_saved_config(&config_path()?, &config)?;
    let status = status_from_config(config)?;
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

pub fn apply_startup_contract() -> Result<Option<RuntimeBootstrapStatus>, String> {
    let contract_path = match env::var(STARTUP_CONTRACT_ENV) {
        Ok(value) if !value.trim().is_empty() => PathBuf::from(value.trim()),
        _ => return Ok(None),
    };
    if !contract_path.is_absolute() {
        let error = "LingJi startup binding contract path must be absolute".to_string();
        set_startup_contract_error(Some(error.clone()));
        return Err(error);
    }
    let bytes = fs::read(&contract_path)
        .map_err(|error| format!("Unable to read LingJi startup binding contract: {error}"))?;
    let contract: RuntimeBindingContract = serde_json::from_slice(&bytes)
        .map_err(|error| format!("Invalid LingJi startup binding contract: {error}"))?;
    if contract.schema_version != STARTUP_CONTRACT_SCHEMA_VERSION {
        let error = "Unsupported LingJi startup binding contract schema".to_string();
        set_startup_contract_error(Some(error.clone()));
        return Err(error);
    }
    if !valid_binding_id(&contract.binding_id) {
        let error = "LingJi startup binding contract has an invalid binding id".to_string();
        set_startup_contract_error(Some(error.clone()));
        return Err(error);
    }
    if control_port_in_use() {
        let error = "Refusing to change LingJi startup binding while port 8766 is already in use"
            .to_string();
        set_startup_contract_error(Some(error.clone()));
        return Err(error);
    }

    let workspace = validate_workspace(&contract.workspace)?;
    let data_root = validate_base_root(&contract.data_root, true)?;
    let config = RuntimeBootstrapConfig {
        schema_version: BOOTSTRAP_SCHEMA_VERSION,
        base_data_root: data_root.display().to_string(),
        active_workspace: workspace,
        owner_confirmed: true,
        effective_data_root: Some(data_root.display().to_string()),
        binding_id: contract.binding_id,
        binding_source: "startup_contract".to_string(),
        binding_locked: true,
    };
    set_startup_contract_error(None);
    activate_config(config).map(Some)
}

pub fn current_status() -> RuntimeBootstrapStatus {
    quarantine_inherited_environment();
    match read_saved_config().and_then(status_from_config) {
        Ok(status) => status,
        Err(error) => unconfigured_status(error),
    }
}

pub fn apply_saved_environment() -> Result<RuntimeBootstrapStatus, String> {
    quarantine_inherited_environment();
    let config = read_saved_config()?;
    let status = status_from_config(config)?;
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
        return Err("LingJi requires an explicitly configured non-C: data directory".to_string());
    }
    Ok(status)
}

pub fn configure(
    base_data_root: String,
    workspace: String,
) -> Result<RuntimeBootstrapStatus, String> {
    quarantine_inherited_environment();
    if control_port_in_use() {
        return Err("Stop the current LingJi runtime before changing its data directory".to_string());
    }
    if read_saved_config()
        .ok()
        .is_some_and(|config| config.binding_locked)
    {
        return Err(
            "The current LingJi data-root binding is locked by a startup contract and cannot be changed from the UI"
                .to_string(),
        );
    }
    let workspace = validate_workspace(&workspace)?;
    let base = validate_base_root(&base_data_root, true)?;
    let effective = base.join(&workspace);
    validate_base_root(effective.to_string_lossy().as_ref(), true)?;

    activate_config(RuntimeBootstrapConfig {
        schema_version: BOOTSTRAP_SCHEMA_VERSION,
        base_data_root: base.display().to_string(),
        active_workspace: workspace,
        owner_confirmed: true,
        effective_data_root: None,
        binding_id: String::new(),
        binding_source: "owner_selection".to_string(),
        binding_locked: false,
    })
}

#[cfg(target_os = "windows")]
fn automatic_base_candidates() -> Vec<PathBuf> {
    ('D'..='Z')
        .map(|letter| PathBuf::from(format!("{letter}:\\LingJiData")))
        .collect()
}

#[cfg(not(target_os = "windows"))]
fn automatic_base_candidates() -> Vec<PathBuf> {
    Vec::new()
}

pub fn auto_configure() -> Result<RuntimeBootstrapStatus, String> {
    if let Ok(config) = read_saved_config() {
        return status_from_config(config);
    }
    if control_port_in_use() {
        return Err("Port 8766 is already in use; automatic DataRoot selection was not attempted".to_string());
    }
    for candidate in automatic_base_candidates() {
        if validate_base_root(candidate.to_string_lossy().as_ref(), true).is_err() {
            continue;
        }
        let workspace = "production".to_string();
        let effective = candidate.join(&workspace);
        if validate_base_root(effective.to_string_lossy().as_ref(), true).is_err() {
            continue;
        }
        return activate_config(RuntimeBootstrapConfig {
            schema_version: BOOTSTRAP_SCHEMA_VERSION,
            base_data_root: candidate.display().to_string(),
            active_workspace: workspace,
            owner_confirmed: true,
            effective_data_root: None,
            binding_id: String::new(),
            binding_source: "automatic_safe_default".to_string(),
            binding_locked: false,
        });
    }
    Err("LingJi could not find a writable non-C: drive automatically".to_string())
}

fn read_runtime_ping() -> Result<RuntimePing, String> {
    let status = require_configured()?;
    let data_root = status
        .data_root_display
        .as_deref()
        .ok_or_else(|| "LingJi data directory is unavailable".to_string())?;
    let token_path = PathBuf::from(data_root)
        .join("storage")
        .join("control_api_token");
    let token = fs::read_to_string(&token_path)
        .map_err(|error| format!("Unable to read the expected Runtime token: {error}"))?;
    if token.trim().is_empty() {
        return Err("Expected Runtime token is empty".to_string());
    }

    let address = SocketAddr::new(IpAddr::V4(Ipv4Addr::LOCALHOST), CONTROL_PORT);
    let mut stream = TcpStream::connect_timeout(&address, Duration::from_millis(500))
        .map_err(|error| format!("Unable to reach LingJi Runtime for binding verification: {error}"))?;
    stream
        .set_read_timeout(Some(Duration::from_millis(900)))
        .map_err(|error| format!("Unable to configure Runtime read timeout: {error}"))?;
    stream
        .set_write_timeout(Some(Duration::from_millis(900)))
        .map_err(|error| format!("Unable to configure Runtime write timeout: {error}"))?;
    let request = format!(
        "GET /api/runtime/ping HTTP/1.1\r\nHost: 127.0.0.1:{CONTROL_PORT}\r\nX-LingJi-Token: {}\r\nConnection: close\r\n\r\n",
        token.trim()
    );
    stream
        .write_all(request.as_bytes())
        .map_err(|error| format!("Unable to send Runtime binding verification: {error}"))?;
    let mut bytes = Vec::new();
    stream
        .take(16 * 1024)
        .read_to_end(&mut bytes)
        .map_err(|error| format!("Unable to read Runtime binding verification: {error}"))?;
    let response = String::from_utf8(bytes)
        .map_err(|error| format!("Runtime binding verification was not UTF-8: {error}"))?;
    let (headers, body) = response
        .split_once("\r\n\r\n")
        .ok_or_else(|| "Runtime binding verification response was incomplete".to_string())?;
    if !headers.starts_with("HTTP/1.1 200") && !headers.starts_with("HTTP/1.0 200") {
        return Err("Runtime binding verification did not return HTTP 200".to_string());
    }
    serde_json::from_str(body)
        .map_err(|error| format!("Invalid Runtime binding verification payload: {error}"))
}

pub fn verify_runtime_binding() -> RuntimeBindingVerification {
    let status = match require_configured() {
        Ok(status) => status,
        Err(error) => {
            return RuntimeBindingVerification {
                verified: false,
                expected_data_root: None,
                actual_data_root: None,
                expected_workspace: None,
                actual_workspace: None,
                source: "unconfigured".to_string(),
                binding_id: None,
                binding_locked: false,
                error: Some(error),
            }
        }
    };
    let expected_data_root = status.data_root_display.clone();
    let expected_workspace = status.active_workspace.clone();
    let source = status.source.clone();
    let binding_id = status.binding_id.clone();
    let binding_locked = status.binding_locked;

    match read_runtime_ping() {
        Ok(actual) => {
            let root_matches = expected_data_root.as_deref().is_some_and(|expected| {
                normalized_identity(Path::new(expected))
                    == normalized_identity(Path::new(&actual.data_root))
            });
            let workspace_matches = expected_workspace
                .as_deref()
                .is_some_and(|expected| expected.eq_ignore_ascii_case(&actual.workspace));
            let status_ok = actual.status.eq_ignore_ascii_case("ok");
            let verified = root_matches && workspace_matches && status_ok;
            RuntimeBindingVerification {
                verified,
                expected_data_root,
                actual_data_root: Some(actual.data_root),
                expected_workspace,
                actual_workspace: Some(actual.workspace),
                source,
                binding_id,
                binding_locked,
                error: (!verified).then_some(
                    "Runtime responded from a different DataRoot or workspace; Desktop refused to adopt it"
                        .to_string(),
                ),
            }
        }
        Err(error) => RuntimeBindingVerification {
            verified: false,
            expected_data_root,
            actual_data_root: None,
            expected_workspace,
            actual_workspace: None,
            source,
            binding_id,
            binding_locked,
            error: Some(error),
        },
    }
}

pub fn require_verified_runtime() -> Result<RuntimeBindingVerification, String> {
    let verification = verify_runtime_binding();
    if verification.verified {
        Ok(verification)
    } else {
        Err(verification.error.clone().unwrap_or_else(|| {
            "LingJi Runtime DataRoot binding could not be verified".to_string()
        }))
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    fn config(schema_version: u32, owner_confirmed: bool) -> RuntimeBootstrapConfig {
        RuntimeBootstrapConfig {
            schema_version,
            base_data_root: "D:\\LingJiData".to_string(),
            active_workspace: "acceptance".to_string(),
            owner_confirmed,
            effective_data_root: None,
            binding_id: String::new(),
            binding_source: "owner_selection".to_string(),
            binding_locked: false,
        }
    }

    #[test]
    fn rejects_windows_system_drive_without_touching_it() {
        let error = validate_base_root(r"C:\LingJiData", false).unwrap_err();
        assert!(error.contains("C: drive"));
    }

    #[test]
    fn workspace_is_part_of_normal_effective_data_root() {
        let value = config(BOOTSTRAP_SCHEMA_VERSION, true);
        let base = PathBuf::from(r"D:\LingJiData");
        assert_eq!(
            effective_data_root(&value, &base, "acceptance"),
            base.join("acceptance")
        );
    }

    #[test]
    fn startup_contract_can_pin_exact_effective_root() {
        let mut value = config(BOOTSTRAP_SCHEMA_VERSION, true);
        value.effective_data_root = Some(r"D:\Task\product".to_string());
        let base = PathBuf::from(r"D:\ignored");
        assert_eq!(
            effective_data_root(&value, &base, "acceptance"),
            PathBuf::from(r"D:\Task\product")
        );
    }

    #[test]
    fn only_known_workspaces_are_allowed() {
        assert_eq!(validate_workspace("ACCEPTANCE").unwrap(), "acceptance");
        assert!(validate_workspace("shared").is_err());
    }

    #[test]
    fn legacy_confirmed_bootstrap_remains_accepted() {
        validate_config_contract(&config(LEGACY_BOOTSTRAP_SCHEMA_VERSION, true)).unwrap();
    }

    #[test]
    fn bootstrap_requires_approved_activation_policy() {
        let error = validate_config_contract(&config(BOOTSTRAP_SCHEMA_VERSION, false)).unwrap_err();
        assert!(error.contains("activation policy"));
    }

    #[test]
    fn locked_binding_requires_valid_id() {
        let mut value = config(BOOTSTRAP_SCHEMA_VERSION, true);
        value.binding_locked = true;
        assert!(validate_config_contract(&value).is_err());
        value.binding_id = "PR60:3e24e65c".to_string();
        assert!(validate_config_contract(&value).is_ok());
    }

    #[test]
    fn normalized_path_identity_is_case_and_slash_insensitive() {
        assert_eq!(
            normalized_identity(Path::new(r"D:\LingJi\acceptance\\")),
            normalized_identity(Path::new("d:/lingji/acceptance"))
        );
    }

    #[test]
    fn automatic_candidates_never_include_system_drive() {
        assert!(automatic_base_candidates()
            .iter()
            .all(|candidate| !looks_like_windows_system_drive(candidate)));
    }
}
