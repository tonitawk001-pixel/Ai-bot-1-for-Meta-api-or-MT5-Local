@echo off
cd /d "%~dp0"
echo Starting V22 Bot Dashboard...
echo Open: http://localhost:5000
echo Close this window to stop the dashboard.
echo.
python dashboard_simple.py
pause