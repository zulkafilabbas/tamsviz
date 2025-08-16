import os
import re
import yaml
import csv
from collections import defaultdict, Counter
import math
from sklearn.metrics import cohen_kappa_score, confusion_matrix, accuracy_score
import numpy as np
import csv

class Agreement:
    """
    Compute inter-annotator agreement from a combined .tmv file,
    output disagreement tracks, and compute agreement metrics.
    """

    def __init__(self, tmv_path: str):
        self.tmv_path = os.path.abspath(tmv_path)
        with open(self.tmv_path, "r") as f:
            self.tmv_data = yaml.safe_load(f)

        self.spans_by_annotator = defaultdict(list)

    def extract_spans(self):
        timeline = self.tmv_data.get("Timeline", {})
        tracks = timeline.get("Tracks", [])

        for track in tracks:
            track_label = str(track.get("Label", ""))
            m = re.match(r"(.+)_([^_]+)$", track_label)
            if not m:
                continue
            track_id, annotator = m.group(1), m.group(2)

            for branch in track.get("Branches", []):
                for span in branch.get("Spans", []):
                    start = span.get("Start")
                    dur = span.get("Duration")
                    end = start + dur if start is not None and dur is not None else None
                    label = span.get("Label", "")
                    span_id = span.get("id")

                    self.spans_by_annotator[annotator].append({
                        "track_id": track_id,
                        "start": start,
                        "end": end,
                        "duration": dur,
                        "label": label,
                        "span_id": span_id,
                    })

        return self.spans_by_annotator

    def align_and_compare(self):
        """
        Align spans track-by-track and return aligned intervals
        with both annotator labels (agreement + disagreement).
        """
        aligned = []

        spans_per_track = defaultdict(lambda: defaultdict(list))
        for annotator, spans in self.spans_by_annotator.items():
            for span in spans:
                spans_per_track[span["track_id"]][annotator].append(span)

        for track_id, ann_dict in spans_per_track.items():
            if len(ann_dict) != 2:
                continue
            a1, a2 = list(ann_dict.keys())
            spans1, spans2 = ann_dict[a1], ann_dict[a2]

            cut_points = set()
            for s in spans1 + spans2:
                cut_points.add(s["start"])
                cut_points.add(s["end"])
            cut_points = sorted(cp for cp in cut_points if cp is not None)

            for i in range(len(cut_points) - 1):
                t0, t1 = cut_points[i], cut_points[i+1]

                def label_at(spans, t0, t1):
                    for s in spans:
                        if s["start"] <= t0 and s["end"] >= t1:
                            return s["label"]
                    return None

                l1 = label_at(spans1, t0, t1)
                l2 = label_at(spans2, t0, t1)

                if l1 is None and l2 is None:
                    continue

                aligned.append({
                    "track_id": track_id,
                    "start": t0,
                    "end": t1,
                    "duration": t1 - t0,
                    "annotator1": l1,
                    "annotator2": l2,
                    "agree": l1 == l2 and l1 is not None
                })

        return aligned



    def compute_metrics(self, aligned_intervals, csv_out="aligned_intervals.csv"):
        """Compute agreement metrics using sklearn + save intervals to CSV."""

        # Flatten into parallel label sequences (weighted by duration)
        labels1, labels2, weights = [], [], []
        for s in aligned_intervals:
            if s["annotator1"] is None and s["annotator2"] is None:
                continue
            l1 = s["annotator1"] if s["annotator1"] is not None else "∅"
            l2 = s["annotator2"] if s["annotator2"] is not None else "∅"
            labels1.append(l1)
            labels2.append(l2)
            weights.append(s["duration"])

        # Convert to arrays
        labels1 = np.array(labels1)
        labels2 = np.array(labels2)
        weights = np.array(weights)

        # Metrics
        overall_acc = accuracy_score(labels1, labels2, sample_weight=weights)
        kappa = cohen_kappa_score(labels1, labels2, sample_weight=weights)
        conf = confusion_matrix(labels1, labels2, sample_weight=weights)

        # Write CSV
        with open(csv_out, "w", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=aligned_intervals[0].keys())
            writer.writeheader()
            writer.writerows(aligned_intervals)

        return {
            "overall_agreement": overall_acc,
            "cohen_kappa": kappa,
            "confusion_matrix": conf.tolist(),
        }


# Example usage
if __name__ == "__main__":
    agreement = Agreement("test_merged_large_overlap/1_combined.tmv")
    agreement.extract_spans()
    aligned = agreement.align_and_compare()
    metrics = agreement.compute_metrics(aligned, "aligned_intervals.csv")
    print("Metrics:", metrics)
