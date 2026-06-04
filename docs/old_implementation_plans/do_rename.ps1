<#
.SYNOPSIS
    Renames the style_transfer repo to picture_styler.
    Run AFTER closing all VS Code windows.

.USAGE
    powershell -ExecutionPolicy Bypass -File "...\docs\do_rename.ps1"
#>
Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$base   = "C:\Users\i09300076\OneDrive - Endress+Hauser\DEV\Python3"
$oldDir = "$base\style_transfer"
$newDir = "$base\picture_styler"
$wtOld  = "$base\style_transfer.worktrees"

function Patch-File($path, $from, $to) {
    $content = [System.IO.File]::ReadAllText($path)
    $patched = $content.Replace($from, $to)
    if ($content -ne $patched) {
        [System.IO.File]::WriteAllText($path, $patched, [System.Text.UTF8Encoding]::new($false))
        Write-Host "  Patched: $([System.IO.Path]::GetFileName($path))"
    }
}

# [1] Remove leftover worktrees folder
Write-Host "`n[1/8] Removing style_transfer.worktrees..." -ForegroundColor Cyan
if (Test-Path $wtOld) {
    Remove-Item -Recurse -Force $wtOld
    Write-Host "  Removed."
} else { Write-Host "  Already gone." }

# [2] Rename main directory
Write-Host "`n[2/8] Renaming directory..." -ForegroundColor Cyan
Rename-Item $oldDir "picture_styler"
Write-Host "  Done: $newDir"

# [3] Update git remote URL
Write-Host "`n[3/8] Updating git remote URL..." -ForegroundColor Cyan
git -C $newDir remote set-url origin https://github.com/PeterWazinski/picture_styler.git
Write-Host "  $(git -C $newDir remote get-url origin)"

# [4] Rename spec files
Write-Host "`n[4/8] Renaming spec files..." -ForegroundColor Cyan
Rename-Item "$newDir\style_transfer.spec"     "picture_styler.spec"
Rename-Item "$newDir\style_transfer-mac.spec" "picture_styler-mac.spec"
Write-Host "  style_transfer.spec     -> picture_styler.spec"
Write-Host "  style_transfer-mac.spec -> picture_styler-mac.spec"

# [5] Patch file contents
Write-Host "`n[5/8] Patching file contents..." -ForegroundColor Cyan
Patch-File "$newDir\compile.ps1"                              "style_transfer.spec"                  "picture_styler.spec"
Patch-File "$newDir\picture_styler.spec"                      "style_transfer.spec"                  "picture_styler.spec"
Patch-File "$newDir\picture_styler-mac.spec"                  "style_transfer.spec"                  "picture_styler.spec"
Patch-File "$newDir\src\core\settings.py"                     ".style_transfer"                      ".picture_styler"
Patch-File "$newDir\training\kaggle_trainer.ipynb"            "PeterWazinski/style_transfer.git"     "PeterWazinski/picture_styler.git"
Patch-File "$newDir\training\kaggle_trainer.ipynb"            "/kaggle/working/style_transfer"       "/kaggle/working/picture_styler"
Patch-File "$newDir\training\kaggle_multi_pic_trainer.ipynb"  "PeterWazinski/style_transfer.git"     "PeterWazinski/picture_styler.git"
Patch-File "$newDir\training\kaggle_multi_pic_trainer.ipynb"  "/kaggle/working/style_transfer"       "/kaggle/working/picture_styler"

# [6] Migrate settings.json
Write-Host "`n[6/8] Migrating settings.json..." -ForegroundColor Cyan
$oldSettings    = "$env:USERPROFILE\.style_transfer\settings.json"
$newSettingsDir = "$env:USERPROFILE\.picture_styler"
$newSettings    = "$newSettingsDir\settings.json"
New-Item -ItemType Directory -Force $newSettingsDir | Out-Null
$json = Get-Content $oldSettings -Raw | ConvertFrom-Json
if ($json.last_open_dir -like "*style_transfer*") {
    $json.last_open_dir = $json.last_open_dir -replace [regex]::Escape("style_transfer"), "picture_styler"
}
$json | ConvertTo-Json -Depth 5 | Set-Content -Encoding UTF8 $newSettings
Write-Host "  Created: $newSettings"

# [7] Commit
Write-Host "`n[7/8] Committing..." -ForegroundColor Cyan
git -C $newDir add -A
git -C $newDir commit -m "chore: rename repo style_transfer -> picture_styler" -m "- Rename spec files to picture_styler.spec / picture_styler-mac.spec
- Update compile.ps1 spec filename reference
- Update src/core/settings.py: ~/.style_transfer -> ~/.picture_styler
- Update Kaggle notebooks REPO_URL + REPO_DIR

Co-authored-by: Copilot <223556219+Copilot@users.noreply.github.com>"

# [8] Open VS Code
Write-Host "`n[8/8] Opening VS Code..." -ForegroundColor Cyan
code $newDir

Write-Host "`n=== Done! ===" -ForegroundColor Green
Write-Host "  Path  : $newDir"
Write-Host "  Remote: $(git -C $newDir remote get-url origin)"
Write-Host ""
Write-Host "Next steps (in new VS Code terminal):" -ForegroundColor Yellow
Write-Host "  python -m pytest" -ForegroundColor Yellow
Write-Host "  .\compile.ps1" -ForegroundColor Yellow