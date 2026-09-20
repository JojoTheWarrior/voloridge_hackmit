from __future__ import annotations

import csv
from pathlib import Path

from .model import MissionResult
from warsignal.util import to_jsonable
from warsignal.util_lock import file_lock


ROOT = Path(__file__).resolve().parents[2]


def append_result(result: MissionResult, csv_path=ROOT / "missions" / "results.csv"):
    path = Path(csv_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    row = to_jsonable(result.to_row())
    with path.open("a+", newline="", encoding="utf-8") as handle:
        with file_lock(handle):
            handle.seek(0)
            existing = [{k: v for k, v in r.items() if k is not None} for r in csv.DictReader(handle)]
            fieldnames = list(existing[0]) if existing else []
            for name in row:
                if name not in fieldnames:
                    fieldnames.append(name)
            if not existing and not fieldnames:
                fieldnames = list(row)
            if not existing:
                handle.seek(0)
                handle.truncate()
                writer = csv.DictWriter(handle, fieldnames=fieldnames)
                writer.writeheader()
            elif fieldnames != list(existing[0]):
                handle.seek(0)
                handle.truncate()
                writer = csv.DictWriter(handle, fieldnames=fieldnames)
                writer.writeheader()
                writer.writerows(existing)
            else:
                handle.seek(0, 2)
                writer = csv.DictWriter(handle, fieldnames=fieldnames)
            writer.writerow(row)


def load_results(csv_path=ROOT / "missions" / "results.csv"):
    path = Path(csv_path)
    if not path.exists():
        return []
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))
