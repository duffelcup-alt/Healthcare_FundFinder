@echo off
rem Used by the scheduled task. Writes a log instead of showing output.
cd /d "%~dp0"
if not exist logs mkdir logs
call "%~dp0_env.bat" > "logs\last_run.log" 2>&1 || exit /b 1
set "PY=%~dp0.venv\Scripts\python.exe"
echo Run started %date% %time% >> "logs\last_run.log"
"%PY%" -m scraper.run --apply >> "logs\last_run.log" 2>&1
"%PY%" site\build_site.py >> "logs\last_run.log" 2>&1
echo Run finished %date% %time% >> "logs\last_run.log"
