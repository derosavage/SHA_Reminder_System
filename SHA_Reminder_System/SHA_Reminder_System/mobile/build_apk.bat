@echo off
set PROJ_DIR=C:\Users\Administrator\StudioProjects\SHA_Reminder_System\SHA_Reminder_System\mobile
cd /d "%PROJ_DIR%"
echo Current directory: %CD%
echo Building APK... This will take several minutes.
echo Build log: C:\Users\Administrator\Desktop\apk_build_log.txt
call c:\src\flutter\bin\flutter.bat build apk --debug > "C:\Users\Administrator\Desktop\apk_build_log.txt" 2>&1
echo.
echo Done! Check C:\Users\Administrator\Desktop\apk_build_log.txt for results.
pause