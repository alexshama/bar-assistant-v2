"""
Pytest helpers for local sandbox-compatible test runs.
"""

from __future__ import annotations

import os
import sys
import tempfile
import types
import uuid
from pathlib import Path


TEST_TMP_DIR = Path(__file__).resolve().parent / ".tmp"
TEST_TMP_DIR.mkdir(parents=True, exist_ok=True)

tempfile.tempdir = str(TEST_TMP_DIR)
os.environ.setdefault("TMP", str(TEST_TMP_DIR))
os.environ.setdefault("TEMP", str(TEST_TMP_DIR))
os.environ.setdefault("TMPDIR", str(TEST_TMP_DIR))

os.environ.setdefault("TELEGRAM_BOT_TOKEN", "test-token")
os.environ.setdefault("OPENAI_API_KEY", "test-openai-key")
os.environ.setdefault("OPENROUTER_API_KEY", "test-openrouter-key")


def _workspace_mkdtemp(*args, **kwargs) -> str:
    del args, kwargs
    path = TEST_TMP_DIR / f"tmp{uuid.uuid4().hex}"
    path.mkdir(parents=True, exist_ok=False)
    return str(path)


tempfile.mkdtemp = _workspace_mkdtemp


if "pydub" not in sys.modules:
    pydub_module = types.ModuleType("pydub")

    class _AudioSegment:
        @staticmethod
        def from_ogg(*args, **kwargs):  # pragma: no cover - replaced by mocks in tests
            raise RuntimeError("pydub stub should be mocked in tests")

    pydub_module.AudioSegment = _AudioSegment
    sys.modules["pydub"] = pydub_module
