# _exec.py - PEMIS write executor (UTF-8 safe)
# Usage: python scripts/_exec.py <target_file>
# Reads stdin as file content, writes with clean UTF-8 no BOM
import sys, os, shutil
if len(sys.argv) < 2:
    print('Usage: python scripts/_exec.py <target_file>')
    sys.exit(1)
target = sys.argv[1]
content = sys.stdin.read()
# Remove any BOM
if content.startswith('\ufeff'):
    content = content[1:]
os.makedirs(os.path.dirname(target) or '.', exist_ok=True)
with open(target, 'w', encoding='utf-8') as f:
    f.write(content)
print(f'Written {len(content)} bytes to {target}')
