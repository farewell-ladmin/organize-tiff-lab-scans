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

def find_outliers(root_folder, output_csv, exclude_folders=None, rarity_threshold=0.03, min_count=15):
    if exclude_folders is None:
        exclude_folders = {'Edits', 'Non Film Scanner', 'Not TIFF'}
    
    all_files = []
    all_discovered_fields = set()
    non_tif_files = []
    
    for dirpath, dirnames, filenames in os.walk(root_folder):
        dirnames[:] = [d for d in dirnames if d not in exclude_folders]
        
        for fname in filenames:
            fpath = os.path.join(dirpath, fname)
            ext = os.path.splitext(fname)[1].lower()
            
            if ext not in ['.tif', '.tiff']:
                rel_path = os.path.relpath(fpath, root_folder)
                non_tif_files.append({
                    'path': rel_path,
                    'filename': fname,
                    'extension': ext,
                    'size': os.path.getsize(fpath)
                })
                continue
            
            meta = get_tif_metadata(fpath)
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
    
    return all_files, outliers, field_distributions, non_tif_files

def main():
    if len(sys.argv) < 3:
        print("Usage: python find_outliers.py <folder> <output.csv>")
        sys.exit(1)
    
    folder = sys.argv[1]
    output = sys.argv[2]
    
    print(f"Analyzing: {folder}")
    print(f"Output: {output}")
    print()
    
    all_files, outliers, distributions, non_tif_files = find_outliers(folder, output)
    
    print(f"Scanned {len(all_files)} TIF files")
    print(f"Found {len(non_tif_files)} non-TIF files")
    print(f"Found {len(outliers)} outlier instances")
    
    unique_outlier_files = set(o['filename'] for o in outliers)
    print(f"Unique outlier files: {len(unique_outlier_files)}")
    
    print(f"\nReport saved to: {output}")

if __name__ == '__main__':
    main()
