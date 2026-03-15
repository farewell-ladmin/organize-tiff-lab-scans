# AGENTS.md - Configuration for AI Agents

**⚠️ THE REAL WILD WEST ⚠️**

This file is for AI agents (and vibe coders) to reconfigure the tool without reading code.

> **IMPORTANT: This code is designed for TIFF files.** The main script and all detection logic is tuned for .tif/.tiff files. See the customization sections below to adapt for other formats.

**I am not responsible for what your agent does with this prompt. You're giving an AI permission to move your files. Be smart about it.**

---

## For the AI Agent

You are working with a film scan organization tool. The user wants to customize how it detects edits and outliers.

## Why This Tool Exists

1. **Separate edits from originals** - Keeps edited scans separate from originals (important for training data)
2. **Identify non-scanner files** - DSLR shots, RAW files, etc. that aren't from the film scanner

The detection logic is tuned for a very specific workflow (a particular cinema scanner, specific editing software). Users will need to customize it for their own setup.

## Current Setup

The tool operates on: `/path/to/scans`
- **TIFF files** (.tif, .tiff)
- Scans for edited files
- Identifies non-scanner files (DSLR shots, RAW files)
- Moves them to subfolders

## Available Scripts

1. `organize_lab_scans.py` - Main orchestrator (in root)
2. `src/scan_edits.py` - Edit detection
3. `src/find_outliers.py` - Outlier detection (DSLR, non-TIF)
4. `src/move_edits.py` - Move edits and non-scanner files
5. `src/move_non_tif.py` - Move non-TIF files

## Configuration Options

### Change Original File Format

Currently looks for: `.tif`, `.tiff`

The code also detects TIFFs by content (magic bytes) for files with unusual extensions like `.tif_original`.

To add more formats (e.g., `.png`, `.jpg`):

Edit `src/find_outliers.py` and `src/move_non_tif.py` - look for `get_file_ext()` function:

### Change What Folders to Ignore

Currently excluded: `Edits`, `Non Film Scanner`, `Not TIFF`

Find lines with:
```python
exclude_folders = {'Edits', 'Non Film Scanner', 'Not TIFF'}
```

And modify the set.

### Change Edit Detection Criteria

In `src/scan_edits.py`, look for `detect_edit()` function. You can add/remove:

- Artist metadata presence
- Copyright metadata presence  
- Software detection (Luminar, Lightroom versions)
- 16-bit depth detection
- Resolution detection (240 DPI)
- Filename patterns (-2, -3, -Edit, -Copy, _original)

### Change Outlier Detection

In `src/find_outliers.py`, look for outlier detection logic:

- DSLR detection: Looks for Make/Model metadata
- Non-TIF files: .dop (Capture One), .arw (Sony RAW), etc.
- Rare metadata: Currently checks Make, Model, Compression, BitsPerSample, XResolution, YResolution
- Threshold: Currently `< 15 files or < 3%` = outlier

### Non-Film Scanner (DSLR) Handling

The tool handles DSLR/non-scanner files differently:

- **All DSLR folder**: Entire folder moved to `{parent}/Non Film Scanner/{folder_name}/`
- **Mixed folder**: Only DSLR files moved to `{parent}/Non Film Scanner/`

### Change Subfolder Names

- Default: `Edits`, `Not TIFF`, `Non Film Scanner`

Find and replace these strings in the code.

## Example Prompts for Agents

### "Add support for PNG files"
```
Add .png to the file format detection in src/find_outliers.py and 
src/move_non_tif.py. Update get_file_ext() to handle png as an original format.
```

### "Change my edits detection to look for Photoshop instead of Lightroom"
```
In src/scan_edits.py, update detect_edit() to flag files with "Photoshop" 
in the Software field as edits, instead of the current Lightroom detection.
```

### "I use Capture One instead of Lightroom"
```
Update detect_edit() to look for "Capture One" in the Software field,
and remove the Lightroom detection.
```

### "Add -final as an edit marker"
```
Update the filename pattern detection to also flag files containing 
"-final" as edits, in addition to the existing -2, -3, -Edit patterns.
```

### "Don't move non-tif files, just report them"
```
Modify the --move flag behavior to only print what would be moved 
instead of actually moving files. Or add a --report-only flag.
```

---

## Running the Tool

**IMPORTANT: Use a virtual environment or pipx** - Modern OSes get annoyed with system-wide pip packages.

```bash
# Option 1: Virtual environment (recommended)
python -m venv venv
source venv/bin/activate  # or venv\Scripts\activate on Windows
pip install pillow tifffile

# Preview what would happen
python organize_lab_scans.py "/your/scan/folder" --all

# With confirmation  
python organize_lab_scans.py "/your/scan/folder" --all

# Force (no confirmation, for agents/non-interactive)
python organize_lab_scans.py "/your/scan/folder" --all --force

# Skip existing files
python organize_lab_scans.py "/your/scan/folder" --all --force --skip
```

## Output Files

- `edits_report.csv` - List of detected edits
- `outliers_report.csv` - List of detected outliers

---

**Remember: Always backup your data before letting an AI move your files!**
