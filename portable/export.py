#!/usr/bin/env python3
import sys, os, shutil, json, zipfile
from pathlib import Path
from datetime import datetime

BASE_DIR = Path(__file__).parent.parent
BACKUP_ZIP = Path('lingji_backup.zip')


def export_backup():
    zip_path = BASE_DIR / BACKUP_ZIP
    files_to_zip = []

    # Source code
    for f in ['main.py', 'backup.py', 'run_service.py', 'start_lingji.py', 'requirements.txt', '.gitignore']:
        p = BASE_DIR / f
        if p.exists():
            files_to_zip.append((p, f))

    # src/
    for p in (BASE_DIR / 'src').rglob('*.py'):
        files_to_zip.append((p, 'src/' + str(p.relative_to(BASE_DIR / 'src'))))

    # vault/
    for p in (BASE_DIR / 'vault').rglob('*'):
        if p.is_file():
            files_to_zip.append((p, 'vault/' + str(p.relative_to(BASE_DIR / 'vault'))))

    # storage/
    for p in (BASE_DIR / 'storage').rglob('*'):
        if p.is_file():
            files_to_zip.append((p, 'storage/' + str(p.relative_to(BASE_DIR / 'storage'))))

    # logs/ (only structure)
    for p in (BASE_DIR / 'logs').rglob('*'):
        if p.is_file():
            files_to_zip.append((p, 'logs/' + str(p.relative_to(BASE_DIR / 'logs'))))

    # snapshot/
    for p in (BASE_DIR / 'snapshot').rglob('*'):
        if p.is_file():
            files_to_zip.append((p, 'snapshot/' + str(p.relative_to(BASE_DIR / 'snapshot'))))

    # Write zip
    with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zf:
        for src_path, arcname in files_to_zip:
            zf.write(src_path, arcname)

    manifest = {
        'export_time': datetime.now().isoformat(),
        'total_files': len(files_to_zip),
        'version': 'pemis-v5.2',
    }
    manifest_path = BASE_DIR / 'export_manifest.json'
    with open(manifest_path, 'w', encoding='utf-8') as f:
        json.dump(manifest, f, indent=2)

    print(f'Export complete: {zip_path}')
    print(f'  Files: {len(files_to_zip)}')
    print(f'  Size: {zip_path.stat().st_size / 1024:.1f} KB')
    return str(zip_path)


if __name__ == '__main__':
    export_backup()
