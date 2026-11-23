@echo off
rem Shared setup: finds Python, creates .venv on first use, installs packages.
cd /d "%~dp0"
if exist ".venv\Scripts\python.exe" goto have_venv
set "PYLAUNCH="
py -3 --version >nul 2>&1 && set "PYLAUNCH=py -3"
if not defined PYLAUNCH python --version >nul 2>&1 && set "PYLAUNCH=python"
if not defined PYLAUNCH (
  echo.
  echo Python is not installed on this computer.
  echo Install it from https://www.python.org/downloads/  ^(tick "Add python.exe to PATH"^)
  echo or open a terminal and run:  winget install Python.Python.3.12
  echo Then double-click this file again.
  exit /b 1
)
echo First run: setting up a private Python environment. This takes a minute...
%PYLAUNCH% -m venv .venv || exit /b 1
:have_venv
set "PY=%~dp0.venv\Scripts\python.exe"
if not exist ".venv\installed.txt" (
  "%PY%" -m pip install --disable-pip-version-check -q -r requirements-local.txt || exit /b 1
  echo ok> ".venv\installed.txt"
)
exit /b 0
