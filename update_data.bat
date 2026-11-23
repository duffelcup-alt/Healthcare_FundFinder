@echo off
title Healthcare Fund Finder - checking sources
cd /d "%~dp0"
call "%~dp0_env.bat" || (pause & exit /b 1)
set "PY=%~dp0.venv\Scripts\python.exe"
echo Checking every scheme page. This takes a few minutes (the scraper waits between requests)...
echo.
"%PY%" -m scraper.run --apply || (echo The check failed. See the message above. & pause & exit /b 1)
"%PY%" site\build_site.py || (pause & exit /b 1)
echo.
echo Done. Opening the updates page.
start "" "%~dp0site\public\updates.html"
timeout /t 5 >nul
