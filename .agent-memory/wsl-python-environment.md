---
name: wsl-python-environment
description: Windows-side Python is a broken WindowsApps stub; user runs Python work in WSL
metadata:
  type: user
---

On Windows, `python` in Git Bash resolves to the WindowsApps stub
(`/c/Users/Muhajir/AppData/Local/Microsoft/WindowsApps/python`) and fails with
Permission denied. The user runs Python from **WSL** instead. This repo was recloned to
`~/hajir` in WSL (originally worked on at
`c:/Users/Muhajir/Downloads/quranic-corpus-morphology-0.4` on Windows) — do Python work
there. Also useful: on Windows, WinRAR's UnRAR exists at
`C:\Program Files\WinRAR\UnRAR.exe` (no 7z in PATH); in WSL prefer `unrar`/`7z` from apt.
