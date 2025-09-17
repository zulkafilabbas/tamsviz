# resample_global_kappa.py

import os
import numpy as np
from sklearn.metrics import cohen_kappa_score, accuracy_score, confusion_matrix
from tmv_utils import TmvParser   # reuse your existing parser!

SAMPLE_RATE = 100  # Hz
DT = 1.0 / SAMPLE_RATE

OA1_DIR = "/home/robovie/Desktop/September_8_Agreement_Analysis/OA1_male"
OA2_DIR = "/home/robovie/Desktop/September_8_Agreement_Analysis/OA2_female"


def collect_fix_sorted_files(oa1_dir, oa2_dir):
    """Match only files ending with _fix_sorted.tmv and present in both OA1 and OA2."""
    oa1_files = {f for f in os.listdir(oa1_dir) if f.endswith("_fix_sorted.tmv")}
    oa2_files = {f for f in os.listdir(oa2_dir) if f.endswith("_fix_sorted.tmv")}
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


if __name__ == "__main__":
    main()
