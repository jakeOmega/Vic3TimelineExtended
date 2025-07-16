@echo off
setlocal

:: --- Configuration ---
set "BACKUP_FOLDER=backup_originals"
set "TARGET_SIZE=256x256"
:: -------------------

:: Create the backup directory if it doesn't exist
if not exist "%BACKUP_FOLDER%\" (
    echo Creating backup folder: %BACKUP_FOLDER%
    mkdir "%BACKUP_FOLDER%"
)

:: Loop through all DDS files in the current folder
for %%f in (*.dds) do (
    echo Backing up "%%f"...
    copy "%%f" "%BACKUP_FOLDER%\"
    
    echo Resizing "%%f" in place to %TARGET_SIZE%...
    magick mogrify -resize %TARGET_SIZE% "%%f"
)

echo.
echo Process complete.
echo Original files have been backed up to the '%BACKUP_FOLDER%' folder.
endlocal
pause