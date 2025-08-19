from pathlib import Path
import csv

base_dir = Path("/media/robovie/Crucial X9/Selected")
output_csv = base_dir / "bag_selection_summary.csv"

# Dictionary: key = session_id, value = {"chosen": Path, "replaced": Path or None}
sessions = {}

# 1. Collect fixed bags
for f in base_dir.rglob("*.bag"):
    name = f.name
    if name.endswith(("fix_sorted.bag", "manual_fix_sorted.bag")):
        key = name.replace("_fix_sorted.bag", "").replace("_manual_fix_sorted.bag", "")
        sessions[key] = {"chosen": f.resolve(), "replaced": None}

# 2. Collect tracked bags (only use if no fixed chosen)
for f in base_dir.glob("*_merged_tracked.bag"):
    key = f.stem
    if key not in sessions:
        sessions[key] = {"chosen": f.resolve(), "replaced": None}
    else:
        sessions[key]["replaced"] = f.resolve()

# 3. Print and compute totals
total_size = 0
print("Final bag selection (preferring fixed if available):\n")
for key in sorted(sessions.keys()):
    chosen = sessions[key]["chosen"]
    replaced = sessions[key]["replaced"]
    size_gb = chosen.stat().st_size / (1024**3)
    total_size += chosen.stat().st_size

    if replaced:
        print(f"[FIXED]  {chosen}  ({size_gb:.2f} GB)  <- replaced {replaced.name}")
    else:
        print(f"[TRACKED] {chosen}  ({size_gb:.2f} GB)")

print("\n=== SUMMARY ===")
print(f"Total bags chosen: {len(sessions)}")
print(f"Total size: {total_size / (1024**3):.2f} GB")

# 4. Write CSV
with open(output_csv, "w", newline="") as csvfile:
    writer = csv.writer(csvfile)
    writer.writerow(["session_id", "chosen_path", "size_GB", "replaced_path"])
    for key in sorted(sessions.keys()):
        chosen = sessions[key]["chosen"]
        replaced = sessions[key]["replaced"]
        size_gb = chosen.stat().st_size / (1024**3)
        writer.writerow([key, str(chosen), f"{size_gb:.2f}", str(replaced) if replaced else ""])

print(f"\nCSV summary written to {output_csv}")
