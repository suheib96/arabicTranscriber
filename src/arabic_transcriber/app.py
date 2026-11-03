import argparse
import json
from pathlib import Path

from .bridge import DesktopAPI


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--smoke", action="store_true", help="Launch and exercise native bridge, then close"
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
        str(Path(__file__).parent / "ui" / "index.html"),
        js_api=api,
        width=1060,
        height=800,
        min_size=(760, 600),
        background_color="#f6f5f1",
    )
    api.window = window
    window.events.closing += lambda: api.cancel()

    def smoke():
        import time

        time.sleep(2)
        import threading

        completed = threading.Event()
        report = {}

        def received(value):
            report.update(value)
            completed.set()

        window.evaluate_js("window.desktopSmoke()", callback=received)
        completed.wait(15)
        if args.smoke_report:
            args.smoke_report.parent.mkdir(parents=True, exist_ok=True)
            args.smoke_report.write_text(json.dumps(report, ensure_ascii=False), encoding="utf-8")
        window.destroy()

    webview.start(smoke if args.smoke else None, debug=False)


if __name__ == "__main__":
    main()
