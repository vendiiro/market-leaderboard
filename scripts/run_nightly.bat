@echo off
REM Nightly data build after the market close. Registered with Task Scheduler by scripts\install_task.ps1 (see README.md).
REM Pattern from dip-dashboard scripts\run_daily.bat (commit f14d55c).
REM Writes the four JSON files to web\public\data and copies them to web\dist\data (the folder the page is served from).
REM The page itself is not rebuilt here: run "npm --prefix web run build" only after code changes.
REM Exit code: 0 = ok, 2 = too few tickers had data (the previous files are kept), 3 = setup problem, other = crash.
REM Retry: after exit code 2 only (usually Yahoo down or rate-limited), wait 20 minutes and run once more.
REM   The wait uses PowerShell Start-Sleep, not "timeout" (timeout fails under Task Scheduler, which has no console input).
REM Log: output\nightly.log; when it is over about 5 MB it is moved to output\nightly.log.1 (two files at most).
REM Optional test hook: MLB_RETRY_WAIT = seconds to wait before the retry (default 1200).
setlocal
cd /d "%~dp0\.."
REM UTF-8 for the log only. Do NOT use PYTHONUTF8=1: with a non-ASCII user folder name it breaks the certificate file
REM lookup and every download fails (seen in dip-dashboard, 2026-11-04).
set PYTHONIOENCODING=utf-8
set RETRIED=
if not defined MLB_RETRY_WAIT set MLB_RETRY_WAIT=1200
set "PY=.venv\Scripts\python.exe"
if not exist output mkdir output
if exist "%PY%" goto rotate
echo %date% %time% ==== setup problem: %PY% not found, run "uv sync" first (see README.md) >> output\nightly.log
exit /b 3

:rotate
set LOGSIZE=0
if exist output\nightly.log for %%F in ("output\nightly.log") do set LOGSIZE=%%~zF
if %LOGSIZE% LEQ 5242880 goto run
move /y output\nightly.log output\nightly.log.1 >nul

:run
echo %date% %time% ==== start >> output\nightly.log
"%PY%" -m engine build >> output\nightly.log 2>&1
set RC=%errorlevel%
echo %date% %time% ==== exit code %RC% >> output\nightly.log
if not "%RC%"=="2" goto finish
if defined RETRIED goto finish
set RETRIED=1
echo %date% %time% ==== exit code 2, retrying in %MLB_RETRY_WAIT% s >> output\nightly.log
powershell -NoProfile -Command "Start-Sleep -Seconds %MLB_RETRY_WAIT%" >> output\nightly.log 2>&1
goto run

:finish
if not "%RC%"=="0" exit /b %RC%
if not exist web\dist\index.html goto nodist
if not exist web\dist\data mkdir web\dist\data
copy /y web\public\data\*.json web\dist\data\ >nul
if errorlevel 1 goto copyfailed
exit /b 0

:nodist
echo %date% %time% ==== data is ready, but the page is not built yet: run "npm --prefix web run build" >> output\nightly.log
exit /b 3

:copyfailed
echo %date% %time% ==== the data could not be copied to web\dist\data >> output\nightly.log
exit /b 1
