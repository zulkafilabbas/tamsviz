# resample_global_kappa.py

# Overview:
# This script takes pairs of annotation files from two annotators, 
# turns their labeled spans into frame-by-frame labels at 100 Hz, 
# and stitches all files together into one long timeline. For every frame, 
# it checks what label each annotator gave (or "NULL_OBJ" if none), 
# so we end up with two parallel streams of labels that can be compared directly. 
# From this, it computes accuracy (how often they match) and Cohen’s kappa (agreement beyond chance), 
# and then visualizes the results with a timeline plot showing when they agreed or disagreed and 
# a confusion matrix heatmap showing which types of labels were confused most often.

# Details
# We repeat this process for every file pair that both annotators worked on.
# Each new file’s labels are shifted forward on the timeline (using an offset) so all files can be stitched into one long global timeline without overlap.
# As we go, we keep extending two global sequences: one for OA1’s labels and one for OA2’s labels.
# Once all files are processed, we have two long parallel label streams — one label per frame per annotator.
# We then compute accuracy (percentage of frames where the labels match) and Cohen’s kappa (agreement beyond chance).
# We also build a confusion matrix to see which labels were confused with which.
# To make the matrix easier to read, we simplify the long label strings into short codes like Shelf+Pick+Int.
# Finally, we visualize:
# A timeline plot showing when annotators agreed vs. disagreed over time.
# A confusion matrix heatmap showing agreement and confusions across label categories.

# Kappa Calculation
# We use cohen_kappa_score from scikit-learn (sklearn.metrics).
# It takes two parallel sequences of categorical labels
# (here: OA1’s labels vs. OA2’s labels, one per sampled frame).
# It computes Cohen’s κ, defined as:
#   κ = (p_o - p_e) / (1 - p_e)
# where:
#   p_o = observed agreement (accuracy = % of frames both annotators match)
#   p_e = expected agreement by chance
#         (calculated from each annotator’s label distribution).
#
# Interpretation:
#   κ = 1   → perfect agreement
#   κ = 0   → agreement is no better than chance
#   κ < 0   → worse than chance (systematic disagreement)
#
# In this code, since labels are nominal categories (not ordered),
# we use the unweighted κ (default in sklearn), which is the standard
# choice for classification-style annotation tasks.

"""
We pair up annotation files from OA1 and OA2, resample them into two long global
timelines (one label per frame per annotator), and ensure a 1-to-1 correspondence
at every frame. These sequences are fed into sklearn.metrics functions to compute
Cohen’s kappa (agreement beyond chance), raw accuracy (percent match), and a
confusion matrix (breakdown of agreements and confusions by label).
"""

"""
Functions used (from sklearn.metrics):

1. accuracy_score(y1, y2)
   - Input: two parallel sequences of labels (OA1 vs. OA2, one per frame).
   - Output: a float between 0 and 1.
   - Meaning: proportion of frames where both annotators gave the same label.

2. cohen_kappa_score(y1, y2)
   - Input: two parallel sequences of labels (OA1 vs. OA2, one per frame).
   - Output: a float between -1 and 1.
       1.0 → perfect agreement
       0.0 → agreement equals chance
       <0.0 → systematic disagreement
   - Meaning: agreement adjusted for chance (accounts for base rates of each label).

3. confusion_matrix(y1, y2, labels=all_labels)
   - Input: two parallel sequences of labels + the list of all possible labels.
   - Output: a 2D array (rows = OA1’s labels, columns = OA2’s labels).
   - Meaning: counts of how often each OA1 label was paired with each OA2 label.
              Diagonal cells = agreements, off-diagonals = disagreements.
"""

import os
import numpy as np
from sklearn.metrics import cohen_kappa_score, accuracy_score, confusion_matrix
from tmv_utils import TmvParser   # reuse your existing parser!
import matplotlib.pyplot as plt
import seaborn as sns   # optional, for nicer heatmaps

SAMPLE_RATE = 100  # Hz
DT = 1.0 / SAMPLE_RATE

OA1_DIR = "/home/robovie/Desktop/September_18_Agreement_Analysis/OA1_male"
OA2_DIR = "/home/robovie/Desktop/September_18_Agreement_Analysis/OA2_female"


def collect_fix_sorted_files(oa1_dir, oa2_dir):
    """Match only files ending with _fix_sorted.tmv and present in both OA1 and OA2."""
    # oa1_files = {f for f in os.listdir(oa1_dir) if f.endswith("_fix_sorted.tmv")}
    # oa2_files = {f for f in os.listdir(oa2_dir) if f.endswith("_fix_sorted.tmv")}

    oa1_files = {f for f in os.listdir(oa1_dir) if f.endswith(".tmv")}
    oa2_files = {f for f in os.listdir(oa2_dir) if f.endswith(".tmv")}

    common = sorted(list(oa1_files & oa2_files))
    return [(os.path.join(oa1_dir, f), os.path.join(oa2_dir, f)) for f in common]


def spans_to_label(spans, t):
    """Find the active label at time t, or NULL_OBJ if none covers it."""
    for s in spans:
        if s["start"] <= t < s["end"]:
            return s["label"]
    return "NULL_OBJ"


def process_pair(file1, file2, global_offset, dt):
    """Resample two matched tmv files and return label sequences + new offset."""
    parser1 = TmvParser(file1)
    parser2 = TmvParser(file2)

    # Collect spans for each annotator
    spans1 = []
    for _, span in parser1.iter_annotations():
        span_copy = dict(span)
        span_copy["start"] += global_offset
        span_copy["end"] += global_offset
        spans1.append(span_copy)

    spans2 = []
    for _, span in parser2.iter_annotations():
        span_copy = dict(span)
        span_copy["start"] += global_offset
        span_copy["end"] += global_offset
        spans2.append(span_copy)

    # If either file has no spans, just skip this pair
    if not spans1 or not spans2:
        print(f"⚠️  Skipping {os.path.basename(file1)} (one annotator has no spans)")
        return [], [], global_offset

    max_end = max(max(s["end"] for s in spans1), max(s["end"] for s in spans2))
    times = np.arange(global_offset, max_end, dt)

    labels1, labels2 = [], []
    for t in times:
        labels1.append(spans_to_label(spans1, t))
        labels2.append(spans_to_label(spans2, t))

    new_offset = max_end + 1.0  # 1 sec padding
    return labels1, labels2, new_offset

def simplify_label(label: str) -> str:
    if label == "NULL_OBJ":
        return "None"
    # Extract key phrases
    parts = []
    if "Moving Through the Store" in label:
        parts.append("Move")
    elif "Standing at the Shelf" in label:
        parts.append("Shelf")
    elif "Standing at the Mirror" in label:
        parts.append("Mirror")
    elif "Standing at the Counter" in label:
        parts.append("Counter")

    if "Idle" in label:
        parts.append("Idle")
    elif "Pick or Place" in label:
        parts.append("Pick")
    elif "Holding Hat" in label:
        parts.append("Hold")
    elif "Wear or Take Off" in label:
        parts.append("Wear")

    if "Interacting" in label:
        if "Not Interacting" in label:
            parts.append("NoInt")
        else:
            parts.append("Int")

    return "+".join(parts) if parts else "Other"


def main():
    pairs = collect_fix_sorted_files(OA1_DIR, OA2_DIR)

    global_labels1, global_labels2 = [], []
    offset = 0.0

    for f1, f2 in pairs:
        print(f"Processing pair: {os.path.basename(f1)}")
        l1, l2, offset = process_pair(f1, f2, offset, DT)
        global_labels1.extend(l1)
        global_labels2.extend(l2)

    # Compute metrics
    kappa = cohen_kappa_score(global_labels1, global_labels2)
    acc = accuracy_score(global_labels1, global_labels2)
    labels = list(dict.fromkeys(global_labels1 + global_labels2))  # preserve order
    cm = confusion_matrix(global_labels1, global_labels2, labels=labels)

    print("\n=== Global Agreement Metrics (Resampled) ===")
    print(f"Overall agreement: {acc:.4f}")
    print(f"Cohen's kappa: {kappa:.4f}")
    print("Confusion matrix:")
    print(labels)
    print(cm)

    # === PLOT 1: Global timeline agreement/disagreement ===
    agreement = [1 if a == b else 0 for a, b in zip(global_labels1, global_labels2)]
    plt.figure(figsize=(15, 3))
    plt.plot(agreement, linewidth=0.5, color="black")
    plt.title("Global Timeline Agreement (1=agree, 0=disagree)")
    plt.xlabel("Sample index")
    plt.ylabel("Agreement")
    plt.tight_layout()
    plt.show()

    # === PLOT 2: Confusion matrix heatmap with counts ===
    labels1_simple = [simplify_label(l) for l in global_labels1]
    labels2_simple = [simplify_label(l) for l in global_labels2]

    unique_labels = sorted(set(labels1_simple) | set(labels2_simple))
    cm = confusion_matrix(labels1_simple, labels2_simple, labels=unique_labels)

    plt.figure(figsize=(10, 8))
    sns.heatmap(cm, annot=True, fmt="g",
                xticklabels=unique_labels, yticklabels=unique_labels,
                cmap="Blues", cbar=True)
    plt.title("Confusion Matrix (Simplified Labels)")
    plt.xlabel("Annotator 2")
    plt.ylabel("Annotator 1")
    plt.tight_layout()
    plt.show()

    print("\n=== Global Agreement Report ===")
    print(f"Frames compared: {len(global_labels1):,}")
    print(f"Accuracy (percent match): {acc:.2%}")
    print(f"Cohen’s kappa: {kappa:.5f}  "
        f"({'poor' if kappa < 0.5 else 'fair' if kappa < 0.6 else 'moderate' if kappa < 0.7 else 'substantial' if kappa < 0.85 else 'almost perfect'})")
    print("\nTop 5 confusion pairs (most frequent disagreements):")
    off_diag = []
    for i, li in enumerate(labels):
        for j, lj in enumerate(labels):
            if i != j and cm[i, j] > 0:
                off_diag.append((cm[i, j], li, lj))
    for count, li, lj in sorted(off_diag, reverse=True)[:5]:
        print(f"  {li} vs {lj}: {int(count)} frames")

if __name__ == "__main__":
    main()
