import os
import tifffile
import csv
import sys

def get_tif_metadata(filepath):
    try:
        with tifffile.TiffFile(filepath) as tif:
            tags = {}
            for tag in tif.pages[0].tags.values():
                try:
                    name = tag.name
                    if name in ['Software', 'Make', 'Model', 'DateTime', 'DateTimeOriginal', 
                               'Artist', 'Copyright', 'ImageDescription', 'XResolution', 
                               'YResolution', 'ResolutionUnit', 'Orientation', 'BitsPerSample',
                               'Compression', 'Photometric', 'SamplesPerPixel', 'PageNumber',
                               'HostComputer', 'InstrumentSerialNumber']:
                        tags[name] = str(tag.value)
                except:
                    pass
            tags['_file_mtime'] = os.path.getmtime(filepath)
            tags['_file_size'] = os.path.getsize(filepath)
            return tags
    except Exception as e:
        return {'_error': str(e)}

def detect_edit(meta, filename):
    reasons = []
    filename_lower = filename.lower()
    
    if meta.get('_error'):
        return 'error', [meta['_error']]
    
    artist = meta.get('Artist', '')
    copyright = meta.get('Copyright', '')
    software = meta.get('Software', '')
    bits = meta.get('BitsPerSample', '')
    xres = meta.get('XResolution', '')
    
    if artist and artist != 'None':
        reasons.append(f'Artist="{artist}"')
    
    if copyright and copyright != 'None':
        reasons.append(f'Copyright="{copyright}"')
    
    if 'Luminar' in software:
        reasons.append(f'Software=Luminar')
    
    if 'Lightroom' in software and 'Windows' in software:
        if '13.' in software or '14.' in software or '15.' in software:
            reasons.append(f'Software=Lightroom(Win)')
    
    if '16' in bits:
        reasons.append(f'16-bit')
    
    if xres and xres not in ['(72, 1)', '(720000, 10000)', '(300, 1)']:
        if xres == '(240, 1)':
            reasons.append(f'DPI=240')
    
    name_without_ext = filename_lower.replace('.tif', '').replace('.tiff', '')
    
    has_filename_marker = False
    if '-edit' in name_without_ext:
        has_filename_marker = True
    elif '_original' in name_without_ext:
        has_filename_marker = True
    elif '-copy' in name_without_ext or 'copy' in name_without_ext:
        has_filename_marker = True
    elif name_without_ext.count('-2') > 1:
        has_filename_marker = True
    elif name_without_ext.count('-3') > 1:
        has_filename_marker = True
    elif '_' in name_without_ext and (name_without_ext.endswith('-2') or name_without_ext.endswith('-3')):
        has_filename_marker = True
    
    if has_filename_marker:
        reasons.append('filename=-2/-3/-Edit/-Copy')
    
    is_edit = len(reasons) > 0
    
    return is_edit, reasons

def scan_for_edits(root_folder, output_csv, exclude_folders=None):
    if exclude_folders is None:
        exclude_folders = {'Edits', 'Non Film Scanner', 'Not TIFF'}
    
    results = []
    folders_scanned = 0
    files_scanned = 0
    
    for dirpath, dirnames, filenames in os.walk(root_folder):
        dirnames[:] = [d for d in dirnames if d not in exclude_folders]
        folders_scanned += 1
        tif_files = [f for f in filenames if f.lower().endswith(('.tif', '.tiff'))]
        
        for fname in tif_files:
            fpath = os.path.join(dirpath, fname)
            files_scanned += 1
            
            meta = get_tif_metadata(fpath)
            is_edit, reasons = detect_edit(meta, fname)
            
            rel_path = os.path.relpath(fpath, root_folder)
            
            results.append({
                'path': rel_path,
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
    
    return folders_scanned, files_scanned, results

def main():
    if len(sys.argv) < 3:
        print("Usage: python scan_edits.py <folder> <output.csv>")
        sys.exit(1)
    
    folder = sys.argv[1]
    output = sys.argv[2]
    
    print(f"Scanning: {folder}")
    print(f"Output: {output}")
    print()
    
    folders, files, results = scan_for_edits(folder, output)
    
    edits = [r for r in results if r['is_edit']]
    originals = [r for r in results if not r['is_edit']]
    
    print(f"Scanned {folders} folders, {files} TIF files")
    print(f"Found {len(edits)} edits, {len(originals)} originals")
    print(f"\nReport saved to: {output}")

if __name__ == '__main__':
    main()
