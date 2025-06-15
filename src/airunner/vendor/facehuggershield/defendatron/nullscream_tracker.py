from airunner.vendor.facehuggershield.shadowlogger.base_tracker import BaseTracker


class NullscreamTracker(BaseTracker):
    def __init__(self):
        self.data = {
            "blocked": {},
            "allowed": {},
        }

    def process_log_record(self, log_entry):
        if "nullscream_allow" in log_entry:
            root_module = log_entry.split(" ")[1].split(".")[0]
            self.data["allowed"].setdefault(
                root_module, {"total": 0, "modules": []}
            )
            self.data["allowed"][root_module]["total"] += 1
            self.data["allowed"][root_module]["modules"].append(
                log_entry.split(" ")[1]
            )
        elif "nullscream_block" in log_entry:
            root_module = log_entry.split(" ")[1].split(".")[0]
            self.data["blocked"].setdefault(
                root_module, {"total": 0, "modules": []}
            )
            self.data["blocked"][root_module]["total"] += 1
            self.data["blocked"][root_module]["modules"].append(
                log_entry.split(" ")[1]
            )
