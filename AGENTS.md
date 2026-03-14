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
3. `src/find_outliers.py` - Outlier detection  
4. `src/move_edits.py` - Move edits
5. `src/move_non_tif.py` - Move non-TIF files

## Configuration Options

### Change Original File Format

Currently looks for: `.tif`, `.tiff`

To add more formats (e.g., `.png`, `.jpg`):

Edit `organize_lab_scans.py` and change:
```python
if not fname.lower().endswith(('.tif', '.tiff')):
```
to:
```python
if not fname.lower().endswith(('.tif', '.tiff', '.png', '.jpg')):
```

### Change What Folders to Ignore

Currently excluded: `Edits`, `Non Film Scanner`, `Not TIFF`

Find lines with:
```python
exclude_folders = {'Edits', 'Non Film Scanner', 'Not TIFF'}
```

And modify the set.

### Change Edit Detection Criteria

In `organize_lab_scans.py`, look for `detect_edit()` function. You can add/remove:

- Artist metadata presence
- Copyright metadata presence  
- Software detection (Luminar, Lightroom versions)
- 16-bit depth detection
- Resolution detection (240 DPI)
- Filename patterns (-2, -3, -Edit, -Copy, _original)

### Change Outlier Detection

In `organize_lab_scans.py`, look for `find_outliers()` function:

- DSLR detection: Looks for Make/Model metadata
- Rare metadata: Currently checks Make, Model, Compression, BitsPerSample, XResolution, YResolution
- Threshold: Currently `< 15 files or < 3%` = outlier

### Change Subfolder Names

- Default: `Edits`, `Not TIFF`, `Non Film Scanner`

Find and replace these strings in the code.

## Example Prompts for Agents

### "Add support for PNG files"
```
Add .png to the file format detection in organize_lab_scans.py. 
Also update move_non_tif.py to handle png files as originals, not non-tif.
```

### "Change my edits detection to look for Photoshop instead of Lightroom"
```
In organize_lab_scans.py, update detect_edit() to flag files with "Photoshop" 
in the Software field as edits, instead of the current Lightroom detection.
```

### "I use Capture One instead of Lightroom"
```
Update detect_edit() to look for "Capture One" in the Software field,
and remove the Lightroom detection.
```

### "Make -final标记为编辑"
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

```bash
# Preview what would happen
python organize_lab_scans.py "/your/scan/folder" --all

# With confirmation  
python organize_lab_scans.py "/your/scan/folder" --all

# Force (no confirmation)
python organize_lab_scans.py "/your/scan/folder" --all --force
```

## Output Files

- `edits_report.csv` - List of detected edits
- `outliers_report.csv` - List of detected outliers

---

**Remember: Always backup your data before letting an AI move your files!**
