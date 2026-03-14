import os
import csv
import shutil
import sys

def move_edits(root_folder, edits_csv, edits_folder_name='Edits', skip_existing=False):
    moved = []
    skipped = []
    
    with open(edits_csv, 'r') as f:
        reader = csv.DictReader(f)
        for row in reader:
            if row['is_edit'] == 'True':
                rel_path = row['path']
                src = os.path.join(root_folder, rel_path)
                
                folder = os.path.dirname(rel_path)
                if not folder:
                    continue
                
                edits_folder = os.path.join(root_folder, folder, edits_folder_name)
                os.makedirs(edits_folder, exist_ok=True)
                
                filename = row['filename']
                dst = os.path.join(edits_folder, filename)
                
                if os.path.exists(src):
                    if os.path.exists(dst):
                        if skip_existing:
                            skipped.append(dst)
                            continue
                        print(f"Warning: Overwrite: {dst}")
                    try:
                        shutil.move(src, dst)
                        moved.append((src, dst))
                    except (OSError, IOError) as e:
                        print(f"Warning: Failed to move {src}: {e}")
                else:
                    print(f"Missing: {src}")
    
    return moved, skipped


def move_non_scanner(root_folder, outliers_csv, non_scanner_folder_name='Non Film Scanner', skip_existing=False):
    with open(outliers_csv, 'r') as f:
        reader = csv.DictReader(f)
        dslr_files = [row for row in reader if row['outlier_reason'] == 'dslr_shot']
    
    if not dslr_files:
        return [], []
    
    folder_groups = {}
    for row in dslr_files:
        folder = os.path.dirname(row['path'])
        if folder not in folder_groups:
            folder_groups[folder] = []
        folder_groups[folder].append(row)
    
    moved = []
    skipped = []
    
    for folder, files in folder_groups.items():
        folder_path = os.path.join(root_folder, folder)
        
        all_files_in_folder = set()
        for f in os.listdir(folder_path):
            if os.path.isfile(os.path.join(folder_path, f)):
                all_files_in_folder.add(f)
        
        dslr_filenames = set(f['filename'] for f in files)
        
        if all_files_in_folder == dslr_filenames:
            folder_name = os.path.basename(folder)
            if folder:
                parent_of_folder = os.path.dirname(folder)
                dest_folder = os.path.join(root_folder, parent_of_folder, non_scanner_folder_name, folder_name)
            else:
                dest_folder = os.path.join(root_folder, non_scanner_folder_name, folder_name)
            os.makedirs(dest_folder, exist_ok=True)
            for row in files:
                src = os.path.join(root_folder, row['path'])
                dst = os.path.join(dest_folder, row['filename'])
                if os.path.exists(src):
                    if os.path.exists(dst):
                        if skip_existing:
                            skipped.append(dst)
                            continue
                        print(f"Warning: Overwrite: {dst}")
                    try:
                        shutil.move(src, dst)
                        moved.append((src, dst))
                    except (OSError, IOError) as e:
                        print(f"Warning: Failed to move {src}: {e}")
        else:
            ns_folder = os.path.join(root_folder, folder, non_scanner_folder_name)
            os.makedirs(ns_folder, exist_ok=True)
            for row in files:
                src = os.path.join(root_folder, row['path'])
                dst = os.path.join(ns_folder, row['filename'])
                if os.path.exists(src):
                    if os.path.exists(dst):
                        if skip_existing:
                            skipped.append(dst)
                            continue
                        print(f"Warning: Overwrite: {dst}")
                    try:
                        shutil.move(src, dst)
                        moved.append((src, dst))
                    except (OSError, IOError) as e:
                        print(f"Warning: Failed to move {src}: {e}")
    
    return moved, skipped

def main():
    if len(sys.argv) < 3:
        print("Usage: python move_edits.py <folder> <edits_csv> [Edits_folder_name]")
        print("  Default Edits_folder_name: Edits")
        sys.exit(1)
    
    folder = sys.argv[1]
    csv_file = sys.argv[2]
    edits_folder = sys.argv[3] if len(sys.argv) > 3 else 'Edits'
    
    moved = move_edits(folder, csv_file, edits_folder)
    
    print(f"Moved {len(moved)} files to {edits_folder} subfolders")
    
    by_folder = {}
    for src, dst in moved:
        folder = os.path.dirname(dst)
        by_folder.setdefault(folder, 0)
        by_folder[folder] += 1
    
    print("\nBy folder:")
    for folder, count in sorted(by_folder.items()):
        print(f"  {os.path.basename(folder)}: {count}")

if __name__ == '__main__':
    main()
