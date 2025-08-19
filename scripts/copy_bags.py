import csv
import shutil
from pathlib import Path
from tqdm import tqdm

csv_file = Path("/media/robovie/Crucial X9/Selected/bag_selection_summary.csv")
dest_dir = Path("/media/robovie/Crucial X9/August_Annotation")
dest_dir.mkdir(parents=True, exist_ok=True)

def copy_with_progress(src: Path, dest: Path, chunk_size=1024*1024):
    try:
        if dest.exists():
            print(f"Skipping (already exists): {dest}")
            return False
        total = src.stat().st_size
        with open(src, "rb") as fsrc, open(dest, "wb") as fdst, tqdm(
            total=total, unit="B", unit_scale=True, unit_divisor=1024,
            desc=src.name, ascii=True
        ) as bar:
            while True:
                buf = fsrc.read(chunk_size)
                if not buf:
                    break
                fdst.write(buf)
                bar.update(len(buf))
        shutil.copystat(src, dest)
        return True
    except (PermissionError, OSError) as e:
        print(f"Error copying {src}: {e}")
        return False

# Validate CSV file
if not csv_file.exists():
    print(f"CSV file not found: {csv_file}")
    exit(1)

# Process CSV
success_count, skip_count, error_count = 0, 0, 0
with open(csv_file, newline="") as f:
    reader = csv.DictReader(f)
    if "chosen_path" not in reader.fieldnames:
        print(f"CSV missing 'chosen_path' column")
        exit(1)
    
    for row in reader:
        src = Path(row["chosen_path"])
        if not src.exists():
            print(f"Skipping (not found): {src}")
            skip_count += 1
            continue

        dest = dest_dir / src.name
        print(f"Copying {src} -> {dest}")
        if copy_with_progress(src, dest):
            success_count += 1
        else:
            error_count += 1

# Summary
print(f"\n Copy complete: {success_count} files copied, {skip_count} skipped, {error_count} errors")
print(f"Destination: {dest_dir}")