import argparse
import base64
import json
from pathlib import Path

from .bridge import DesktopAPI


def ui_document():
    """Inline trusted local assets so the desktop needs no HTTP listener."""
    root = Path(__file__).parent
    html = (root / "ui/index.html").read_text("utf-8")
    css = (root / "ui/style.css").read_text("utf-8")
    font = base64.b64encode((root / "fonts/NotoSansArabic.ttf").read_bytes()).decode("ascii")
    css = css.replace("url('../fonts/NotoSansArabic.ttf')", f"url(data:font/ttf;base64,{font})")
    script = (root / "ui/app.js").read_text("utf-8")
    return html.replace(
        '<link rel="stylesheet" href="style.css">', "<style>" + css + "</style>"
    ).replace('<script src="app.js"></script>', "<script>" + script + "</script>")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--smoke", action="store_true", help="Launch native bridge check, then close"
    )
    parser.add_argument("--smoke-report", type=Path)
    parser.add_argument("--self-check", action="store_true")
    args = parser.parse_args()
    if args.self_check:
        from .diagnostics import self_check

        raise SystemExit(0 if self_check(args.smoke_report or Path("package-check.json")) else 1)
    import webview

    api = DesktopAPI()
    window = webview.create_window(
        "Arabic Transcriber",
        html=ui_document(),
        js_api=api,
        width=1060,
        height=800,
        min_size=(760, 600),
        background_color="#f6f5f1",
    )
    api.window = window
    window.events.closing += lambda: api.cancel()

    def smoke():
        import os
        import threading

        completed = threading.Event()
        report = {}

        def received(value):
            report.update(value)
            completed.set()

        try:
            if not window.events.loaded.wait(30):
                raise RuntimeError("Native document did not load within 30 seconds")
            window.evaluate_js("window.desktopSmoke()", callback=received)
            if not completed.wait(15):
                raise RuntimeError("Native bridge did not reply within 15 seconds")
        except Exception as error:
            report["error"] = str(error)
        if args.smoke_report:
            args.smoke_report.parent.mkdir(parents=True, exist_ok=True)
            args.smoke_report.write_text(json.dumps(report, ensure_ascii=False), encoding="utf-8")
        if "error" in report:
            # Test mode only: never leave a hung CI desktop process behind.
            os._exit(1)
        window.destroy()

    webview.start(smoke if args.smoke else None, debug=False)


if __name__ == "__main__":
    main()
