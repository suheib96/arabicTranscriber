"""Fetch pinned Node with upstream SHA256; copy the wheel's platform FFmpeg."""

import hashlib
import json
import platform
import shutil
import subprocess
import tarfile
import urllib.request
import zipfile
from pathlib import Path

import imageio_ffmpeg

NODE_VERSION = "24.13.0"
ROOT = Path(__file__).resolve().parents[1]
TARGET = ROOT / "build" / "tools"


def fetch(url, path):
    if not path.exists():
        with urllib.request.urlopen(url, timeout=90) as source, path.open("wb") as output:
            shutil.copyfileobj(source, output)


def main():
    TARGET.mkdir(parents=True, exist_ok=True)
    system = platform.system()
    arch = {"arm64": "arm64", "aarch64": "arm64", "AMD64": "x64", "x86_64": "x64"}[
        platform.machine()
    ]
    os_name = {"Darwin": "darwin", "Windows": "win"}[system]
    extension = "zip" if system == "Windows" else "tar.gz"
    name = f"node-v{NODE_VERSION}-{os_name}-{arch}"
    archive_name = name + "." + extension
    base = f"https://nodejs.org/dist/v{NODE_VERSION}/"
    archive = TARGET.parent / archive_name
    checksums = TARGET.parent / f"node-{NODE_VERSION}-SHASUMS256.txt"
    fetch(base + "SHASUMS256.txt", checksums)
    expected = next(
        line.split()[0]
        for line in checksums.read_text().splitlines()
        if line.split()[-1] == archive_name
    )
    fetch(base + archive_name, archive)
    if hashlib.sha256(archive.read_bytes()).hexdigest() != expected:
        raise RuntimeError("Node checksum mismatch. Remove the cached archive and retry.")
    if system == "Windows":
        with zipfile.ZipFile(archive) as bundle:
            node = bundle.read(name + "/node.exe")
            license_text = bundle.read(name + "/LICENSE")
    else:
        with tarfile.open(archive) as bundle:
            node = bundle.extractfile(name + "/bin/node").read()
            license_text = bundle.extractfile(name + "/LICENSE").read()
    node_path = TARGET / ("node.exe" if system == "Windows" else "node")
    node_path.write_bytes(node)
    node_path.chmod(0o755)
    (TARGET / "NODE-LICENSE.txt").write_bytes(license_text)
    ffmpeg = Path(imageio_ffmpeg.get_ffmpeg_exe())
    ffmpeg_target = TARGET / ("ffmpeg.exe" if system == "Windows" else "ffmpeg")
    shutil.copy2(ffmpeg, ffmpeg_target)
    ffmpeg_target.chmod(0o755)
    ffmpeg_version = subprocess.check_output(
        [str(ffmpeg_target), "-version"], text=True
    ).splitlines()[0]
    (TARGET / "versions.json").write_text(
        json.dumps(
            {
                "node": NODE_VERSION,
                "node_archive_sha256": expected,
                "ffmpeg": ffmpeg_version,
                "ffmpeg_binary_sha256": hashlib.sha256(ffmpeg_target.read_bytes()).hexdigest(),
                "platform": system,
                "arch": arch,
            },
            indent=2,
        )
    )
    print(f"Tools ready: {system} {arch}; {ffmpeg_version}")


if __name__ == "__main__":
    main()
