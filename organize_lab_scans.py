"""
Organize Scans - A tool to organize film scanner output

Workflow:
1. Scan for edits (files modified with editing software)
2. Scan for outliers (DSLR shots, non-TIF files)
3. Move edits to Edits/ subfolders
4. Move non-TIF files to Not TIFF/ subfolders
"""

import os
import sys
import csv
import shutil
import argparse

from src.scan_edits import get_tif_metadata, detect_edit, scan_for_edits
from src.find_outliers import find_outliers
from src.move_edits import move_edits as move_edits_func, move_non_scanner
from src.move_non_tif import move_non_tif as move_non_tif_func, get_file_ext, is_tiff_by_content


def validate_path(folder):
    if not os.path.exists(folder):
        raise ValueError(f"Path does not exist: {folder}")
    if not os.path.isdir(folder):
        raise ValueError(f"Path is not a directory: {folder}")
    if os.path.islink(folder):
        raise ValueError(f"Path is a symlink (not allowed): {folder}")
    if not os.access(folder, os.R_OK):
        raise ValueError(f"Path is not readable: {folder}")
    if not os.access(folder, os.W_OK):
        raise ValueError(f"Path is not writable: {folder}")
    
    abs_folder = os.path.abspath(folder)
    if abs_folder.startswith('/Volumes/') or abs_folder.startswith('/mnt/') or '//' in abs_folder:
        print(f"Warning: Running on network share ({abs_folder})")
        print("  Network shares can be slow and may have file locking issues.")
        print("  Consider running on local copy first, then syncing back.")
    
    return True


def is_path_safe(root_folder, rel_path):
    abs_root = os.path.abspath(root_folder)
    abs_target = os.path.abspath(os.path.join(root_folder, rel_path))
    return abs_target.startswith(abs_root + os.sep) or abs_target == abs_root


def check_overwrite(dst, skip=False):
    if os.path.exists(dst):
        if skip:
            return False
        print(f"Warning: Overwrite detected: {dst}")
        return True
    return True


def safe_move(src, dst, retries=3):
    import time
    for attempt in range(retries):
        try:
            shutil.move(src, dst)
            return True
        except (OSError, IOError) as e:
            if attempt < retries - 1:
                time.sleep(0.5 * (attempt + 1))
            else:
                print(f"Warning: Failed to move {src}: {e}")
                return False
    return False


def scan_with_cache(root_folder, output_csv, exclude_folders=None):
    if exclude_folders is None:
        exclude_folders = {'Edits', 'Non Film Scanner', 'Not TIFF'}
    
    results = []
    cache = {}
    
    for dirpath, dirnames, filenames in os.walk(root_folder):
        dirnames[:] = [d for d in dirnames if d not in exclude_folders]
        
        for fname in filenames:
            ext = get_file_ext(fname)
            if ext not in ['.tif', '.tiff']:
                continue
            
            fpath = os.path.join(dirpath, fname)
            
            if fpath not in cache:
                cache[fpath] = get_tif_metadata(fpath)
            
            meta = cache[fpath]
            is_edit, reasons = detect_edit(meta, fname)
            
            results.append({
                'path': os.path.relpath(fpath, root_folder),
                'filename': fname,
                'is_edit': is_edit,
                'reasons': '; '.join(reasons) if reasons else 'none',
                'artist': meta.get('Artist', ''),
                'copyright': meta.get('Copyright', ''),
                'software': meta.get('Software', ''),
                'bits': meta.get('BitsPerSample', ''),
                'xres': meta.get('XResolution', ''),
                'file_size': meta.get('_file_size', 0),
            })
    
    with open(output_csv, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=['path', 'filename', 'is_edit', 'reasons', 
                                                 'artist', 'copyright', 'software', 
                                                 'bits', 'xres', 'file_size'])
        writer.writeheader()
        writer.writerows(results)
    
    return results, cache


def find_outliers_with_cache(root_folder, output_csv, metadata_cache, exclude_folders=None):
    if exclude_folders is None:
        exclude_folders = {'Edits', 'Non Film Scanner', 'Not TIFF'}
    
    all_files = []
    all_discovered_fields = set()
    non_tif_files = []
    
    for dirpath, dirnames, filenames in os.walk(root_folder):
        dirnames[:] = [d for d in dirnames if d not in exclude_folders]
        
        for fname in filenames:
            fpath = os.path.join(dirpath, fname)
            ext = get_file_ext(fname)
            
            if ext not in ['.tif', '.tiff']:
                rel_path = os.path.relpath(fpath, root_folder)
                non_tif_files.append({
                    'path': rel_path,
                    'filename': fname,
                    'extension': ext,
                    'size': os.path.getsize(fpath)
                })
                continue
            
            if fpath in metadata_cache:
                meta = metadata_cache[fpath].copy()
            else:
                meta = get_tif_metadata(fpath)
                metadata_cache[fpath] = meta
            
            meta['_filename'] = fname
            meta['_path'] = os.path.relpath(fpath, root_folder)
            all_files.append(meta)
            
            for k in meta.keys():
                if not k.startswith('_'):
                    all_discovered_fields.add(k)
    
    exclude_fields = {'DateTime', 'DateTimeOriginal', 'HostComputer', 'PageNumber', 
                     'StripByteCounts', 'RowsPerStrip', 'StripOffsets', 'TileOffsets',
                     'TileByteCounts', 'XPosition', 'YPosition', 'Software'}
    
    target_fields = [f for f in sorted(all_discovered_fields) if f not in exclude_fields]
    
    field_distributions = {k: {} for k in target_fields}
    
    for f in all_files:
        if '_error' in f:
            continue
        for field in target_fields:
            v = f.get(field, '')
            if v:
                field_distributions[field][v] = field_distributions[field].get(v, 0) + 1
    
    outliers = []
    total = len(all_files)
    rarity_threshold = 0.03
    min_count = 15
    
    for f in all_files:
        if '_error' in f:
            continue
        
        make = f.get('Make', '')
        model = f.get('Model', '')
        if make or model:
            outliers.append({
                'path': f['_path'],
                'filename': f['_filename'],
                'outlier_reason': 'dslr_shot',
                'field': 'Make/Model',
                'value': f"{make} {model}"[:100],
                'field_freq': 'N/A',
                'count': field_distributions['Make'].get(make, 1) if make else 1,
                'total_files': total
            })
            continue
        
        for field in target_fields:
            v = f.get(field, '')
            if not v:
                continue
            
            count = field_distributions[field].get(v, 0)
            ratio = count / total
            
            if ratio < rarity_threshold and count < min_count:
                outliers.append({
                    'path': f['_path'],
                    'filename': f['_filename'],
                    'outlier_reason': f'rare_{field.lower()}',
                    'field': field,
                    'value': v[:100],
                    'field_freq': f"{ratio:.1%}",
                    'count': count,
                    'total_files': total
                })
                break
    
    for nf in non_tif_files:
        outliers.append({
            'path': nf['path'],
            'filename': nf['filename'],
            'outlier_reason': f'non_tif_{nf["extension"]}',
            'field': 'file_type',
            'value': nf['extension'],
            'field_freq': 'N/A',
            'count': 1,
            'total_files': total
        })
    
    with open(output_csv, 'w', newline='', encoding='utf-8') as csvfile:
        fieldnames = ['path', 'filename', 'outlier_reason', 'field', 'value', 'field_freq', 'count', 'total_files']
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(outliers)
    
    return outliers, non_tif_files


def move_edits_wrapper(root_folder, edits_csv, edits_folder='Edits', preview=False, skip_existing=False):
    if preview:
        files_to_move = []
        with open(edits_csv, 'r') as f:
            reader = csv.DictReader(f)
            for row in reader:
                if row['is_edit'] == 'True':
                    rel_path = row['path']
                    if not is_path_safe(root_folder, rel_path):
                        print(f"Warning: Path traversal attempt blocked: {rel_path}")
                        continue
                    src = os.path.join(root_folder, rel_path)
                    folder = os.path.dirname(rel_path)
                    if not folder:
                        continue
                    dst = os.path.join(root_folder, folder, edits_folder, row['filename'])
                    files_to_move.append((src, dst))
        return files_to_move
    
    return move_edits_func(root_folder, edits_csv, edits_folder, skip_existing)


def move_non_tif_wrapper(root_folder, exclude_folders=None, not_tif_folder='Not TIFF', preview=False, skip_existing=False):
    if exclude_folders is None:
        exclude_folders = {'Edits', 'Non Film Scanner', 'Not TIFF'}
    
    ignored_files = {'.DS_Store', 'Thumbs.db', 'desktop.ini'}
    
    if preview:
        files_to_move = []
        for dirpath, dirnames, filenames in os.walk(root_folder):
            dirnames[:] = [d for d in dirnames if d not in exclude_folders]
            for fname in filenames:
                if fname in ignored_files:
                    continue
                ext = get_file_ext(fname)
                if ext not in ['.tif', '.tiff']:
                    src = os.path.join(dirpath, fname)
                    if is_tiff_by_content(src):
                        continue
                    dst = os.path.join(dirpath, not_tif_folder, fname)
                    files_to_move.append((src, dst))
        return files_to_move
    
    return move_non_tif_func(root_folder, exclude_folders, not_tif_folder, skip_existing)


def move_non_scanner_wrapper(root_folder, outliers_csv, non_scanner_folder='Non Film Scanner', preview=False, skip_existing=False):
    if preview:
        with open(outliers_csv, 'r') as f:
            reader = csv.DictReader(f)
            dslr_files = [row for row in reader if row['outlier_reason'] == 'dslr_shot']
        
        if not dslr_files:
            return []
        
        folder_groups = {}
        for row in dslr_files:
            folder = os.path.dirname(row['path'])
            if folder not in folder_groups:
                folder_groups[folder] = []
            folder_groups[folder].append(row)
        
        files_to_move = []
        
        for folder, files in folder_groups.items():
            if not is_path_safe(root_folder, folder):
                print(f"Warning: Path traversal attempt blocked: {folder}")
                continue
            
            folder_path = os.path.join(root_folder, folder)
            
            all_files_in_folder = set()
            try:
                for f in os.listdir(folder_path):
                    if os.path.isfile(os.path.join(folder_path, f)):
                        all_files_in_folder.add(f)
            except OSError:
                continue
            
            dslr_filenames = set(f['filename'] for f in files)
            
            if all_files_in_folder == dslr_filenames:
                folder_name = os.path.basename(folder)
                if folder:
                    parent_of_folder = os.path.dirname(folder)
                    dest_folder = os.path.join(root_folder, parent_of_folder, non_scanner_folder, folder_name)
                else:
                    dest_folder = os.path.join(root_folder, non_scanner_folder, folder_name)
                for row in files:
                    src = os.path.join(root_folder, row['path'])
                    dst = os.path.join(dest_folder, row['filename'])
                    files_to_move.append((src, dst))
            else:
                ns_folder = os.path.join(root_folder, folder, non_scanner_folder)
                for row in files:
                    src = os.path.join(root_folder, row['path'])
                    dst = os.path.join(ns_folder, row['filename'])
                    files_to_move.append((src, dst))
        
        return files_to_move
    
    return move_non_scanner(root_folder, outliers_csv, non_scanner_folder)


def prompt_confirm(message):
    try:
        if not sys.stdin.isatty():
            print(f"{message} [y/n] (non-interactive, aborting]")
            return False
        response = input(f"{message} [y/n] ").strip().lower()
        return response in ('y', 'yes')
    except (EOFError, KeyboardInterrupt):
        return False


def main():
    parser = argparse.ArgumentParser(
        description='Organize film scanner output - detect edits and outliers, move files to subfolders.',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog='''
Examples:
  %(prog)s /path/to/scans              # Preview only
  %(prog)s /path/to/scans --edits      # Scan edits only
  %(prog)s /path/to/scans --outliers   # Scan outliers only
  %(prog)s /path/to/scans --all        # Full workflow with confirmation
  %(prog)s /path/to/scans --all --force  # Full workflow without confirmation
  %(prog)s /path/to/scans --all --skip   # Skip existing files on move
        '''
    )
    parser.add_argument('folder', help='Folder containing film scans')
    parser.add_argument('--edits', action='store_true', help='Scan for edited files')
    parser.add_argument('--outliers', action='store_true', help='Scan for outliers (DSLR, non-TIF)')
    parser.add_argument('--move', action='store_true', help='Move files (uses existing CSVs)')
    parser.add_argument('--all', action='store_true', help='Run full workflow (scan + move)')
    parser.add_argument('--force', action='store_true', help='Skip confirmation prompt')
    parser.add_argument('--skip', action='store_true', help='Skip files that already exist')
    
    args = parser.parse_args()
    
    if not os.path.exists(args.folder):
        print(f"Error: Folder does not exist: {args.folder}")
        sys.exit(1)
    
    folder = args.folder
    
    try:
        validate_path(folder)
    except ValueError as e:
        print(f"Error: {e}")
        sys.exit(1)
    
    do_edits = args.edits or args.all
    do_outliers = args.outliers or args.all
    do_move = args.move or args.all
    force = args.force
    skip_overwrites = args.skip
    
    edits_csv = 'edits_report.csv'
    outliers_csv = 'outliers_report.csv'
    
    metadata_cache = {}
    
    if do_edits:
        print("Scanning for edits...")
        if do_outliers:
            results, metadata_cache = scan_with_cache(folder, edits_csv)
        else:
            results, metadata_cache = scan_with_cache(folder, edits_csv)
        edits = [r for r in results if r['is_edit']]
        print(f"  Found {len(edits)} edits, {len(results) - len(edits)} originals")
        print(f"  Saved to {edits_csv}")
    
    if do_outliers:
        print("Scanning for outliers...")
        if metadata_cache:
            outliers, non_tif = find_outliers_with_cache(folder, outliers_csv, metadata_cache)
        else:
            all_files, outliers, distributions, non_tif = find_outliers(folder, outliers_csv)
        dslr = [o for o in outliers if o['outlier_reason'] == 'dslr_shot']
        non_tif_list = [o for o in outliers if 'non_tif' in o['outlier_reason']]
        print(f"  Found {len(dslr)} DSLR shots, {len(non_tif_list)} non-TIF files")
        print(f"  Saved to {outliers_csv}")
    
    if do_move:
        edits_to_move = []
        non_tif_to_move = []
        non_scanner_to_move = []
        
        if do_edits:
            edits_to_move = move_edits_wrapper(folder, edits_csv, preview=True)
        if do_outliers or args.all:
            non_tif_to_move = move_non_tif_wrapper(folder, preview=True)
            non_scanner_to_move = move_non_scanner_wrapper(folder, outliers_csv, preview=True)
        
        print("\n=== Summary ===")
        if edits_to_move:
            print(f"Edits to move: {len(edits_to_move)}")
            for src, dst in edits_to_move[:5]:
                src_folder = os.path.dirname(src)
                parent_folder = os.path.basename(src_folder)
                print(f"  {os.path.basename(src)} -> {parent_folder}/Edits/")
            if len(edits_to_move) > 5:
                print(f"  ... and {len(edits_to_move) - 5} more")
        
        if non_tif_to_move:
            print(f"Non-TIF files to move: {len(non_tif_to_move)}")
            for src, dst in non_tif_to_move[:5]:
                src_folder = os.path.dirname(src)
                parent_folder = os.path.basename(src_folder)
                print(f"  {os.path.basename(src)} -> {parent_folder}/Not TIFF/")
            if len(non_tif_to_move) > 5:
                print(f"  ... and {len(non_tif_to_move) - 5} more")
        
        if non_scanner_to_move:
            print(f"Non-scanner files to move: {len(non_scanner_to_move)}")
            shown_folders = set()
            for src, dst in non_scanner_to_move:
                dst_folder = os.path.dirname(dst)
                if dst_folder not in shown_folders:
                    if dst_folder.startswith(folder):
                        rel_dst = dst_folder[len(folder):].lstrip('/\\')
                    else:
                        rel_dst = dst_folder
                    print(f"  -> {rel_dst}/")
                    shown_folders.add(dst_folder)
            if len(non_scanner_to_move) > len(shown_folders):
                print(f"  ... and {len(non_scanner_to_move) - len(shown_folders)} more files")
            if len(non_scanner_to_move) > 5:
                print(f"  ... and {len(non_scanner_to_move) - 5} more")
        
        if not edits_to_move and not non_tif_to_move and not non_scanner_to_move:
            print("Nothing to move.")
        elif force:
            print("\nRunning with --force, proceeding...")
        else:
            print()
            if not prompt_confirm("Proceed with moving files?"):
                print("Aborted.")
                return
        
        if (do_outliers or args.all) and non_scanner_to_move:
            print("Moving non-scanner files...")
            moved, skipped = move_non_scanner_wrapper(folder, outliers_csv, skip_existing=skip_overwrites)
            print(f"  Moved {len(moved)} files")
            if skipped:
                print(f"  Skipped {len(skipped)} existing files (--skip)")
        if (do_outliers or args.all) and non_tif_to_move:
            print("Moving non-TIF files...")
            moved, skipped = move_non_tif_wrapper(folder, skip_existing=skip_overwrites)
            print(f"  Moved {len(moved)} files")
            if skipped:
                print(f"  Skipped {len(skipped)} existing files (--skip)")
        if do_edits and edits_to_move:
            print("Moving edits...")
            moved, skipped = move_edits_wrapper(folder, edits_csv, skip_existing=skip_overwrites)
            print(f"  Moved {len(moved)} files")
            if skipped:
                print(f"  Skipped {len(skipped)} existing files (--skip)")
    
    print("\nDone!")


if __name__ == '__main__':
    main()
