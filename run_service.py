import sys
import os
import time
import logging
from pathlib import Path

# Add project root to path
BASE_DIR = Path(__file__).parent.parent
sys.path.insert(0, str(BASE_DIR))

from src.config import settings
from main import PEMISCore

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(name)s] %(levelname)s: %(message)s',
    handlers=[
        logging.FileHandler(BASE_DIR / 'logs' / 'lingji_service.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger('lingji.service')

class LingJiService:
    def __init__(self):
        self.core = None
        self.running = False

    def start(self):
        logger.info('LingJi service starting...')
        self.core = PEMISCore()
        self.core.start()
        self.running = True
        logger.info('LingJi service started successfully')

    def stop(self):
        logger.info('LingJi service stopping...')
        if self.core:
            self.core.stop()
        self.running = False
        logger.info('LingJi service stopped')

    def run_forever(self):
        self.start()
        try:
            while self.running:
                time.sleep(10)
        except KeyboardInterrupt:
            self.stop()

if __name__ == '__main__':
    svc = LingJiService()
    svc.run_forever()
