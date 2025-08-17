import os
import yaml
import copy


# Keep TmvParser and TmvMerger as two separate classes, one uses the other!
#
# - TmvParser: focused only on one file at a time. It loads a .tmv, cleans up differences 
#   (e.g. track labels as strings vs. ints), and provides spans/tracks in a consistent, 
#   structured format. Nothing more.
#
# - TmvMerger: builds on top of TmvParser. It takes multiple parsed files, checks they all 
#   point to the same bag, renames tracks with the {trackid}_{annotator} scheme to preserve 
#   annotator identity, and writes out a single valid .tmv that TAMSVIZ can load.
#
# This split gives us a clear two-layer design: 
#   TmvParser → single-file correctness and normalization
#   TmvMerger → multi-file merging and annotator disambiguation

class TmvParser:
    """
    Parser for TAMSVIZ .tmv annotation files.
    Provides structured access to annotations per track.
    """

    def __init__(self, tmv_path: str):
        self.tmv_path = os.path.abspath(tmv_path)
        self.tmv_data = None
        self.bag_name = None
        self.tracks = {}  # {track_id: [spans]}
        self._load()

    def _load(self):
        """Load YAML and parse tracks, branches, and spans."""
        with open(self.tmv_path, "r") as f:
            self.tmv_data = yaml.safe_load(f)

        timeline = self.tmv_data.get("Timeline", {})
        tracks = timeline.get("Tracks", [])

        for track in tracks:
            track_id = str(track.get("Label"))  # normalize everything to string
            self.tracks[track_id] = []

            for branch in track.get("Branches", []):
                # In bag-linked .tmv, Branch.Name is the bag filename
                if not self.bag_name:
                    branch_name = branch.get("Name", "")
                    if branch_name.endswith(".bag"):
                        self.bag_name = branch_name

                for span in branch.get("Spans", []):
                    start = span.get("Start")
                    duration = span.get("Duration")
                    end = start + duration if start is not None and duration is not None else None
                    label = span.get("Label", "")
                    span_id = span.get("id")

                    self.tracks[track_id].append({
                        "start": start,
                        "duration": duration,
                        "end": end,
                        "label": label,
                        "span_id": span_id
                    })

    def get_bag_name(self):
        """Return the rosbag filename associated with this .tmv (if present)."""
        return self.bag_name

    def get_tracks(self):
        """Return list of track IDs available in this .tmv."""
        return list(self.tracks.keys())

    def get_annotations(self, track_id: str):
        """
        Return all annotations for a given track_id.
        Each annotation is a dict: {start, duration, end, label, span_id}
        """
        return self.tracks.get(str(track_id), [])

    def iter_annotations(self):
        """Iterate over all annotations across tracks."""
        for tid, spans in self.tracks.items():
            for span in spans:
                yield tid, span

    def summary(self):
        """Quick human-readable summary of the .tmv contents."""
        return {
            "tmv_file": self.tmv_path,
            "bag_name": self.bag_name,
            "num_tracks": len(self.tracks),
            "num_annotations": sum(len(s) for s in self.tracks.values()),
            "tracks": {tid: len(spans) for tid, spans in self.tracks.items()}
        }

#######################################################################################################
########################################## Initial tests for parser ###################################
#######################################################################################################

# parser = TmvParser("test_merged.tmv")
# print(parser.summary())

# # Get all annotations for track "1"
# annotations = parser.get_annotations("1")
# for ann in annotations:
#     print(ann["start"], ann["end"], ann["label"])

# annotations = parser.get_annotations("2")
# for ann in annotations:
#     print(ann["start"], ann["end"], ann["label"])

# annotations = parser.get_annotations("3")
# for ann in annotations:
#     print(ann["start"], ann["end"], ann["label"])


class TmvMerger:
    """
    Merge multiple TAMSVIZ .tmv files (from different annotators) into one.
    Uses the first TMV as the base structure, and just injects extra tracks
    from the others (renamed with _annotator suffix).
    """

    def __init__(self, tmv_paths, annotator_ids):
        assert len(tmv_paths) == len(annotator_ids), "Paths and annotator IDs must align."
        self.tmv_paths = [os.path.abspath(p) for p in tmv_paths]
        self.annotator_ids = annotator_ids
        self.parsers = [TmvParser(p) for p in self.tmv_paths]
        self.bag_name = None
        self.merged_data = None

        self._check_bags()
        self._merge()

    def _check_bags(self):
        """Ensure all input .tmv files refer to the same bag."""
        bag_names = {p.get_bag_name() for p in self.parsers}
        if len(bag_names) != 1:
            raise ValueError(f"Mismatched bags across TMVs: {bag_names}")
        self.bag_name = bag_names.pop()

    ##############################################################################
    # def _merge(self):
    #     # Deep copy first TMV
    #     base_data = copy.deepcopy(self.parsers[0].tmv_data)
    #     merged_tracks = []

    #     # Rename base annotator’s tracks too
    #     for track in base_data["Timeline"]["Tracks"]:
    #         new_track = copy.deepcopy(track)
    #         new_track["Label"] = f"{track['Label']}_{self.annotator_ids[0]}"
    #         for branch in new_track.get("Branches", []):
    #             branch["Name"] = self.bag_name
    #         merged_tracks.append(new_track)

    #     # Add tracks from other annotators
    #     for parser, annotator in zip(self.parsers[1:], self.annotator_ids[1:]):
    #         for track in parser.tmv_data["Timeline"]["Tracks"]:
    #             new_track = copy.deepcopy(track)
    #             new_track["Label"] = f"{track['Label']}_{annotator}"
    #             for branch in new_track.get("Branches", []):
    #                 branch["Name"] = self.bag_name
    #             merged_tracks.append(new_track)

    #     base_data["Timeline"]["Tracks"] = merged_tracks
    #     self.merged_data = base_data

    ##############################################################################
    # def _merge(self):
    #     # Deep copy first TMV
    #     base_data = copy.deepcopy(self.parsers[0].tmv_data)
    #     merged_tracks = []

    #     # Rename base annotator’s tracks too
    #     for track in base_data["Timeline"]["Tracks"]:
    #         new_track = copy.deepcopy(track)
    #         new_track["Label"] = f"{track['Label']}_{self.annotator_ids[0]}"
    #         # Keep IDs unchanged for annotator1
    #         for branch in new_track.get("Branches", []):
    #             branch["Name"] = self.bag_name
    #         merged_tracks.append(new_track)

    #     # Add tracks from other annotators with shifted IDs
    #     for idx, (parser, annotator) in enumerate(zip(self.parsers[1:], self.annotator_ids[1:]), start=2):
    #         for track in parser.tmv_data["Timeline"]["Tracks"]:
    #             new_track = copy.deepcopy(track)
    #             new_track["Label"] = f"{track['Label']}_{annotator}"

    #             # Shift IDs far away to avoid collisions
    #             def shift_ids(obj, factor=idx*1000):
    #                 if isinstance(obj, dict):
    #                     if "id" in obj and isinstance(obj["id"], int):
    #                         obj["id"] += factor
    #                     for v in obj.values():
    #                         shift_ids(v, factor)
    #                 elif isinstance(obj, list):
    #                     for v in obj:
    #                         shift_ids(v, factor)

    #             shift_ids(new_track)

    #             for branch in new_track.get("Branches", []):
    #                 branch["Name"] = self.bag_name

    #             merged_tracks.append(new_track)

    #     base_data["Timeline"]["Tracks"] = merged_tracks
    #     self.merged_data = base_data

    ##############################################################################
    def _merge(self):
        # Deep copy first TMV
        base_data = copy.deepcopy(self.parsers[0].tmv_data)
        merged_tracks = []

        # Rename base annotator’s tracks too
        for track in base_data["Timeline"]["Tracks"]:
            new_track = copy.deepcopy(track)
            new_track["Label"] = f"{track['Label']}_{self.annotator_ids[0]}"
            # Keep IDs unchanged for annotator1
            for branch in new_track.get("Branches", []):
                branch["Name"] = self.bag_name
            merged_tracks.append(new_track)

        # Add tracks from other annotators with shifted IDs
        for idx, (parser, annotator) in enumerate(zip(self.parsers[1:], self.annotator_ids[1:]), start=2):
            for track in parser.tmv_data["Timeline"]["Tracks"]:
                new_track = copy.deepcopy(track)
                new_track["Label"] = f"{track['Label']}_{annotator}"

                # Shift IDs far away to avoid collisions
                def shift_ids(obj, factor=idx*1000):
                    if isinstance(obj, dict):
                        if "id" in obj and isinstance(obj["id"], int):
                            obj["id"] += factor
                        for v in obj.values():
                            shift_ids(v, factor)
                    elif isinstance(obj, list):
                        for v in obj:
                            shift_ids(v, factor)

                shift_ids(new_track)

                for branch in new_track.get("Branches", []):
                    branch["Name"] = self.bag_name

                merged_tracks.append(new_track)

        base_data["Timeline"]["Tracks"] = merged_tracks
        self.merged_data = base_data



    def to_dict(self):
        return self.merged_data

    def save(self, out_path):
        with open(out_path, "w") as f:
            yaml.dump(self.merged_data, f, sort_keys=False)
        return os.path.abspath(out_path)

#######################################################################################################
########################################## Initial tests for merger ###################################
#######################################################################################################

# merger = TmvMerger(
#     ["overall_test/1_annotator1.tmv", "overall_test/1_annotator2.tmv"],
#     ["annotator1", "annotator2"]
# )
# print(merger.to_dict())  # see merged structure
# merger.save("overall_test/1_combined.tmv")  # ready to load into TAMSVIZ


merger = TmvMerger(
    ["overall_test_sublabels/1_annotator1.tmv", "overall_test_sublabels/1_annotator2.tmv"],
    ["annotator1", "annotator2"]
)
print(merger.to_dict())  # see merged structure
merger.save("overall_test_sublabels/1_combined.tmv")  # ready to load into TAMSVIZ
