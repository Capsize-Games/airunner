@echo off
echo Setting up build environment...

REM --- Activate your Python virtual environment here ---
REM For example:
REM CALL .venv\Scripts\activate.bat
REM CALL path\to\your\venv\Scripts\activate.bat
echo IMPORTANT: Ensure your Python virtual environment is active for a consistent build.

echo.
echo Installing PyInstaller (version 6.12.0)...
python -m pip install pyinstaller==6.12.0
if errorlevel 1 (
    echo ERROR: Failed to install PyInstaller. Please check your Python and pip setup.
    goto :eof
)

echo.
echo Running PyInstaller for airunner (Windows)...
pyinstaller airunner.spec --noconfirm --clean --distpath ./dist_windows --workpath ./build_windows

echo.
if errorlevel 1 (
    echo ERROR: PyInstaller failed to build airunner. Check the output above for details.
) else (
    echo SUCCESS: PyInstaller completed successfully.
    echo Your bundled application should be in the 'dist_windows' directory.
)

echo.
pause

:eof
