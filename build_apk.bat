@echo off
set PROJ_DIR=C:\Users\Administrator\StudioProjects\sha-pay\mobile
cd /d "%PROJ_DIR%"
echo Current directory: %CD%
echo Looking for pubspec.yaml...
if exist "%PROJ_DIR%\pubspec.yaml" (
    echo Found pubspec.yaml
) else (
    echo pubspec.yaml NOT FOUND!
    pause
    exit /b 1
)
echo Building APK... This will take several minutes.
echo Build log: C:\Users\Administrator\Desktop\apk_build_log.txt
call c:\src\flutter\bin\flutter.bat build apk --debug > "C:\Users\Administrator\Desktop\apk_build_log.txt" 2>&1
echo.
echo Done! Check C:\Users\Administrator\Desktop\apk_build_log.txt for results.
pause