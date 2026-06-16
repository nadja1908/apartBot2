@echo off
REM Start apartment monitor daemon
REM This script starts the continuous monitor in the background

cd /d "%~dp0"

echo Starting Apartment Monitor Daemon...
echo Process will run in background. Check monitor_daemon.log for status.

REM Run Python daemon in background
start /B python monitor_daemon.py

echo Daemon started. Logs: monitor_daemon.log
pause
