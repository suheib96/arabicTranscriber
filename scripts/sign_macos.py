"""Ad-hoc verification plus optional Developer ID notarization for trusted releases."""

import os
import plistlib
import subprocess
import tempfile
from pathlib import Path


def run(*args):
    try:
        subprocess.run(list(args), check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    except subprocess.CalledProcessError:
        raise RuntimeError(f"{args[0]} failed; credentials omitted from logs.") from None


def main():
    # Enforce the minimum required by locked PyTorch/NumPy wheels before signing.
    info_path = Path("dist/Arabic Transcriber.app/Contents/Info.plist")
    with info_path.open("rb") as stream:
        info = plistlib.load(stream)
    if info.get("LSMinimumSystemVersion") != "14.0":
        info["LSMinimumSystemVersion"] = "14.0"
        with info_path.open("wb") as stream:
            plistlib.dump(info, stream)
    identity = os.environ.get("APPLE_SIGN_IDENTITY")
    if not identity:
        app = Path("dist/Arabic Transcriber.app")
        run("codesign", "--force", "--deep", "--sign", "-", "--timestamp=none", str(app))
        run("codesign", "--verify", "--deep", "--strict", str(app))
        print("Ad-hoc signature verified. No Developer ID / notarization.")
        return
    # PyInstaller must already have used the identity for every nested binary.
    app = Path("dist/Arabic Transcriber.app")
    run("codesign", "--verify", "--deep", "--strict", str(app))
    if not os.environ.get("APPLE_ID"):
        print("Developer ID signed; notarization not configured.")
        return
    with tempfile.TemporaryDirectory() as temporary:
        archive = str(Path(temporary) / "notarize.zip")
        run("ditto", "-c", "-k", "--keepParent", str(app), archive)
        run(
            "xcrun",
            "notarytool",
            "submit",
            archive,
            "--apple-id",
            os.environ["APPLE_ID"],
            "--team-id",
            os.environ["APPLE_TEAM_ID"],
            "--password",
            os.environ["APPLE_APP_PASSWORD"],
            "--wait",
            "--timeout",
            "30m",
        )
    run("xcrun", "stapler", "staple", str(app))
    run("spctl", "--assess", "--type", "execute", str(app))
    print("Notarization and stapling completed.")


if __name__ == "__main__":
    main()
