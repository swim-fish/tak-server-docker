"""Ensure scheduled and foreground workers cannot consume one queue together."""

from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from host_worker_lock import exclusive_worker


class HostWorkerLockTests(unittest.TestCase):
    def test_duplicate_worker_is_rejected_and_lock_is_reusable(self) -> None:
        runtime = Path(__file__).resolve().parents[2] / "runtime"
        with tempfile.TemporaryDirectory(dir=runtime) as directory:
            control = Path(directory)
            with exclusive_worker(control):
                with self.assertRaisesRegex(RuntimeError, "already running"):
                    with exclusive_worker(control):
                        self.fail("Duplicate worker acquired the queue")
            with exclusive_worker(control):
                pass


if __name__ == "__main__":
    unittest.main()
