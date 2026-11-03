"""Make a static instance for Word/LibreOffice, which vary in variable-font support."""

from pathlib import Path

from fontTools.ttLib import TTFont
from fontTools.varLib.instancer import instantiateVariableFont

for path in Path("src/arabic_transcriber/fonts").glob("*.ttf"):
    font = TTFont(path)
    if "fvar" in font:
        static = instantiateVariableFont(font, {"wght": 400, "wdth": 100}, inplace=False)
        static.save(path)
