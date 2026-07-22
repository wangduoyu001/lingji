use std::env;

fn export_build_value(name: &str, fallback: &str) {
    let value = env::var(name).unwrap_or_else(|_| fallback.to_string());
    let sanitized = value.replace('\r', " ").replace('\n', " ");
    println!("cargo:rustc-env={name}={sanitized}");
    println!("cargo:rerun-if-env-changed={name}");
}

fn main() {
    export_build_value("LINGJI_BUILD_COMMIT", "development");
    export_build_value("LINGJI_BUILD_TIME_UTC", "unknown");
    export_build_value("LINGJI_BUILD_CHANNEL", "development");
    export_build_value("LINGJI_BUILD_TARGET", "local");
    export_build_value("LINGJI_BUILD_SIGNED", "false");
    tauri_build::build()
}
