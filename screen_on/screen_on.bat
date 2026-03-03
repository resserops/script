@echo off
py -3 "%~dp0screen_on.py" && exit
echo Run script failed. Error code: %ERRORLEVEL%
pause
exit /b %ERRORLEVEL%
