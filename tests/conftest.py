# conftest - disable real Obsidian CLI tests in this environment
import os
os.environ.setdefault('OBSIDIAN_VAULT_PATH', '')
os.environ.setdefault('SECOND_BRAIN_OBSIDIAN_DIR', '')
