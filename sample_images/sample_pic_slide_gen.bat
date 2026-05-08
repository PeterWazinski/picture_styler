@echo off
setlocal enabledelayedexpansion

:: ── paths ───────────────────────────────────────────────────────────────────
set "SCRIPT_DIR=%~dp0"
set "SAMPLE_PICS=%SCRIPT_DIR%..\sample_pics"
set "STYLED_OUT=%SCRIPT_DIR%random_styled_images"
set "CHAIN_DIR=%SCRIPT_DIR%..\style-chains"
set "BATCHSTYLER=%SCRIPT_DIR%..\..\dist\PetersPictureStyler\BatchStyler.exe"
set "SLIDEGEN=C:\Users\i09300076\OneDrive - Endress+Hauser\DEV\Python3\slideshow-maker\dist\slidegen.exe"
set "SLIDESHOW=%SCRIPT_DIR%sample_pic_slideshow.mp4"

:: ── sanity checks ───────────────────────────────────────────────────────────
if not exist "%BATCHSTYLER%" (
    echo ERROR: BatchStyler.exe not found at %BATCHSTYLER%
    echo        Run compile.ps1 first.
    exit /b 1
)
if not exist "%SLIDEGEN%" (
    echo ERROR: slidegen.exe not found at %SLIDEGEN%
    echo        Build slideshow-maker first.
    exit /b 1
)
if not exist "%SAMPLE_PICS%" (
    echo ERROR: sample_pics folder not found: %SAMPLE_PICS%
    exit /b 1
)
if not exist "%CHAIN_DIR%" (
    echo ERROR: style_chains folder not found: %CHAIN_DIR%
    exit /b 1
)

:: ── ensure output dir exists ─────────────────────────────────────────────────
if not exist "%STYLED_OUT%" mkdir "%STYLED_OUT%"

:: ── apply a random style chain to every sample pic ──────────────────────────
echo.
echo === Applying random style chains to sample pics ===
"%BATCHSTYLER%" --apply-random-style-chain "%CHAIN_DIR%" --input-dir "%SAMPLE_PICS%" --output-dir "%STYLED_OUT%"
if errorlevel 1 (
    echo ERROR: BatchStyler failed.
    exit /b 1
)

:: ── generate slideshow from styled images ───────────────────────────────────
echo.
echo === Generating slideshow ===
"%SLIDEGEN%" "%STYLED_OUT%" --slideshow "%SLIDESHOW%" --mood calm --ken-burns none --transition fade --overwrite
if errorlevel 1 (
    echo ERROR: slidegen failed.
    exit /b 1
)

echo.
echo Done.
echo   Styled images : %STYLED_OUT%
echo   Slideshow     : %SLIDESHOW%
endlocal
