# Rename: style_transfer -> picture_styler

## Status

| # | Step | Who | Status |
|---|------|-----|--------|
| 1 | GitHub repo renamed | Manual | Done |
| 2 | ~/.style_transfer/settings.json backed up | Already done | Done |
| 3 | Delete style_transfer.worktrees/ folder | do_rename.ps1 | Pending |
| 4 | Rename directory style_transfer -> picture_styler | do_rename.ps1 | Pending |
| 5 | Update git remote URL | do_rename.ps1 | Pending |
| 6 | Rename + patch spec files | do_rename.ps1 | Pending |
| 7 | Patch compile.ps1 | do_rename.ps1 | Pending |
| 8 | Patch src/core/settings.py | do_rename.ps1 | Pending |
| 9 | Patch Kaggle notebooks (source cells only) | do_rename.ps1 | Pending |
| 10 | Migrate ~/.picture_styler/settings.json | do_rename.ps1 | Pending |
| 11 | Commit changes | do_rename.ps1 | Pending |
| 12 | Open VS Code at new path | do_rename.ps1 | Pending |
| 13 | Run: python -m pytest | Manual in VS Code terminal | Pending |
| 14 | Run: .\compile.ps1 | Manual in VS Code terminal | Pending |

## Manual steps

### Before running the script
> Close ALL VS Code windows first!
> The rename will fail if VS Code has the folder open.

### Run the script
```
powershell -ExecutionPolicy Bypass -File "C:\Users\i09300076\OneDrive - Endress+Hauser\DEV\Python3\style_transfer\docs\do_rename.ps1"
```

### After the script
1. Open a terminal in the new VS Code window
2. Run: python -m pytest
3. Run: .\compile.ps1
4. If build passes: git push

## Files changed by the script

| File | Change |
|------|--------|
| style_transfer.spec | Renamed -> picture_styler.spec, comment updated |
| style_transfer-mac.spec | Renamed -> picture_styler-mac.spec, comment updated |
| compile.ps1 | style_transfer.spec -> picture_styler.spec |
| src/core/settings.py | ~/.style_transfer -> ~/.picture_styler |
| training/kaggle_trainer.ipynb | REPO_URL + REPO_DIR updated |
| training/kaggle_multi_pic_trainer.ipynb | REPO_URL + REPO_DIR updated |

Not changed: output cells of other notebooks (cached output, not active code).