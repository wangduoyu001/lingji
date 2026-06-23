import sys, os, time, logging
from pathlib import Path

BASE_DIR = Path(__file__).parent
sys.path.insert(0, str(BASE_DIR))

(BASE_DIR / 'logs').mkdir(exist_ok=True)

logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(name)s] %(levelname)s: %(message)s',
    handlers=[logging.FileHandler(str(BASE_DIR / 'logs' / 'lingji_service.log'), encoding='utf-8'), logging.StreamHandler()])
logger = logging.getLogger('lingji.service')

from main import PEMISCore

core = None

def start():
    global core
    logger.info('LingJi v6 starting...')
    core = PEMISCore()
    core.start()
    logger.info('LingJi v6 started')

def stop():
    global core
    if core:
        core.stop()
    logger.info('LingJi stopped')

if __name__ == '__main__':
    start()
    try:
        while True:
            time.sleep(10)
    except KeyboardInterrupt:
        stop()
