@echo off
echo Updating Desktop Project...
rem Copy all files from current directory to Desktop/BabyAuto
rem /E = Recursive
rem /IS = Include Same files (overwrite/update timestamp)
rem /XC = Exclude Changed (not used, we want to overwrite)
rem /XO = Exclude Older (not used, we want to force update)
robocopy "%~dp0." "%USERPROFILE%\Desktop\BabyAuto" /E /IS
if %ERRORLEVEL% GEQ 8 (
    echo Copy failed.
    exit /b %ERRORLEVEL%
)
echo Update Complete.
