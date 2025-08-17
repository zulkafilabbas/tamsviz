import os
import glob
import argparse
import csv
import numpy as np
from sklearn.metrics import cohen_kappa_score, confusion_matrix

"""
This script computes *global inter-annotator agreement* across multiple bags of
aligned interval annotations. Each bag (e.g. aligned_intervals_bag1.csv) contains
rows with annotator1, annotator2, and a duration weight for that interval.

- All rows from all bags are concatenated into one dataset. We do NOT average
  per-bag metrics (which would be mathematically incorrect for κ).
- Each row contributes one weighted observation, where "duration" is the weight.
- Cohen’s kappa and overall agreement are computed once globally using
  scikit-learn, with sample_weight = duration.
- The global confusion matrix is produced by pooling (summing) across all bags.
  This is equivalent to element-wise addition of per-bag matrices, ensuring
  consistent label order across the combined dataset.

In short: this script implements the correct *pooled* agreement calculation
(accuracy, κ, and confusion matrix), rather than per-bag averaging.
"""

def load_all_csvs(input_dir):
    """Load all aligned_intervals*.csv files into a list of dicts."""
    files = glob.glob(os.path.join(input_dir, "**", "aligned_intervals_*.csv"), recursive=True)
    if not files:
        raise FileNotFoundError(f"No aligned_intervals_*.csv files found in {input_dir}")

    rows = []
    for f in files:
        bag_id = os.path.basename(f)  # e.g. aligned_intervals_bag1.csv
        with open(f, "r", newline="") as csvfile:
            reader = csv.DictReader(csvfile)
            for row in reader:
                row["source_file"] = bag_id  # provenance only
                rows.append(row)
    return rows

def compute_pooled_metrics(rows, label1="annotator1", label2="annotator2", weight_col="duration"):
    """Compute pooled accuracy, Cohen's kappa, and confusion matrix weighted by duration."""
    ann1, ann2, weights = [], [], []
    for r in rows:
        ann1.append(str(r[label1]))
        ann2.append(str(r[label2]))
        weights.append(float(r[weight_col]))
    ann1, ann2, weights = np.array(ann1), np.array(ann2), np.array(weights)

    # Weighted Cohen's kappa
    kappa = cohen_kappa_score(ann1, ann2, sample_weight=weights)

    # Weighted accuracy
    correct = (ann1 == ann2).astype(float)
    overall_agreement = np.average(correct, weights=weights)

    # Weighted confusion matrix
    # labels = sorted(set(ann1) | set(ann2))
    # keep order as seen in the data
    labels = list(dict.fromkeys(list(ann1) + list(ann2)))

    cm = confusion_matrix(ann1, ann2, labels=labels, sample_weight=weights)

    return {
        "overall_agreement": overall_agreement,
        "cohen_kappa": kappa,
        "confusion_matrix": cm,
        "labels": labels
    }

def main():
    # Hard-coded paths
    input_dir = "kappa_test_by_hand_global"
    out_file = "kappa_test_by_hand_global/global_confusion.csv"

    rows = load_all_csvs(input_dir)
    metrics = compute_pooled_metrics(rows)

    print("=== Global Agreement Metrics ===")
    print(f"Overall agreement: {metrics['overall_agreement']:.4f}")
    print(f"Cohen's kappa: {metrics['cohen_kappa']:.4f}")

    # Export confusion matrix
    with open(out_file, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow([""] + metrics["labels"])  # header row
        for label, row in zip(metrics["labels"], metrics["confusion_matrix"]):
            writer.writerow([label] + list(row))

    print(f"Confusion matrix saved to {out_file}")

if __name__ == "__main__":
    main()
