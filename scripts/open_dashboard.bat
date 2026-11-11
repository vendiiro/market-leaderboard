@echo off
REM Opens the dashboard: serves web\dist with Python's built-in static server and opens the browser.
REM   scripts\open_dashboard.bat        this PC only (address http://localhost:8765/)
REM   scripts\open_dashboard.bat lan    also reachable from a phone on the same Wi-Fi (see below)
REM The page must be served over http: opening web\dist\index.html directly as a file does not work.
REM Close this window (or press Ctrl+C) to stop the server.
REM
REM "lan" makes the page readable by every device on your network while this window is open. It holds no private
REM data (public prices; test mixes stay in each browser), but use it on your home network only. Windows may ask
REM once whether Python may accept connections: allow "Private networks".
setlocal
cd /d "%~dp0\.."
set PORT=8765
set BIND=127.0.0.1
if /i "%~1"=="lan" set BIND=0.0.0.0
if not exist ".venv\Scripts\python.exe" goto nopython
if not exist "web\dist\index.html" goto nodist
if not exist "web\dist\data\meta.json" echo Note: no data yet. Run scripts\run_nightly.bat first; the page will say so until then.
if /i "%~1"=="lan" echo On the phone open http://ADDRESS:%PORT%/ where ADDRESS is this PC's IPv4 address:
if /i "%~1"=="lan" ipconfig | findstr /c:"IPv4"
echo Serving the dashboard at http://localhost:%PORT%/  (close this window to stop)
start "" "http://localhost:%PORT%/"
".venv\Scripts\python.exe" -m http.server %PORT% --bind %BIND% --directory web\dist
exit /b %errorlevel%

:nopython
echo Python environment not found. Run "uv sync" in this folder first (see README.md).
pause
exit /b 3

:nodist
echo The page is not built yet. Run:  npm --prefix web install  and then  npm --prefix web run build
pause
exit /b 3
