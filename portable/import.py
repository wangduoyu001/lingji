#!/usr/bin/env python3
import sys, os, shutil, json, zipfile
from pathlib import Path
from datetime import datetime

BASE_DIR = Path(__file__).parent.parent
BACKUP_ZIP = BASE_DIR / 'lingji_backup.zip'


def import_backup(zip_path=None):
    if zip_path is None:
        zip_path = BACKUP_ZIP
    zip_path = Path(zip_path)

    if not zip_path.exists():
        print(f'Error: {zip_path} not found')
        return False

    print(f'Restoring from: {zip_path}')
    restore_map = {
        'src/': BASE_DIR / 'src',
        'vault/': BASE_DIR / 'vault',
        'storage/': BASE_DIR / 'storage',
        'logs/': BASE_DIR / 'logs',
        'snapshot/': BASE_DIR / 'snapshot',
    }

    with zipfile.ZipFile(zip_path, 'r') as zf:
        namelist = zf.namelist()
        for name in namelist:
            for prefix, dest_dir in restore_map.items():
                if name.startswith(prefix) and not name.endswith('/'):
                    rel = name[len(prefix):]
                    dest = dest_dir / rel
                    dest.parent.mkdir(parents=True, exist_ok=True)
                    zf.extract(name, BASE_DIR)
                    break
            else:
                # root files
                if '/' not in name:
                    zf.extract(name, BASE_DIR)

    print(f'Restore complete: {len(namelist)} files extracted')
    print('')
    print('Run: pip install -r requirements.txt')
    print('Run: python main.py')
    return True


if __name__ == '__main__':
    import sys
    if len(sys.argv) > 1:
        import_backup(sys.argv[1])
    else:
        import_backup()
