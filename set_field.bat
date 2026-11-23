@echo off
rem Change a scheme, e.g.:  set_field.bat BR-02 status="Suspended"
rem                         set_field.bat VL-04 next_deadline=2027-03-15
rem                         set_field.bat BR-02 --verified
cd /d "%~dp0"
call "%~dp0_env.bat" || (pause & exit /b 1)
set "PY=%~dp0.venv\Scripts\python.exe"
if "%~1"=="" (
  "%PY%" -m scraper.set_field --help
  pause
  exit /b 0
)
"%PY%" -m scraper.set_field %* && "%PY%" site\build_site.py
