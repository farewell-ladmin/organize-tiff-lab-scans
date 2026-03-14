"""
Organize Scans - A tool to organize film scanner output

Workflow:
1. Scan for edits (files modified with editing software)
2. Scan for outliers (DSLR shots, non-TIF files)
3. Move edits to Edits/ subfolders
4. Move non-TIF files to Not TIFF/ subfolders

Usage:
    python organize_lab_scans.py <folder>           # Preview only
    python organize_lab_scans.py <folder> --edits    # Edits only
    python organize_lab_scans.py <folder> --outliers # Outliers only
    python organize_lab_scans.py <folder> --move      # Move files only (uses existing CSVs)
    python organize_lab_scans.py <folder> --all       # Full workflow (default)
    python organize_lab_scans.py <folder> --all --force  # Run without confirmation
"""

import os
import sys
import csv
import shutil

def scan_for_edits(root_folder, output_csv, exclude_folders=None):
    import tifffile
    
    if exclude_folders is None:
        exclude_folders = {'Edits', 'Non Film Scanner', 'Not TIFF'}
    
    def get_tif_metadata(filepath):
        try:
            with tifffile.TiffFile(filepath) as tif:
                tags = {}
                for tag in tif.pages[0].tags.values():
                    try:
                        name = tag.name
                        if name in ['Software', 'Make', 'Model', 'Artist', 'Copyright', 
                                   'BitsPerSample', 'XResolution', 'YResolution']:
                            tags[name] = str(tag.value)
                    except:
                        pass
                return tags
        except:
            return {}
    
    def detect_edit(meta, filename):
        reasons = []
        filename_lower = filename.lower()
        name_without_ext = filename_lower.replace('.tif', '').replace('.tiff', '')
        
        artist = meta.get('Artist', '')
        copyright = meta.get('Copyright', '')
        software = meta.get('Software', '')
        bits = meta.get('BitsPerSample', '')
        xres = meta.get('XResolution', '')
        
        if artist and artist != 'None':
            reasons.append('Artist')
        if copyright and copyright != 'None':
            reasons.append('Copyright')
        if 'Luminar' in software:
            reasons.append('Luminar')
        if 'Lightroom' in software and 'Windows' in software:
            if any(v in software for v in ['13.', '14.', '15.']):
                reasons.append('Lightroom(Win)')
        if '16' in bits:
            reasons.append('16-bit')
        if xres == '(240, 1)':
            reasons.append('DPI=240')
        
        if any(x in name_without_ext for x in ['-edit', '_original', '-copy']) or \
           name_without_ext.count('-2') > 1 or name_without_ext.count('-3') > 1 or \
           ('_' in name_without_ext and name_without_ext.endswith(('-2', '-3'))):
            reasons.append('filename')
        
        return len(reasons) > 0, reasons
    
    results = []
    
    for dirpath, dirnames, filenames in os.walk(root_folder):
        dirnames[:] = [d for d in dirnames if d not in exclude_folders]
        
        for fname in filenames:
            if not fname.lower().endswith(('.tif', '.tiff')):
                continue
            
            fpath = os.path.join(dirpath, fname)
            meta = get_tif_metadata(fpath)
            is_edit, reasons = detect_edit(meta, fname)
            
            results.append({
                'path': os.path.relpath(fpath, root_folder),
                'filename': fname,
                'is_edit': is_edit,
                'reasons': '; '.join(reasons) if reasons else 'none'
            })
    
    with open(output_csv, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=['path', 'filename', 'is_edit', 'reasons'])
        writer.writeheader()
        writer.writerows(results)
    
    return results

def find_outliers(root_folder, output_csv, exclude_folders=None):
    import tifffile
    
    if exclude_folders is None:
        exclude_folders = {'Edits', 'Non Film Scanner', 'Not TIFF'}
    
    def get_tif_metadata(filepath):
        try:
            with tifffile.TiffFile(filepath) as tif:
                tags = {}
                for tag in tif.pages[0].tags.values():
                    try:
                        name = tag.name
                        if name in ['Make', 'Model', 'Software', 'Artist', 'Copyright',
                                   'BitsPerSample', 'Compression', 'XResolution', 'YResolution']:
                            tags[name] = str(tag.value)
                    except:
                        pass
                return tags
        except:
            return {}
    
    all_files = []
    non_tif_files = []
    field_values = {}
    
    for dirpath, dirnames, filenames in os.walk(root_folder):
        dirnames[:] = [d for d in dirnames if d not in exclude_folders]
        
        for fname in filenames:
            fpath = os.path.join(dirpath, fname)
            ext = os.path.splitext(fname)[1].lower()
            
            if ext not in ['.tif', '.tiff']:
                non_tif_files.append({'path': os.path.relpath(fpath, root_folder), 'filename': fname})
                continue
            
            meta = get_tif_metadata(fpath)
            meta['_filename'] = fname
            meta['_path'] = os.path.relpath(fpath, root_folder)
            all_files.append(meta)
            
            for k in meta.keys():
                if k.startswith('_'):
                    continue
                if k not in field_values:
                    field_values[k] = {}
                v = meta[k]
                field_values[k][v] = field_values[k].get(v, 0) + 1
    
    outliers = []
    total = len(all_files)
    
    for f in all_files:
        make = f.get('Make', '')
        model = f.get('Model', '')
        if make or model:
            outliers.append({
                'path': f['_path'], 'filename': f['_filename'],
                'outlier_reason': 'dslr_shot', 'field': 'Make/Model',
                'value': f"{make} {model}"[:100]
            })
            continue
        
        for field in ['Make', 'Model', 'Compression', 'BitsPerSample', 'XResolution', 'YResolution']:
            v = f.get(field, '')
            if not v:
                continue
            count = field_values.get(field, {}).get(v, 0)
            if count < min(15, total * 0.03):
                outliers.append({
                    'path': f['_path'], 'filename': f['_filename'],
                    'outlier_reason': f'rare_{field}', 'field': field,
                    'value': v[:100]
                })
                break
    
    for nf in non_tif_files:
        outliers.append({
            'path': nf['path'], 'filename': nf['filename'],
            'outlier_reason': 'non_tif', 'field': 'file_type',
            'value': os.path.splitext(nf['filename'])[1]
        })
    
    with open(output_csv, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=['path', 'filename', 'outlier_reason', 'field', 'value'])
        writer.writeheader()
        writer.writerows(outliers)
    
    return outliers

def move_edits(root_folder, edits_csv, edits_folder='Edits', preview=False):
    files_to_move = []
    with open(edits_csv, 'r') as f:
        reader = csv.DictReader(f)
        for row in reader:
            if row['is_edit'] == 'True':
                src = os.path.join(root_folder, row['path'])
                folder = os.path.dirname(row['path'])
                if not folder:
                    continue
                dst = os.path.join(root_folder, folder, edits_folder, row['filename'])
                files_to_move.append((src, dst))
    
    if preview:
        return files_to_move
    
    moved = []
    for src, dst in files_to_move:
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        if os.path.exists(src):
            shutil.move(src, dst)
            moved.append(dst)
    return moved

def move_non_tif(root_folder, exclude_folders=None, not_tif_folder='Not TIFF', preview=False):
    if exclude_folders is None:
        exclude_folders = {'Edits', 'Non Film Scanner', 'Not TIFF'}
    
    files_to_move = []
    for dirpath, dirnames, filenames in os.walk(root_folder):
        dirnames[:] = [d for d in dirnames if d not in exclude_folders]
        for fname in filenames:
            ext = os.path.splitext(fname)[1].lower()
            if ext not in ['.tif', '.tiff']:
                src = os.path.join(dirpath, fname)
                dst = os.path.join(dirpath, not_tif_folder, fname)
                files_to_move.append((src, dst))
    
    if preview:
        return files_to_move
    
    moved = []
    for src, dst in files_to_move:
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        shutil.move(src, dst)
        moved.append(dst)
    return moved

def prompt_confirm(message):
    response = input(f"{message} [y/n] ").strip().lower()
    return response in ('y', 'yes')

def main():
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)
    
    folder = sys.argv[1]
    
    do_all = '--all' in sys.argv
    do_edits = '--edits' in sys.argv or do_all
    do_outliers = '--outliers' in sys.argv or do_all
    do_move = '--move' in sys.argv or do_all
    force = '--force' in sys.argv
    
    edits_csv = 'edits_report.csv'
    outliers_csv = 'outliers_report.csv'
    
    if do_edits:
        print("Scanning for edits...")
        results = scan_for_edits(folder, edits_csv)
        edits = [r for r in results if r['is_edit']]
        print(f"  Found {len(edits)} edits, {len(results) - len(edits)} originals")
        print(f"  Saved to {edits_csv}")
    
    if do_outliers:
        print("Scanning for outliers...")
        outliers = find_outliers(folder, outliers_csv)
        dslr = [o for o in outliers if o['outlier_reason'] == 'dslr_shot']
        non_tif = [o for o in outliers if o['outlier_reason'] == 'non_tif']
        print(f"  Found {len(dslr)} DSLR shots, {len(non_tif)} non-TIF files")
        print(f"  Saved to {outliers_csv}")
    
    if do_move:
        edits_to_move = []
        non_tif_to_move = []
        
        if do_edits:
            edits_to_move = move_edits(folder, edits_csv, preview=True)
        if do_outliers or do_all:
            non_tif_to_move = move_non_tif(folder, preview=True)
        
        print("\n=== Summary ===")
        if edits_to_move:
            print(f"Edits to move: {len(edits_to_move)}")
            for src, dst in edits_to_move[:5]:
                print(f"  {os.path.basename(src)} -> {os.path.basename(os.path.dirname(dst))}/Edits/")
            if len(edits_to_move) > 5:
                print(f"  ... and {len(edits_to_move) - 5} more")
        
        if non_tif_to_move:
            print(f"Non-TIF files to move: {len(non_tif_to_move)}")
            for src, dst in non_tif_to_move[:5]:
                print(f"  {os.path.basename(src)} -> {os.path.basename(os.path.dirname(dst))}/Not TIFF/")
            if len(non_tif_to_move) > 5:
                print(f"  ... and {len(non_tif_to_move) - 5} more")
        
        if not edits_to_move and not non_tif_to_move:
            print("Nothing to move.")
        elif force:
            print("\nRunning with --force, proceeding...")
        else:
            print()
            if not prompt_confirm("Proceed with moving files?"):
                print("Aborted.")
                return
        
        if do_edits and edits_to_move:
            print("Moving edits...")
            moved = move_edits(folder, edits_csv)
            print(f"  Moved {len(moved)} files")
        if (do_outliers or do_all) and non_tif_to_move:
            print("Moving non-TIF files...")
            moved = move_non_tif(folder)
            print(f"  Moved {len(moved)} files")
    
    print("\nDone!")

if __name__ == '__main__':
    main()
