import json
import sys
from pathlib import Path

report = json.loads(Path(sys.argv[1]).read_text())
assert report.get("font") is True, report
assert report["bridge"] and report["buttons"] and report["rtl"] == "rtl", report
assert report["bodyWidth"] <= report["viewport"], report
print("Native bridge smoke passed")
