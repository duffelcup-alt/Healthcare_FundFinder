@echo off
cd /d "%~dp0"
echo This adds a Windows scheduled task that checks the sources every day at 09:00.
echo If the laptop is off or asleep at 09:00, it runs as soon as it's back on.
echo.
powershell -NoProfile -ExecutionPolicy Bypass -Command "$a = New-ScheduledTaskAction -Execute '%~dp0run_daily.bat' -WorkingDirectory '%~dp0'; $t = New-ScheduledTaskTrigger -Daily -At '09:00'; $s = New-ScheduledTaskSettingsSet -StartWhenAvailable -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries; Register-ScheduledTask -TaskName 'Healthcare Fund Finder daily check' -Action $a -Trigger $t -Settings $s -Force | Out-Null"
if errorlevel 1 (
  echo Could not create the task. Try right-clicking this file and choosing "Run as administrator".
) else (
  echo Done. The daily check is scheduled. Results appear on the "Data updates" page.
  echo To stop it, double-click unschedule_daily.bat.
)
pause
