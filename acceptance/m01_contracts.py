"""Offline M01 acceptance. Run from the repository root without installing it."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import importlib
import json


SAMPLES = Path(__file__).resolve().parents[1] / "samples" / "m01"
EXPECTED_CASES = {
    "01_complete.json": (("complete_valid", True),),
    "02_null_doi.json": (("null_doi_valid", True),),
    "03_invalid_nulls.json": (("chemicals_null", False), ("conclusions_null", False)),
    "04_inconsistent_status.json": (("success_without_methods", False),),
}


def main() -> int:
    try:
        from contracts import validate_record
    except Exception:
        print("FAIL bootstrap: dependency/import check failed; no input data displayed")
        return 1
    passed = failed = 0

    def report(label: str, ok: bool, detail: str) -> None:
        nonlocal passed, failed
        passed += int(ok)
        failed += int(not ok)
        print(f"{'PASS' if ok else 'FAIL'} {label}: {detail}")

    for filename, expected in EXPECTED_CASES.items():
        try:
            data = json.loads((SAMPLES / filename).read_text(encoding="utf-8"))
            cases = data["cases"]
            if type(cases) is not list or len(cases) != len(expected):
                raise ValueError
        except Exception:
            report(filename, False, "fixture could not be loaded; input omitted")
            continue
        for case, (name, should_pass) in zip(cases, expected):
            try:
                if type(case) is not dict or case.get("name") != name:
                    raise ValueError
                result = validate_record(case["record"])
                ok = (result.valid is should_pass and
                      ((result.record is not None and not result.errors) if should_pass
                       else (result.record is None and bool(result.errors))))
                detail = "valid record accepted" if should_pass else "invalid record rejected"
                report(f"{filename}/{name}", ok, detail if ok else "unexpected validation outcome; input omitted")
            except Exception:
                report(f"{filename}/{name}", False, "unexpected error; input omitted")

    expected_classes = ["BaseFetcher", "BaseParser", "BaseExtractor"]
    try:
        data = json.loads((SAMPLES / "05_abstract_classes.json").read_text(encoding="utf-8"))
        if data.get("abstract_classes") != expected_classes:
            raise ValueError
    except Exception:
        report("05_abstract_classes.json", False, "invalid fixture; input omitted")
    else:
        for name in expected_classes:
            try:
                # Import each named class independently before instantiation.
                cls = getattr(importlib.import_module("contracts.interfaces"), name)
            except Exception:
                report(f"05_abstract_classes.json/{name}", False, "class import failed")
                continue
            try:
                cls()
            except TypeError:
                report(f"05_abstract_classes.json/{name}", True, "TypeError raised")
            except Exception:
                report(f"05_abstract_classes.json/{name}", False, "unexpected exception type")
            else:
                report(f"05_abstract_classes.json/{name}", False, "abstract class was instantiated")
    try:
        from contracts import Stage
        data = json.loads((SAMPLES / "06_stage_enum.json").read_text(encoding="utf-8"))
        cases = data["cases"]
        if type(cases) is not list or len(cases) != 1:
            raise ValueError
        case = cases[0]
        if case["name"] != "stage_enum_compatibility":
            raise ValueError
        originals = [
            ["SEARCH", "search"], ["METADATA", "metadata"],
            ["DOWNLOAD", "download"], ["PARSE", "parse"],
            ["EXTRACT", "extract"], ["VALIDATE", "validate"],
            ["EXPORT", "export"],
        ]
        required = [["STORAGE", "storage"], ["EXPORT", "export"]]
        if case["original_members"] != originals or case["required_members"] != required:
            raise ValueError
        for name, value in originals + required:
            if Stage(value) is not getattr(Stage, name):
                raise ValueError
        # Existing names and their order must remain unchanged, including EXPORT.
        if list(Stage.__members__) != [name for name, _ in originals] + ["STORAGE"]:
            raise ValueError
        if case["unknown_value"] != "unknown_stage":
            raise ValueError
        try:
            Stage(case["unknown_value"])
        except ValueError:
            pass
        else:
            raise ValueError
    except Exception:
        report("06_stage_enum.json/stage_enum_compatibility", False,
               "enum compatibility check failed; input omitted")
    else:
        report("06_stage_enum.json/stage_enum_compatibility", True,
               "storage/export constructible; original members preserved; unknown rejected")
    print(f"SUMMARY: {passed} passed, {failed} failed; 6 fixture files")
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
