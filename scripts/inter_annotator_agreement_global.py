import os
import glob
import argparse
import pandas as pd
import numpy as np
from sklearn.metrics import cohen_kappa_score, confusion_matrix, accuracy_score

def load_all_csvs(input_dir):
    """Load all aligned_intervals.csv files from a directory into one DataFrame."""
    files = glob.glob(os.path.join(input_dir, "*.csv"))
    if not files:
        raise FileNotFoundError(f"No CSV files found in {input_dir}")

    dfs = []
    for f in files:
        df = pd.read_csv(f)
        df["bag_id"] = os.path.basename(f)  # keep provenance
        dfs.append(df)
    return pd.concat(dfs, ignore_index=True)

def compute_pooled_metrics(df, label1="annotator1_label", label2="annotator2_label", weight_col="duration"):
    """Compute pooled accuracy, Cohen's kappa, and confusion matrix weighted by duration."""
    # Flatten into repeated samples based on duration (rounded)
    weights = df[weight_col].astype(float)
    ann1 = df[label1].astype(str)
    ann2 = df[label2].astype(str)

    # Weighted Cohen's kappa (duration used as sample weights)
    kappa = cohen_kappa_score(ann1, ann2, sample_weight=weights)

    # Weighted accuracy
    correct = (ann1 == ann2).astype(float)
    overall_agreement = np.average(correct, weights=weights)

    # Weighted confusion matrix
    labels = sorted(set(ann1) | set(ann2))
    cm = confusion_matrix(ann1, ann2, labels=labels, sample_weight=weights)

    return {
        "overall_agreement": overall_agreement,
        "cohen_kappa": kappa,
        "confusion_matrix": cm.tolist(),
        "labels": labels
    }

def main():
    parser = argparse.ArgumentParser(description="Pool per-bag agreement CSVs and compute global metrics.")
    parser.add_argument("input_dir", help="Directory containing aligned_intervals.csv files")
    args = parser.parse_args()

    df = load_all_csvs(args.input_dir)
    metrics = compute_pooled_metrics(df)

    print("=== Global Agreement Metrics ===")
    print(f"Overall agreement: {metrics['overall_agreement']:.4f}")
    print(f"Cohen's kappa: {metrics['cohen_kappa']:.4f}")
    print("Confusion matrix (rows=ann1, cols=ann2):")
    print(pd.DataFrame(metrics["confusion_matrix"], index=metrics["labels"], columns=metrics["labels"]))

if __name__ == "__main__":
    main()
