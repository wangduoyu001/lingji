#!/usr/bin/env python3
from __future__ import annotations

import logging
import sys
import time
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(BASE_DIR))

from src.config import settings
from src.extraction import ExtractionWorker, build_extraction_pipeline

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(name)s] %(levelname)s: %(message)s")


def main() -> int:
    pipeline = build_extraction_pipeline(settings)
    worker = ExtractionWorker(
        pipeline,
        poll_seconds=settings.extraction_poll_seconds,
        batch_size=settings.extraction_batch_size,
    )
    worker.start()
    try:
        while worker.running:
            time.sleep(1)
    except KeyboardInterrupt:
        worker.stop()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
