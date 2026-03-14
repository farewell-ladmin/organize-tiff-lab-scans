import os
import csv
import shutil
import sys

def move_edits(root_folder, edits_csv, edits_folder_name='Edits'):
    moved = []
    
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
                    shutil.move(src, dst)
                    moved.append((src, dst))
                else:
                    print(f"Missing: {src}")
    
    return moved

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
