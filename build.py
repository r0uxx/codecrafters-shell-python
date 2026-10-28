"""
Builds a standalone `codecrafters-shell` executable for the current OS with PyInstaller.

PyInstaller can't cross-compile, so run this on each OS (and CPU type) you want a binary for:

    uv run --group build python build.py

On Windows this also bundles pyreadline3 (a project dependency there), which provides tab completion.
The executable ends up in dist/ (dist/codecrafters-shell.exe on Windows).
.github/workflows/build.yml does this for Linux, macOS and Windows automatically.

macOS signing: set CODESIGN_IDENTITY to your "Developer ID Application: Name (TEAMID)" certificate
and the binary is signed with the hardened runtime, ready for notarization. Without it, it's ad-hoc signed.
"""
import os
import sys
from pathlib import Path

import PyInstaller.__main__

ROOT = Path(__file__).resolve().parent

options = [
    str(ROOT / "app" / "main.py"),
    "--name", "codecrafters-shell",
    "--onefile",
    "--console",
    "--paths", str(ROOT),
    "--specpath", str(ROOT / "build"),
    "--distpath", str(ROOT / "dist"),
    "--workpath", str(ROOT / "build"),
    "--clean",
    "--noconfirm",
]

if sys.platform == "darwin" and (identity := os.environ.get("CODESIGN_IDENTITY")):
    options += [
        "--codesign-identity", identity,
        "--osx-entitlements-file", str(ROOT / "entitlements.plist"),
    ]

PyInstaller.__main__.run(options)
