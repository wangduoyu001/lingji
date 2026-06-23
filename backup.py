import shutil, json, logging
from pathlib import Path
from datetime import datetime

BASE_DIR = Path(__file__).parent
BACKUP_ROOT = Path('D:/codex/backups/pemis')

logging.basicConfig(level=logging.INFO, format='%(asctime)s [backup] %(message)s')
logger = logging.getLogger('backup')


def backup_code():
    ts = datetime.now().strftime('%Y%m%d_%H%M%S')
    dest = BACKUP_ROOT / 'code' / ('src_' + ts)
    dest.mkdir(parents=True, exist_ok=True)
    for f in ['main.py', 'backup.py', 'run_service.py', 'start_lingji.py', 'start_lingji.bat', 'requirements.txt', '.gitignore']:
        src = BASE_DIR / f
        if src.exists():
            shutil.copy2(src, dest / f)
    src_dir = BASE_DIR / 'src'
    if src_dir.exists():
        shutil.copytree(src_dir, dest / 'src', dirs_exist_ok=True)
    pdir = BASE_DIR / 'portable'
    if pdir.exists():
        shutil.copytree(pdir, dest / 'portable', dirs_exist_ok=True)
    logger.info('Code backup: %s', dest)
    return str(dest)


def backup_data():
    ts = datetime.now().strftime('%Y%m%d_%H%M%S')
    dest = BACKUP_ROOT / 'data' / ('data_' + ts)
    dest.mkdir(parents=True, exist_ok=True)
    for d in ['storage', 'logs']:
        src = BASE_DIR / d
        if src.exists():
            shutil.copytree(src, dest / d, dirs_exist_ok=True)
    logger.info('Data backup: %s', dest)
    return str(dest)


def backup_vault():
    ts = datetime.now().strftime('%Y%m%d_%H%M%S')
    dest = BACKUP_ROOT / 'snapshots' / ('vault_' + ts)
    dest.mkdir(parents=True, exist_ok=True)
    src = BASE_DIR / 'vault'
    if src.exists():
        shutil.copytree(src, dest, dirs_exist_ok=True)
    logger.info('Vault snapshot: %s', dest)
    return str(dest)


def cleanup_old(keep_days=14):
    now = datetime.now().timestamp()
    for subdir in list(BACKUP_ROOT.rglob('*')):
        if subdir.is_dir() and any(subdir.name.startswith(p) for p in ['src_', 'data_', 'vault_']):
            age = (now - subdir.stat().st_mtime) / 86400
            if age > keep_days:
                shutil.rmtree(subdir, ignore_errors=True)
                logger.info('Removed old: %s', subdir)


def full_backup():
    manifest = {
        'timestamp': datetime.now().isoformat(),
        'paths': {'code': backup_code(), 'data': backup_data(), 'vault': backup_vault()}
    }
    mf = BACKUP_ROOT / ('manifest_' + datetime.now().strftime('%Y%m%d_%H%M%S') + '.json')
    with open(mf, 'w', encoding='utf-8') as f:
        json.dump(manifest, f, ensure_ascii=False, indent=2)
    cleanup_old()
    logger.info('Full backup complete')
    return manifest


if __name__ == '__main__':
    full_backup()
