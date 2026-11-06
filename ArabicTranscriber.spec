# Build on the target OS and architecture. Weights/cache/tokens are never included.
import os
from pathlib import Path
from PyInstaller.utils.hooks import collect_data_files, collect_submodules, copy_metadata

root = Path(SPECPATH)
data = [(str(root / 'src/arabic_transcriber/ui'), 'arabic_transcriber/ui'),
        (str(root / 'src/arabic_transcriber/fonts'), 'arabic_transcriber/fonts'),
        (str(root / 'docs/THIRD_PARTY.md'), 'licenses'),
        (str(root / 'LICENSE'), 'licenses'),
        (str(root / 'build/tools/NODE-LICENSE.txt'), 'licenses'),
        (str(root / 'build/tools/versions.json'), 'tools')]
# Transformers uses lazy imports and inspects source files. Ship sources, not every ASR model's deps.
for package in ('transformers', 'librosa', 'yt_dlp', 'yt_dlp_ejs'):
    data += collect_data_files(package, include_py_files=True)
for package in ('transformers', 'torch', 'huggingface_hub', 'tokenizers', 'safetensors',
                'regex', 'numpy', 'tqdm', 'requests', 'packaging', 'pyyaml', 'filelock',
                'librosa', 'scipy', 'numba', 'llvmlite', 'scikit-learn', 'fpdf2', 'python-docx', 'yt-dlp', 'yt-dlp-ejs', 'sentencepiece', 'accelerate'):
    data += copy_metadata(package)
hidden = ['transformers.models.auto.processing_auto',
          'transformers.models.cohere_asr.configuration_cohere_asr',
          'transformers.models.cohere_asr.feature_extraction_cohere_asr',
          'transformers.models.cohere_asr.modeling_cohere_asr',
          'transformers.models.cohere_asr.processing_cohere_asr',
          'librosa', 'sentencepiece', 'safetensors.torch', 'uharfbuzz', 'soundfile', 'pyperclip',
          'arabic_transcriber.model']
hidden += collect_submodules('yt_dlp_ejs')
suffix = '.exe' if os.name == 'nt' else ''
binaries = [(str(root / 'build/tools' / (tool + suffix)), 'tools') for tool in ('node','ffmpeg')]
a = Analysis([str(root / 'scripts/desktop_entry.py')], pathex=[str(root / 'src')],
             binaries=binaries, datas=data, hiddenimports=hidden,
             excludes=['pytest', 'tkinter', 'matplotlib', 'IPython', 'pandas',
                       'torchvision', 'torchaudio', 'PyQt5', 'PyQt6', 'PySide6'])
pyz = PYZ(a.pure)
exe = EXE(pyz, a.scripts, [], exclude_binaries=True, name='Arabic Transcriber',
          debug=False, bootloader_ignore_signals=False, strip=False, upx=False,
          console=False, codesign_identity=os.environ.get('APPLE_SIGN_IDENTITY') or None,
          entitlements_file=str(root / 'scripts/entitlements.plist') if os.environ.get('APPLE_SIGN_IDENTITY') else None)
if os.name == 'nt':
    coll = COLLECT(exe, a.binaries, a.datas, strip=False, upx=False, name='Arabic Transcriber')
else:
    app = BUNDLE(exe, a.binaries, a.datas, name='Arabic Transcriber.app', bundle_identifier='org.arabictranscriber.desktop',
                 info_plist={'NSHighResolutionCapable': True, 'LSMinimumSystemVersion': '14.0',
                             'CFBundleShortVersionString':'0.2.0',
                             'NSHumanReadableCopyright':'Arabic Transcriber contributors'},
                 codesign_identity=os.environ.get('APPLE_SIGN_IDENTITY') or None)
