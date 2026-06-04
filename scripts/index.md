# scripts/ — index

| File | Purpose |
|---|---|
| `benchmark.py` | Measures ONNX inference latency for every style model in `styles/`. Runs a warmup pass then times N inferences per model and prints a summary table. |
| `create_sample_overview.bat` | Generates style-overview and style-chain-overview images for every sample photo via `BatchStyler.exe`. Requires a compiled `dist/PictureStyler/` directory — run `compile.ps1` first. |
| `gen_palette_ico_temp.py` | Generates palette and icon assets for the application. |
| `sample_pic_slide_gen.bat` | Applies a random style chain to every sample photo and assembles the results into an MP4 slideshow using an external `slidegen.exe`. |
| `style_analysis.ipynb` | Interactive style-image analyser. Computes texture/geometry metrics for every JPEG in a folder, recommends `STYLE_WEIGHT` / `CONTENT_WEIGHT`, shows a thumbnail grid, and provides a local smoke-test widget (CPU) with a signal-strength check. Use before a Kaggle run to screen images. |

