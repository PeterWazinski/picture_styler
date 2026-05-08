@echo off
setlocal enabledelayedexpansion

:: ── paths relative to this bat file ────────────────────────────────────────
set "SCRIPT_DIR=%~dp0"
set "SAMPLE_PICS=%SCRIPT_DIR%sample_pics"
set "STYLE_OUT=%SCRIPT_DIR%style-overviews"
set "CHAIN_OUT=%SCRIPT_DIR%style-chain-overviews"
::set "CHAIN_DIR=%SCRIPT_DIR%..\dist\PetersPictureStyler\style_chains"
set "CHAIN_DIR=%SCRIPT_DIR%style-chains"
set "BATCHSTYLER=%SCRIPT_DIR%..\dist\PetersPictureStyler\BatchStyler.exe"

:: ── sanity checks ───────────────────────────────────────────────────────────
if not exist "%BATCHSTYLER%" (
    echo ERROR: BatchStyler.exe not found at %BATCHSTYLER%
    echo        Run compile.ps1 first.
    exit /b 1
)
if not exist "%SAMPLE_PICS%" (
    echo ERROR: sample_pics folder not found: %SAMPLE_PICS%
    exit /b 1
)

:: ── ensure output dirs exist ────────────────────────────────────────────────
if not exist "%STYLE_OUT%" mkdir "%STYLE_OUT%"
if not exist "%CHAIN_OUT%" mkdir "%CHAIN_OUT%"

:: ── delete old PDFs ─────────────────────────────────────────────────────────
echo Deleting old style-overview PDFs...
del /q "%STYLE_OUT%\*.pdf" 2>nul

echo Deleting old style-chain-overview PDFs...
del /q "%CHAIN_OUT%\*.pdf" 2>nul

:: ── style overviews (one PDF per sample pic) ────────────────────────────────
echo.
echo === Creating style overviews ===
"%BATCHSTYLER%" --style-overview --input-dir "%SAMPLE_PICS%" --output-dir "%STYLE_OUT%"
if errorlevel 1 (
    echo WARNING: style-overview failed
)

:: ── style-chain overviews (one PDF per sample pic) ──────────────────────────
echo.
echo === Creating style-chain overviews ===
"%BATCHSTYLER%" --style-chain-overview "%CHAIN_DIR%" --input-dir "%SAMPLE_PICS%" --output-dir "%CHAIN_OUT%"
if errorlevel 1 (
    echo WARNING: style-chain-overview failed
)

echo.
echo Done.
echo   Style overviews   : %STYLE_OUT%
echo   Chain overviews   : %CHAIN_OUT%
endlocal
