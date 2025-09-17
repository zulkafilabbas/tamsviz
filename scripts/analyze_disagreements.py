import matplotlib.pyplot as plt
import pandas as pd
import textwrap
from tmv_utils import TmvParser

tmv_files = [
    "/home/robovie/Desktop/August_20_Agreement_Analysis/2025-03-18_s21_merged_tracked_fix_sorted_combined_with_disagreements.tmv",
    "/home/robovie/Desktop/August_20_Agreement_Analysis/2025-04-17_s2_merged_tracked_fix_sorted_combined_with_disagreements.tmv",
    "/home/robovie/Desktop/August_20_Agreement_Analysis/2025-04-27_s44_merged_tracked_fix_sorted_combined_with_disagreements.tmv",
]

# Collect disagreements
all_disagreements = []
for f in tmv_files:
    parser = TmvParser(f)
    disagreements = parser.get_annotations("Disagreements")
    all_disagreements.extend(disagreements)

# Put into DataFrame
df = pd.DataFrame(all_disagreements)

# Aggregate by label
agg = df.groupby("label").agg(
    total_duration=("duration", "sum"),
    count=("label", "size")
).reset_index()

# Sort by total duration
agg = agg.sort_values("total_duration", ascending=False)

# Wrap labels (30 chars per line)
agg["wrapped_label"] = agg["label"].apply(lambda x: "\n".join(textwrap.wrap(x, 30)))

# Plot
plt.figure(figsize=(14, 36))  # much taller figure
plt.barh(
    agg["wrapped_label"],
    agg["total_duration"],
    color="skyblue",
    height=0.6  # slimmer bars, more space
)
plt.yticks(fontsize=6)   # smaller text
plt.xlabel("Total Disagreement Duration (s)", fontsize=8)
plt.ylabel("Disagreement Type", fontsize=8)
plt.title("Disagreements by Type (duration-weighted)", fontsize=8)
plt.gca().invert_yaxis()
plt.tight_layout()
plt.show()
