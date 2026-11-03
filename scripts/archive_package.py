"""Create distributable archives/checksums after optional signing."""

import hashlib
import platform
import shutil
import subprocess
from pathlib import Path

root = Path(__file__).resolve().parents[1]
dist = root / "dist"
release = dist / "release"
release.mkdir(exist_ok=True)
arch = platform.machine().lower()
if platform.system() == "Darwin":
    name = f"ArabicTranscriber-macOS-{arch}"
    archive = release / (name + ".zip")
    subprocess.run(
        [
            "ditto",
            "-c",
            "-k",
            "--sequesterRsrc",
            "--keepParent",
            str(dist / "Arabic Transcriber.app"),
            str(archive),
        ],
        check=True,
    )
else:
    name = f"ArabicTranscriber-Windows-{arch}"
    shutil.make_archive(str(release / name), "zip", dist, "Arabic Transcriber")
for file in release.iterdir():
    if file.suffix in (".zip", ".exe", ".dmg"):
        checksum = hashlib.file_digest(file.open("rb"), "sha256").hexdigest()
        file.with_suffix(file.suffix + ".sha256").write_text(f"{checksum}  {file.name}\n")
print(release)
