#!/usr/bin/env python3
"""CI gate for the package path reported by ``ue-kb doctor``.

The command intentionally points at a unique missing index: this verifies the
runtime package identity without downloading a model or mutating an index.
"""

from __future__ import annotations

import json
import os
import platform
import subprocess
import sys
import uuid
from pathlib import Path


def main() -> int:
    mode = os.environ.get("UE_KB_EXPECT_PACKAGE_MODE")
    if mode not in {"source", "wheel"}:
        raise SystemExit("UE_KB_EXPECT_PACKAGE_MODE must be source or wheel")
    token = uuid.uuid4().hex
    if platform.system() == "Windows":
        missing_db = Path(f"C:/ue-kb-doctor-missing-{token}")
    else:
        missing_db = Path(f"/tmp/ue-kb-doctor-missing-{token}")
    result = subprocess.run(
        [
            sys.executable, "-m", "ue_knowledge.cli", "doctor", "--json",
            "--db", str(missing_db),
        ],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        env={**os.environ, "PYTHONIOENCODING": "utf-8"},
        timeout=30,
    )
    if result.returncode != 1:
        raise SystemExit(
            f"doctor expected rc=1, got {result.returncode}: {result.stderr}"
        )
    payload = json.loads(result.stdout)
    module_path = Path(payload["package"]["module_path"])
    if mode == "source":
        source_root = Path(__file__).resolve().parents[1] / "src"
        if not module_path.is_relative_to(source_root):
            raise SystemExit(f"doctor imported outside checkout: {module_path}")
    elif "site-packages" not in str(module_path).lower():
        raise SystemExit(f"doctor did not import an installed package: {module_path}")
    print(f"doctor identity ok ({mode}): {module_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
