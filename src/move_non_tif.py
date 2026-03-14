import os
import shutil
import sys

def move_non_tif(root_folder, exclude_folders=None, not_tif_folder_name='Not TIFF'):
    if exclude_folders is None:
        exclude_folders = {'Edits', 'Non Film Scanner', 'Not TIFF'}
    
    moved = []
    
    for dirpath, dirnames, filenames in os.walk(root_folder):
        dirnames[:] = [d for d in dirnames if d not in exclude_folders]
        
        for fname in filenames:
            ext = os.path.splitext(fname)[1].lower()
            if ext not in ['.tif', '.tiff']:
                src = os.path.join(dirpath, fname)
                
                not_tif_folder = os.path.join(dirpath, not_tif_folder_name)
                os.makedirs(not_tif_folder, exist_ok=True)
                
                dst = os.path.join(not_tif_folder, fname)
                shutil.move(src, dst)
                moved.append((src, dst))
    
    return moved

def main():
    if len(sys.argv) < 2:
        print("Usage: python move_non_tif.py <folder> [Not_Tif_folder_name]")
        print("  Default Not_Tif_folder_name: Not TIFF")
        sys.exit(1)
    
    folder = sys.argv[1]
    not_tif_folder = sys.argv[2] if len(sys.argv) > 2 else 'Not TIFF'
    
    moved = move_non_tif(folder, not_tif_folder_name=not_tif_folder)
    
    print(f"Moved {len(moved)} non-TIF files")
    
    by_folder = {}
    for src, dst in moved:
        folder = os.path.dirname(dst)
        by_folder.setdefault(folder, 0)
        by_folder[folder] += 1
    
    if moved:
        print("\nBy folder:")
        for folder, count in sorted(by_folder.items()):
            print(f"  {os.path.basename(folder)}: {count}")

if __name__ == '__main__':
    main()
