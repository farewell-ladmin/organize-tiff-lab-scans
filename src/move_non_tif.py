import os
import shutil
import sys


def is_tiff_by_content(filepath):
    try:
        with open(filepath, 'rb') as f:
            header = f.read(4)
            if len(header) < 4:
                return False
            magic = header[:2]
            if magic == b'II' or magic == b'MM':
                return True
            return False
    except Exception:
        return False


def get_file_ext(filename):
    filename_lower = filename.lower()
    if filename_lower.endswith('.tiff'):
        return '.tiff'
    if filename_lower.endswith('.tif'):
        return '.tif'
    if '.tif_' in filename_lower or '.tiff_' in filename_lower:
        return '.tif'
    return os.path.splitext(filename)[1].lower()


def move_non_tif(root_folder, exclude_folders=None, not_tif_folder_name='Not TIFF', skip_existing=False):
    if exclude_folders is None:
        exclude_folders = {'Edits', 'Non Film Scanner', 'Not TIFF'}
    
    ignored_files = {'.DS_Store', 'Thumbs.db', 'desktop.ini'}
    
    moved = []
    skipped = []
    
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
                
                not_tif_folder = os.path.join(dirpath, not_tif_folder_name)
                os.makedirs(not_tif_folder, exist_ok=True)
                
                dst = os.path.join(not_tif_folder, fname)
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
