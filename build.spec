# -*- mode: python ; coding: utf-8 -*-

block_cipher = None

from PyInstaller.utils.hooks import collect_submodules

hiddenimports = collect_submodules('pydantic')
hiddenimports.extend([
    'ffmpeg_encoder',
    'ffmpeg_encoder.app',
    'ffmpeg_encoder.ui',
    'ffmpeg_encoder.ui.main_window',
    'ffmpeg_encoder.ui.queue_panel',
    'ffmpeg_encoder.ui.settings_panel',
    'ffmpeg_encoder.ui.log_panel',
    'ffmpeg_encoder.ui.rename_dialog',
    'ffmpeg_encoder.ui.flamenco_dialog',
    'ffmpeg_encoder.core',
    'ffmpeg_encoder.core.ffmpeg_cmd',
    'ffmpeg_encoder.core.ffprobe',
    'ffmpeg_encoder.core.presets',
    'ffmpeg_encoder.core.queue',
    'ffmpeg_encoder.core.batch_rename',
    'ffmpeg_encoder.core.runner',
    'ffmpeg_encoder.utils',
    'ffmpeg_encoder.utils.env',
    'ffmpeg_encoder.utils.logger',
    'ffmpeg_encoder.utils.ffmpeg_check',
    'ffmpeg_encoder.integrations',
    'ffmpeg_encoder.integrations.flamenco_client',
])

a = Analysis(
    ['main.py'],
    pathex=['.'],
    binaries=[],
    datas=[],
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
)
pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)
exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='FFmpegEncoder_v2',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=True,
    disable_windowed_traceback=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
