"""Run before PyInstaller, only in trusted CI with explicit secret configuration."""

import base64
import os
import secrets
import subprocess
import tempfile
from pathlib import Path

encoded = os.environ.get("APPLE_CERTIFICATE_P12_BASE64")
if encoded:
    keychain = str(Path(os.environ["RUNNER_TEMP"]) / "arabic-transcriber-signing.keychain-db")
    password = secrets.token_urlsafe(32)

    def run(*args):
        try:
            subprocess.run(
                list(args), check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
            )
        except subprocess.CalledProcessError:
            raise RuntimeError(
                "Certificate import failed; credentials omitted from logs."
            ) from None

    with tempfile.TemporaryDirectory() as temporary:
        cert = Path(temporary) / "certificate.p12"
        cert.write_bytes(base64.b64decode(encoded))
        cert.chmod(0o600)
        run("security", "create-keychain", "-p", password, keychain)
        run("security", "set-keychain-settings", "-lut", "21600", keychain)
        run("security", "unlock-keychain", "-p", password, keychain)
        run(
            "security",
            "import",
            str(cert),
            "-P",
            os.environ["APPLE_CERTIFICATE_PASSWORD"],
            "-A",
            "-t",
            "cert",
            "-f",
            "pkcs12",
            "-k",
            keychain,
        )
        run(
            "security",
            "set-key-partition-list",
            "-S",
            "apple-tool:,apple:",
            "-k",
            password,
            keychain,
        )
        run("security", "list-keychains", "-d", "user", "-s", keychain)
    print("Temporary signing keychain ready.")
