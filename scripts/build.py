"""Build native bundle on this OS; downloads tools, never model weights."""

import subprocess
import sys
from pathlib import Path

root = Path(__file__).resolve().parents[1]
for command in (
    [sys.executable, str(root / "scripts/prepare_tools.py")],
    [sys.executable, "-m", "PyInstaller", "--noconfirm", str(root / "ArabicTranscriber.spec")],
    [sys.executable, str(root / "scripts/sign_macos.py")] if sys.platform == "darwin" else None,
    [sys.executable, str(root / "scripts/archive_package.py")],
):
    if command:
        subprocess.run(command, cwd=root, check=True)
