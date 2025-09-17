import os
import re
import yaml
import csv
from collections import defaultdict
import numpy as np
from sklearn.metrics import cohen_kappa_score, confusion_matrix, accuracy_score

"""
This script computes *pairwise inter-annotator agreement* directly from combined
`.tmv` annotation files (exported timelines with multiple annotators). It supports
both detailed disagreement reporting and global metrics.

1. **Span extraction**: Read each annotator’s tracks from the `.tmv`, normalize
   track/annotator IDs, and collect all labeled spans with start, end, and duration.
2. **Alignment**: For each track, cut time into minimal sub-intervals where labels
   may change (union of all annotators’ start/end points). Each interval is assigned
   the label active for each annotator, or `NULL_OBJ` if none covers it.
3. **Comparison**: Build an aligned list of intervals with annotator1/annotator2
   labels, durations, and a flag marking whether they agree.
4. **Metrics**: Compute weighted accuracy, Cohen’s κ, and the confusion matrix
   using duration as sample weight. Save the aligned intervals to CSV.
5. **Disagreements**: Optionally write a new `.tmv` track containing only
   disagreement spans, with labels reduced to just the differing subcategories.

Key idea: Instead of treating spans independently, we align annotator timelines
to the same cut-points, so overlapping but non-identical segmentations are still
fairly compared. This ensures consistent weighting by duration and allows κ and
the confusion matrix to reflect *all intervals equally* across annotators.
"""


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
        """Align spans track-by-track and return aligned intervals with both annotator labels."""
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
        labels1, labels2, weights = [], [], []
        for s in aligned_intervals:
            if s["annotator1"] is None and s["annotator2"] is None:
                continue
            l1 = s["annotator1"] if s["annotator1"] is not None else "NULL_OBJ"
            l2 = s["annotator2"] if s["annotator2"] is not None else "NULL_OBJ"
            labels1.append(l1)
            labels2.append(l2)
            weights.append(s["duration"])

        labels1 = np.array(labels1)
        labels2 = np.array(labels2)
        weights = np.array(weights)

        overall_acc = accuracy_score(labels1, labels2, sample_weight=weights)
        kappa = cohen_kappa_score(labels1, labels2, sample_weight=weights)
        conf = confusion_matrix(labels1, labels2, sample_weight=weights)

        with open(csv_out, "w", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=aligned_intervals[0].keys())
            writer.writeheader()
            writer.writerows(aligned_intervals)

        return {
            "overall_agreement": overall_acc,
            "cohen_kappa": kappa,
            "confusion_matrix": conf.tolist(),
        }

    def diff_sub_labels(self, label1: str, label2: str) -> str:
        """
        Extracts only the differing sub-labels between two annotators,
        always reporting in canonical order.
        """
        def parse(label_str):
            if not label_str:
                return {}
            if "label:" in label_str:
                label_str = label_str.split("label:", 1)[1]
            label_str = label_str.strip(" []")
            parts = [p.strip() for p in label_str.split(",")]
            parsed = {}
            for p in parts:
                if ": " in p:
                    k, v = p.split(": ", 1)
                    parsed[k.strip()] = v.strip()
            return parsed

        d1, d2 = parse(label1), parse(label2)

        # define fixed order
        category_order = [
            "Customer Movement & Locations",
            "Customer Arm Actions",
            "Interaction With Shopkeeper",
        ]

        diffs = []
        for k in category_order:
            v1, v2 = d1.get(k), d2.get(k)
            if v1 != v2:
                diffs.append(f"{k}: {v1 if v1 else 'NULL_OBJ'} vs {v2 if v2 else 'NULL_OBJ'}")

        return " | ".join(diffs) if diffs else "agree"


    def add_disagreements_to_tmv(self, aligned_intervals, out_path):
        """Write disagreements back into the TMV as new tracks."""
        base_data = self.tmv_data
        tracks = base_data["Timeline"]["Tracks"]

        # use the bag name from the first track for consistency
        bag_name = tracks[0]["Branches"][0]["Name"]

        # Collect disagreements only
        disagreements = [s for s in aligned_intervals if not s["agree"]]

        if not disagreements:
            return None

        new_track_id = 100000 + len(tracks)
        new_track = {
            "Branches": [{
                "Name": bag_name,
                "Spans": []
            }],
            "Color": 0.0,
            "Label": "Disagreements",
            "id": new_track_id,
            "type": "AnnotationTrack",
        }
        for idx, s in enumerate(disagreements):
            new_track["Branches"][0]["Spans"].append({
                "id": 900000 + idx,
                "Start": s["start"],
                "Duration": s["duration"],
                # "Label": f"{s['annotator1']} | {s['annotator2']}",
                "Label": self.diff_sub_labels(s['annotator1'], s['annotator2']),

                "Annotations": [],
            })
        tracks.append(new_track)

        base_data["Timeline"]["Tracks"] = tracks

        with open(out_path, "w") as f:
            yaml.dump(base_data, f, sort_keys=False)

        return os.path.abspath(out_path)


# Example usage
if __name__ == "__main__":
    # agreement = Agreement("overall_test/1_combined.tmv")
    # agreement.extract_spans()
    # aligned = agreement.align_and_compare()
    # metrics = agreement.compute_metrics(aligned, "overall_test/aligned_intervals.csv")
    # print("Metrics:", metrics)

    # out_file = agreement.add_disagreements_to_tmv(aligned, "overall_test/1_with_disagreements.tmv")
    # if out_file:
    #     print("Saved disagreements to:", out_file)
    # else:
    #     print("No disagreements found.")

    # agreement = Agreement("overall_test_sublabels/1_combined.tmv")
    # agreement.extract_spans()
    # aligned = agreement.align_and_compare()
    # metrics = agreement.compute_metrics(aligned, "overall_test_sublabels/aligned_intervals.csv")
    # print("Metrics:", metrics)

    # out_file = agreement.add_disagreements_to_tmv(aligned, "overall_test_sublabels/1_with_disagreements.tmv")
    # if out_file:
    #     print("Saved disagreements to:", out_file)
    # else:
    #     print("No disagreements found.")

    ############################################################## kappa_test_by_hand ##############################################################
    # agreement = Agreement("kappa_test_by_hand/1_combined.tmv")
    # agreement.extract_spans()
    # aligned = agreement.align_and_compare()
    # metrics = agreement.compute_metrics(aligned, "kappa_test_by_hand/aligned_intervals.csv")

    # # save metrics to a CSV
    # with open("kappa_test_by_hand/metrics_report.csv", "w", newline="") as f:
    #     writer = csv.DictWriter(f, fieldnames=metrics.keys())
    #     writer.writeheader()
    #     writer.writerow(metrics)

    # print("Metrics:", metrics)

    # out_file = agreement.add_disagreements_to_tmv(aligned, "kappa_test_by_hand/1_with_disagreements.tmv")
    # if out_file:
    #     print("Saved disagreements to:", out_file)
    # else:
    #     print("No disagreements found.")

    ############################################################## kappa_test_by_hand_global ##############################################################
    # agreement = Agreement("kappa_test_by_hand_global/1/1_combined.tmv")
    # agreement.extract_spans()
    # aligned = agreement.align_and_compare()
    # metrics = agreement.compute_metrics(aligned, "kappa_test_by_hand_global/1/aligned_intervals.csv")

    # # save metrics to a CSV
    # with open("kappa_test_by_hand_global/1/metrics_report.csv", "w", newline="") as f:
    #     writer = csv.DictWriter(f, fieldnames=metrics.keys())
    #     writer.writeheader()
    #     writer.writerow(metrics)
    
    # agreement = Agreement("kappa_test_by_hand_global/2/1_combined.tmv")
    # agreement.extract_spans()
    # aligned = agreement.align_and_compare()
    # metrics = agreement.compute_metrics(aligned, "kappa_test_by_hand_global/2/aligned_intervals.csv")

    # # save metrics to a CSV
    # with open("kappa_test_by_hand_global/2/metrics_report.csv", "w", newline="") as f:
    #     writer = csv.DictWriter(f, fieldnames=metrics.keys())
    #     writer.writeheader()
    #     writer.writerow(metrics)


    ############################################################ AUGUST 20th ANNOTATIONS ##############################################################
    # 2025-03-18_s21_merged_tracked_fix_sorted_combined.tmv
    agreement = Agreement("/home/robovie/Desktop/August_20_Agreement_Analysis/2025-03-18_s21_merged_tracked_fix_sorted_combined.tmv")
    agreement.extract_spans()
    aligned = agreement.align_and_compare()
    metrics = agreement.compute_metrics(aligned, "/home/robovie/Desktop/August_20_Agreement_Analysis/2025-03-18_s21_merged_tracked_fix_sorted_combined_aligned_intervals.csv")

    # save metrics to a CSV
    with open("/home/robovie/Desktop/August_20_Agreement_Analysis/2025-03-18_s21_merged_tracked_fix_sorted_combined_metrics_report.csv", "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=metrics.keys())
        writer.writeheader()
        writer.writerow(metrics)
    
    out_file = agreement.add_disagreements_to_tmv(aligned, "/home/robovie/Desktop/August_20_Agreement_Analysis/2025-03-18_s21_merged_tracked_fix_sorted_combined_with_disagreements.tmv")
    if out_file:
        print("Saved disagreements to:", out_file)
    else:
        print("No disagreements found.")

    # 2025-04-17_s2_merged_tracked_fix_sorted_combined.tmv
    agreement = Agreement("/home/robovie/Desktop/August_20_Agreement_Analysis/2025-04-17_s2_merged_tracked_fix_sorted_combined.tmv")
    agreement.extract_spans()
    aligned = agreement.align_and_compare()
    metrics = agreement.compute_metrics(aligned, "/home/robovie/Desktop/August_20_Agreement_Analysis/2025-04-17_s2_merged_tracked_fix_sorted_combined_aligned_intervals.csv")

    # save metrics to a CSV
    with open("/home/robovie/Desktop/August_20_Agreement_Analysis/2025-04-17_s2_merged_tracked_fix_sorted_combined_metrics_report.csv", "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=metrics.keys())
        writer.writeheader()
        writer.writerow(metrics)
    
    out_file = agreement.add_disagreements_to_tmv(aligned, "/home/robovie/Desktop/August_20_Agreement_Analysis/2025-04-17_s2_merged_tracked_fix_sorted_combined_with_disagreements.tmv")
    if out_file:
        print("Saved disagreements to:", out_file)
    else:
        print("No disagreements found.")

    # 2025-04-27_s44_merged_tracked_fix_sorted_combined.tmv
    agreement = Agreement("/home/robovie/Desktop/August_20_Agreement_Analysis/2025-04-27_s44_merged_tracked_fix_sorted_combined.tmv")
    agreement.extract_spans()
    aligned = agreement.align_and_compare()
    metrics = agreement.compute_metrics(aligned, "/home/robovie/Desktop/August_20_Agreement_Analysis/2025-04-27_s44_merged_tracked_fix_sorted_combined_aligned_intervals.csv")

    # save metrics to a CSV
    with open("/home/robovie/Desktop/August_20_Agreement_Analysis/2025-04-27_s44_merged_tracked_fix_sorted_combined_metrics_report.csv", "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=metrics.keys())
        writer.writeheader()
        writer.writerow(metrics)

    out_file = agreement.add_disagreements_to_tmv(aligned, "/home/robovie/Desktop/August_20_Agreement_Analysis/2025-04-27_s44_merged_tracked_fix_sorted_combined_with_disagreements.tmv")
    if out_file:
        print("Saved disagreements to:", out_file)
    else:
        print("No disagreements found.")

    # 2025-04-30_s4_merged_tracked_fix_sorted_combined.tmv
    agreement = Agreement("/home/robovie/Desktop/August_20_Agreement_Analysis/2025-04-30_s4_merged_tracked_fix_sorted_combined.tmv")
    agreement.extract_spans()
    aligned = agreement.align_and_compare()
    metrics = agreement.compute_metrics(aligned, "/home/robovie/Desktop/August_20_Agreement_Analysis/2025-04-30_s4_merged_tracked_fix_sorted_combined_aligned_intervals.csv")

    # save metrics to a CSV
    with open("/home/robovie/Desktop/August_20_Agreement_Analysis/2025-04-30_s4_merged_tracked_fix_sorted_combined_metrics_report.csv", "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=metrics.keys())
        writer.writeheader()
        writer.writerow(metrics)
    
    out_file = agreement.add_disagreements_to_tmv(aligned, "/home/robovie/Desktop/August_20_Agreement_Analysis/2025-04-30_s4_merged_tracked_fix_sorted_combined_with_disagreements.tmv")
    if out_file:
        print("Saved disagreements to:", out_file)
    else:
        print("No disagreements found.")
    