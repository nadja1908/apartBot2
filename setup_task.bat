@echo off
REM This script creates a Windows Task Scheduler task to run the monitor daemon at startup
REM Run as Administrator!

echo Creating Windows Task Scheduler task for Apartment Monitor...
echo This requires Administrator privileges!
echo.

REM Get current directory
for /f "tokens=*" %%A in ('cd') do set "REPO_DIR=%%A"

REM Create the task
powershell -Command ^
  "$action = New-ScheduledTaskAction -Execute 'python.exe' -Argument '%REPO_DIR%\monitor_daemon.py'; " ^
  "$trigger = New-ScheduledTaskTrigger -AtStartup; " ^
  "$settings = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -StartWhenAvailable; " ^
  "$task = New-ScheduledTask -Action $action -Trigger $trigger -Settings $settings -Description 'Continuous apartment monitor daemon'; " ^
  "Register-ScheduledTask -TaskName 'ApartmentMonitorDaemon' -InputObject $task -Force"

echo.
echo Task created! The daemon will start automatically on next reboot.
echo.
echo To check status:
echo   - Open Task Scheduler
echo   - Find "ApartmentMonitorDaemon" under Library/Custom
echo   - Right-click and select "Run" to start immediately
echo.
echo To view logs:
echo   - Check monitor_daemon.log in the repo directory
echo.
pause
