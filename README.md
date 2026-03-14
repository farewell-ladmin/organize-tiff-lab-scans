# Organize TIFF Lab Scans

A tool for organizing **TIFF** film scanner output, detecting edits, and identifying non-scanner files.

> Note: This tool is designed for TIFF files specifically. See AGENTS.md for adapting to other formats.

## Why Does This Exist?

Two main reasons:

1. **Separate edits from originals** - If you do any editing on your scans (color correction, noise removal, etc.), those edits shouldn't be mixed with originals. This is critical if you're using the originals for training data (AI/ML projects, etc.).

2. **Identify non-scanner files** - Labs sometimes send DSLR shots or other non-film-scanner files. This helps identify them so they don't end up in your "film scans only" datasets.

If you're good at file organization, you probably don't need this. I'm not, so I built it.

Niche problems require niche solutions. Niche solutions require vibe coding when you're bad at Python.

## Acknowledgments

Shoutout to [Midwest Film Company](https://www.midwestfilmco.com/) - they offer "cinema" scans of 35mm on a Blackmagic Cintel motion picture scanner. Absolutely stellar lab. Not sponsored, just genuinely awesome.

## ⚠️ WARNING - VIBE CODED

**This tool was vibe coded to solve a very niche problem. It has not been extensively tested. DO NOT run on originals without backing them up first.**

I am not responsible if your AI assistant or this tool eats your files. Always:
- Back up your data before running
- Use `--all` without `--force` to preview changes
- Verify the preview before confirming
- **Network shares**: Consider running on a local copy first, then syncing back

## Purpose

When receiving scans from a lab over many years, you may have:
- Original scanner outputs
- Edited versions of those scans (from your own workflow)
- Non-scanner files (DSLR shots, RAW files, sidecar files)

This tool helps identify and organize these into:
- `Edits/` - Files detected as edited (moved into `Edits/` subfolder within parent)
- `Not TIFF/` - Non-TIF files found in scan folders (moved into `Not TIFF/` subfolder within parent)
- `Non Film Scanner/` - Folders identified as non-scanner (DSLR) shots

### Folder Structure

The tool preserves your folder hierarchy. Given:
```
/path/to/scans/Originals/film_roll_001/
```

- **Edits** → `/path/to/scans/Originals/film_roll_001/Edits/`
- **Not TIFF** → `/path/to/scans/Originals/film_roll_001/Not TIFF/`
- **Non Film Scanner** (ALL DSLR folder) → `/path/to/scans/Originals/Non Film Scanner/film_roll_001/`
- **Non Film Scanner** (MIXED folder) → `/path/to/scans/Originals/film_roll_001/Non Film Scanner/`

## What Each Script Does

### Main Script
- **`organize_lab_scans.py`** - The orchestrator. Runs the full workflow with optional flags.

### Individual Scripts
- **`src/scan_edits.py`** - Scans for edited files based on metadata and filename patterns
- **`src/find_outliers.py`** - Finds non-scanner files (DSLR shots, rare metadata)
- **`src/move_edits.py`** - Moves detected edits to Edits/ subfolders
- **`src/move_non_tif.py`** - Moves non-TIF files to Not TIFF/ subfolders

## Requirements

- Python 3.x
- Pillow
- tifffile

```bash
pip install pillow tifffile
```

Or use something like `pipx` or operate inside a `venv` unlike the author who always forgets.

## Usage

### Basic (Preview Only)
```bash
python organize_lab_scans.py "/path/to/scans" --all
```

### With Confirmation
```bash
python organize_lab_scans.py "/path/to/scans" --all
# Shows preview, then asks: "Proceed with moving files? [y/n]"
```

### Without Confirmation (FORCE)
```bash
python organize_lab_scans.py "/path/to/scans" --all --force
```

### Individual Steps
```bash
# Scan only
python organize_lab_scans.py "/path/to/scans" --edits
python organize_lab_scans.py "/path/to/scans" --outliers

# Move only (uses existing CSVs)
python organize_lab_scans.py "/path/to/scans" --move
```

## ⚠️ Detection Criteria - EXTREMELY IMPORTANT - READ THIS

**The detection logic was tuned for a VERY SPECIFIC workflow:**

- A specific cinema scanner (Blackmagic Cintel)
- Specific editing software (Lightroom on Windows, Luminar)
- Specific filename patterns from a specific person's workflow

**You WILL need to customize this for your own workflow.**

### How Detection Was Developed (For Reference)

The original author used known-good originals vs. known edits to discover what metadata differs:
- Control folders: Known originals (no edits)
- Changes folders: Known edits

This revealed the patterns used for detection:
- Artist/Copyright metadata appears on edited files
- Software version differences (Lightroom Mac vs Windows)
- Bit depth changes (8-bit → 16-bit)
- Resolution changes (72 DPI → 240 DPI)
- Filename suffixes (-2, -Edit, _original, etc.)

### To Customize For Your Workflow

1. **Gather samples**: Create folders with known originals and known edits
2. **Analyze metadata**: Use a TIF metadata viewer to find differences
3. **Update detection**: See `AGENTS.md` for agent-friendly instructions

**Common changes you'll likely need to make:**
- Your lab's specific editing software
- Your specific filename patterns
- Your scanner's metadata signatures
- Different resolution/DPI values

### Current Edit Detection
- Artist/Copyright metadata present
- Luminar software
- Lightroom (Windows) version 13+
- 16-bit depth (vs 8-bit original)
- 240 DPI resolution
- Filename patterns: `-2`, `-3`, `-Edit`, `-Copy`, `_original`

### Current Outlier Detection
- Files with Make/Model metadata (DSLR shots)
- Non-TIF files (.dop, .arw, .cop, etc.)
- Rare metadata values (configurable threshold)

> **Note on DSLR files**: Non-scanner (DSLR) shots are identified by Make/Model metadata. When a folder contains both DSLR and scanner files, the DSLR files are moved to a Non Film Scanner subfolder. Consider running outlier detection before making edits to your originals.

### To Customize

See `AGENTS.md` for agent-friendly instructions to:
- Change file format detection (add .png, .jpg, etc.)
- Add/remove edit detection criteria
- Change outlier thresholds
- Modify folder names
- Add your own software patterns (Capture One, Photoshop, etc.)

## Caveats

- **Detection criteria needs customization** - The current rules are specific to the original author's workflow
- Hardcoded to look for specific editing software patterns
- Detection thresholds are tuned for this specific workflow
- May need adjustment for different labs/workflows
- Does not detect all possible edits - relies on metadata being present
- The "original" detection is based on what was NOT detected as edited
- Not tested on Mac/Linux (uses Python standard libraries, should work)

## Customization

For customization options, see `AGENTS.md` - allows you to:
- Change file format detection
- Add custom edit criteria
- Modify excluded folders
- Adjust outlier thresholds

---

## License

MIT License - See LICENSE file
