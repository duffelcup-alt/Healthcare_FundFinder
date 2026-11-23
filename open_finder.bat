@echo off
title Healthcare Fund Finder
cd /d "%~dp0"
if not exist "site\public\index.html" (
  call "%~dp0_env.bat" || (pause & exit /b 1)
  "%~dp0.venv\Scripts\python.exe" site\build_site.py || (pause & exit /b 1)
)
start "" "%~dp0site\public\index.html"
