# SlideshowGen — Implementation Plan

**Version**: 1.0 — May 2026  
**Project location**: `C:\Users\i09300076\OneDrive - Endress+Hauser\DEV\Python3\slideshow-gen\`

> **Standalone project — do not merge into `style_transfer`.**  
> The two tools have incompatible dependency stacks (ONNX/PySide6 vs. ffmpeg/PyYAML),
> independent compiled outputs, and unrelated test suites.  The only connection is a
> workflow one: styled images from `PetersPictureStyler` can be dropped into
> `slidegen`'s `<picdir>` as plain JPEG files.  Keeping them separate avoids bloating
> the dist package, entangling releases, and inflating the test suite.

---

## 1. Answers to Design Questions

### 1.1 Start fresh or redesign the OSS project?

**Verdict: Start fresh.**

The OSS project (`kbvs`) was designed GUI-first; the CLI is a thin wrapper.
Its core complexity comes from features we don't need:

| OSS feature | Our verdict |
|---|---|
| Per-slide temp video files (multi-pass) | Skip — use single-pass `filter_complex` |
| Per-slide JSON config (overlays, subtitles) | Skip |
| Beat-sync via `aubio` | Skip |
| Loopable output / MKV subtitles | Skip |
| PyInstaller GUI binary | Skip |
| HEIC / video-slide support | HEIC via Pillow, no video slides |

The parts we reuse **conceptually** (not in code):
- The full xfade transition name list from `transitions/readme.md`
- The `zoompan` ffmpeg filter approach for Ken Burns
- The audio-sync duration formula

Our implementation will be ~400–600 lines vs ~2 000 in the OSS project.

---

### 1.2 Is the calm/energizing intention clear?

**Yes, 100 % clear.**  
Implemented as `--mood calm|medium|energizing` (default `medium`).  
Mood drives three things simultaneously:
- slide duration
- transition duration (derived, not a separate flag)
- Ken Burns zoom rate and direction aggressiveness

| mood | slide_duration | transition_duration | zoom_rate | Ken Burns z |
|---|---|---|---|---|
| `calm` | 6.0 s | 1.5 s | 0.0004 | slow in _or_ out |
| `medium` | 4.0 s | 1.0 s | 0.001 | random |
| `energizing` | 2.0 s | 0.5 s | 0.003 | random (aggressive) |

All three values are overridable by explicit CLI flags (see §3.3).  
`--mood` is the "one-knob" shortcut; the individual flags are for fine-tuning.

---

### 1.3 Do I need an explicit `--transition-duration` flag?

**No separate flag needed by default.**  
Auto-derive: `transition_duration = slide_duration × 0.25`  
Constraint `transition_duration < slide_duration / 2` is always satisfied.

We **do** expose an optional `--transition-duration SECS` for power users, but it is not documented in the primary help text — only in `--help-advanced`.

Edge cases:
- `slide_duration < 0.4 s` → transitions are automatically disabled (behaves like `--transition none`)
- `audio-sync` mode → transition_duration is fixed first, slide_duration is derived (see §3.4)

---

## 2. Architecture

### 2.1 Why single-pass over multi-pass

The OSS project encodes one temp `.mp4` per image, then concatenates.
For N=20 images that is 20 encode passes + 1 concat pass.

Our approach: build one `filter_complex` string and call ffmpeg once.
- Faster (one pass)
- No temp files for ≤ 80 images
- For > 80 images: chunked approach (batches of 40, then concat) — handled transparently

### 2.2 ffmpeg filter_complex sketch (N images, xfade)

```
# Input loop: each image → zoompan (Ken Burns) → scale → fps → named stream [v0]..[vN-1]
[0:v]zoompan=z='zoom+0.0010':x=...:y=...:d=180:s=1280x720,fps=30,scale=1280:720:force_original_aspect_ratio=decrease,pad=1280:720:-1:-1:color=black[v0];
[1:v]zoompan=...[v1];
...

# Chain xfade: [v0][v1] → xfade → [x01]; [x01][v2] → xfade → [x012]; ...
[v0][v1]xfade=transition=dissolve:duration=1.0:offset=5.0[x01];
[x01][v2]xfade=transition=wipeleft:duration=1.0:offset=10.0[x012];
...
[x0..N-2][vN-1]xfade=transition=fade:duration=1.0:offset=...[vout];

# Audio (if any): concat mp3 streams → trim/loop to video length
[a0][a1]concat=n=2:v=0:a=1[aout];
```

The `offset` for each xfade = `sum of (slide_duration - transition_duration)` for all previous slides.

### 2.3 Project structure

```
slideshow-gen/
├── slidegen/
│   ├── __init__.py
│   ├── app.py               # CLI: argparse + orchestration
│   ├── config.py            # Pydantic settings, mood presets, TRANSITIONS list
│   ├── ffmpeg_finder.py     # Auto-discover ffmpeg / ffprobe
│   ├── image_collector.py   # Collect + sort + validate images
│   ├── ken_burns.py         # Generate zoompan filter string per image
│   ├── filter_builder.py    # Build full filter_complex string
│   ├── audio_mixer.py       # Concat mp3s, compute audio-sync duration
│   └── runner.py            # Execute ffmpeg, progress reporting
├── tests/
│   ├── test_image_collector.py
│   ├── test_ken_burns.py
│   ├── test_filter_builder.py
│   ├── test_audio_mixer.py
│   └── test_ffmpeg_finder.py
├── ken_burns_config.yml     # Tunable Ken Burns parameters (see §4)
├── pyproject.toml
├── requirements.txt
└── README.md
```

---

## 3. CLI Design

### 3.1 Full command signature

```
slidegen <picdir>
         [--slideshow <file.mp4>]
         [--resolution 480|720|1080]
         [--order random|alpha|date]
         [--transition random|none|<xfade-name>]
         [--mood calm|medium|energizing]
         [--ken-burns low|medium|high|none]
         [--slide-duration <secs>|audio-sync]
         [--mp3 <file.mp3>] [--mp3 <file.mp3> ...]
         [--overwrite]
         [--dry-run]
```

### 3.2 Positional & required

| Argument | Description |
|---|---|
| `<picdir>` | Folder containing images. Supports jpg, jpeg, png, bmp, tiff, webp, heic. |

### 3.3 Optional flags

| Flag | Default | Description |
|---|---|---|
| `--slideshow FILE` | `<picdir-name>_slideshow.mp4` | Output file path |
| `--resolution 480\|720\|1080` | `720` | Output height in pixels; width = auto (16:9) |
| `--order random\|alpha\|date` | `random` | Sort order of images |
| `--transition random\|none\|NAME` | `random` | xfade transition (see §5 for full list) |
| `--mood calm\|medium\|energizing` | `medium` | One-knob preset for duration + Ken Burns intensity |
| `--ken-burns low\|medium\|high\|none` | `medium` | Ken Burns intensity (overrides mood's default) |
| `--slide-duration SECS\|audio-sync` | from mood | Seconds per slide, or stretch to fit audio |
| `--mp3 FILE` | (none, silent) | Audio track; repeat flag for multiple files |
| `--overwrite` | `False` | Overwrite output file without asking |
| `--dry-run` | `False` | Print ffmpeg command but do not execute |

### 3.4 audio-sync formula

When `--slide-duration audio-sync`:

```
total_audio = sum(mp3 durations)
N = number of images
transition_duration = slide_duration_from_mood × 0.25   # fixed first
slide_duration = (total_audio + (N - 1) × transition_duration) / N
```

If the resulting `slide_duration < 0.5 s`, exit with an error:
> "Audio is too short for N images — add more audio or fewer images."

Minimum enforced: `slide_duration ≥ 0.5 s`.

### 3.5 `--transition` valid names

Category | Names
---|---
Wipe | `wipeleft` `wiperight` `wipeup` `wipedown` `wipetl` `wipetr` `wipebl` `wipebr`
Slide | `slideleft` `slideright` `slideup` `slidedown`
Cover/Reveal | `coverleft` `coverright` `coverup` `coverdown` `revealleft` `revealright` `revealup` `revealdown`
Fade | `fade` `fadeblack` `fadewhite` `fadegrays` `fadefast` `fadeslow`
Smooth | `smoothleft` `smoothright` `smoothup` `smoothdown`
Circle | `circlecrop` `circleopen` `circleclose`
Diagonal | `diagtl` `diagtr` `diagbl` `diagbr`
Slice | `hlslice` `hrslice` `vuslice` `vdslice` `hlwind` `hrwind` `vuwind` `vdwind`
Squeeze | `squeezeh` `squeezev`
Vert/Horz | `vertopen` `vertclose` `horzopen` `horzclose`
Other | `dissolve` `pixelize` `distance` `rectcrop` `radial` `hblur` `zoomin`

`random` picks uniformly from the full list for each slide independently.

---

## 4. Ken Burns Config File

`ken_burns_config.yml` lives next to the script (or in the user's home dir as `~/.slidegen/ken_burns_config.yml`).  
The CLI reads it on startup; values are overridden by the `--ken-burns` flag.

```yaml
# Ken Burns parameters — tuned interactively
# zoom_rate: fraction of zoom per frame; higher = more dramatic
# zoom_direction_z: "in" | "out" | "random" | "none"
# zoom_direction_x: "left" | "right" | "center" | "random"
# zoom_direction_y: "top" | "bottom" | "center" | "random"

low:
  zoom_rate: 0.0004        # very subtle drift
  zoom_direction_z: random # alternates in/out slowly
  zoom_direction_x: center # minimal lateral movement
  zoom_direction_y: center
  scale_mode: crop_center

medium:
  zoom_rate: 0.0010
  zoom_direction_z: random
  zoom_direction_x: random
  zoom_direction_y: random
  scale_mode: crop_center

high:
  zoom_rate: 0.0030        # dramatic push-in/pull-out
  zoom_direction_z: random
  zoom_direction_x: random
  zoom_direction_y: random
  scale_mode: crop_center

none:
  zoom_rate: 0.0           # still image, no movement
  zoom_direction_z: none
  zoom_direction_x: center
  zoom_direction_y: center
  scale_mode: crop_center
```

**Rationale for values:**
- `0.0004` → barely perceptible over 6 s (calm)
- `0.001` → standard documentary style (medium)
- `0.003` → MTV/energizing style, full zoom-in over ~3 s

`zoom_rate` maps to ffmpeg's `zoompan` z-expression:  
`z='if(eq(on,1),1,zoom+zoom_rate)'` for zoom-in, `'if(eq(on,1),1.3,zoom-zoom_rate)'` for zoom-out.

---

## 5. ffmpeg Discovery (`ffmpeg_finder.py`)

Search order (Windows):

1. `PATH` via `shutil.which("ffmpeg")`
2. winget install location: `%LOCALAPPDATA%\Microsoft\WinGet\Packages\Gyan.FFmpeg*\**\bin\ffmpeg.exe`
3. Chocolatey: `C:\ProgramData\chocolatey\bin\ffmpeg.exe`
4. Scoop: `%USERPROFILE%\scoop\shims\ffmpeg.exe`
5. Bundled via `imageio-ffmpeg` pip package (`imageio_ffmpeg.get_ffmpeg_exe()`)

If none found → clear error:
```
Error: ffmpeg not found. Install it with:
  winget install Gyan.FFmpeg
or:
  pip install imageio-ffmpeg  (bundles a minimal ffmpeg)
```

`ffprobe` is discovered alongside ffmpeg (same directory, same logic).

---

## 6. Resolution Map

| `--resolution` | Width × Height | ffmpeg scale |
|---|---|---|
| `480` | 854 × 480 | `scale=854:480:force_original_aspect_ratio=decrease,pad=854:480:-1:-1:color=black` |
| `720` | 1280 × 720 | `scale=1280:720:...` |
| `1080` | 1920 × 1080 | `scale=1920:1080:...` |

Portrait images are padded with black bars (letterbox/pillarbox).  
EXIF orientation is respected (Pillow normalises before passing to ffmpeg via `-vf transpose`).

---

## 7. Image Collector

`image_collector.py`:
- Scans `<picdir>` non-recursively (flat folder assumed)
- Supported: `jpg jpeg png bmp tiff webp heic`
- HEIC: auto-converted to JPEG in a temp folder via Pillow + `pillow-heif`
- Sort modes:
  - `alpha` → `Path.name.casefold()`
  - `date` → EXIF `DateTimeOriginal` → file `mtime` fallback
  - `random` → `random.shuffle`
- Exits if `< 2` images found

---

## 8. Audio Mixer

`audio_mixer.py`:
- Multiple `--mp3` files → `concat` ffmpeg audio filter
- Supported formats: mp3, ogg, flac, aac, m4a (anything ffmpeg decodes)
- When total audio < video duration: last track loops (ffmpeg `aloop`) + fade out last 2 s
- When total audio > video duration: trimmed at video end + fade out 2 s
- Output: single `-shortest` flag or explicit `-t total_video_duration`

---

## 9. Dependencies

```
# requirements.txt
Pillow>=10.0
pillow-heif>=0.13          # HEIC support
PyYAML>=6.0                # ken_burns_config.yml
imageio-ffmpeg>=0.4.9      # fallback ffmpeg bundle
pydantic>=2.0              # config validation
```

No GUI framework, no heavy ML libraries.

---

## 10. Implementation Phases

| Phase | Scope | Est. lines |
|---|---|---|
| 1 | `ffmpeg_finder` + `image_collector` + `config` (Pydantic) + `app.py` skeleton | ~200 |
| 2 | `ken_burns.py` + `filter_builder.py` (zoompan + xfade filter_complex) | ~150 |
| 3 | `audio_mixer.py` + audio-sync formula | ~80 |
| 4 | `runner.py` (execute ffmpeg, progress bar) | ~60 |
| 5 | Tests (all modules, mocking ffmpeg) | ~300 |
| 6 | `ken_burns_config.yml` tuning + README | ~50 |

Total estimated: ~840 lines (production) + ~300 lines (tests).

---

## 11. Example Invocations

```powershell
# Calm holiday slideshow with background music
slidegen C:\Photos\Italy2025 --mood calm --mp3 bgm.mp3 --slide-duration audio-sync

# Fast party reel, 720p, random transitions
slidegen C:\Photos\Party --mood energizing --resolution 720

# Specific transition, alphabetical order, silent
slidegen C:\Photos\Architecture --transition fade --order alpha --slideshow arch_tour.mp4

# Preview what would run (no ffmpeg execution)
slidegen C:\Photos\Test --dry-run

# Full control (overrides mood)
slidegen C:\Photos\Wedding --mood calm --slide-duration 8 --ken-burns high --transition dissolve
```

---

## 12. What We Deliberately Skip (vs. OSS project)

| OSS feature | Reason skipped |
|---|---|
| Per-slide JSON config | Adds complexity; CLI flags cover 95 % of use cases |
| Text overlays / subtitles | Out of scope |
| Beat-sync via aubio | Heavy dependency; audio-sync formula is sufficient |
| Video slides as input | HEIC + image formats are enough |
| Loopable output | Niche use case |
| Temp-file multi-pass for all slideshows | Only used as fallback for > 80 images |
| GUI | Explicitly out of scope |
