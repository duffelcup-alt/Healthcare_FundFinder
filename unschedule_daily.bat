@echo off
powershell -NoProfile -Command "Unregister-ScheduledTask -TaskName 'Healthcare Fund Finder daily check' -Confirm:$false" && echo The daily check is removed.
pause
