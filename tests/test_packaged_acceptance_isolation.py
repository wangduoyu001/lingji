from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from run_packaged_control_api import configure_packaged_environment


class PackagedAcceptanceIsolationTests(unittest.TestCase):
    def test_acceptance_override_rejects_a_root_outside_the_task_directory(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            task_root = root / "task-root" / "runtime-data"
            rogue_root = root / "Documents" / "acceptance"

            with self.assertRaisesRegex(ValueError, "LINGJI_ACCEPTANCE_DATA_ROOT"):
                configure_packaged_environment(
                    rogue_root,
                    workspace="acceptance",
                    environ={"LINGJI_ACCEPTANCE_DATA_ROOT": str(task_root)},
                )


if __name__ == "__main__":
    unittest.main()
