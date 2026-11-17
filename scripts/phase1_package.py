"""Package the additive Phase 1 source and its public evidence, never PDF caches."""
from pathlib import Path
import hashlib
import json
import zipfile

ROOT = Path(__file__).resolve().parents[1]
SITE = ROOT.parent / "sites/matterlens"
out = SITE / "downloads/phase1-source.zip"
with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as archive:
    for dirname in ("src", "samples/phase1"):
        for path in (ROOT / dirname).rglob("*"):
            if path.is_file() and "__pycache__" not in path.parts and not path.name.endswith(".pyc"):
                archive.write(path, str(path.relative_to(ROOT)))
    for name in ("pyproject.toml", "scripts/phase1_acquire.py", "acceptance/phase1_acquisition.py",
                 "docs/PHASE1.md", "docs/PHASE1_REPORT.md"):
        archive.write(ROOT / name, name)
    archive.write(ROOT / "docs/PHASE1.md", "README.md")
    for name in ("build.mjs", "package.json", "verify-site.mjs", "verify-phase1.mjs", "README.md"):
        archive.write(SITE / name, "website/" + name)
    for dirname in ("web_assets", "worker", "fixtures"):
        for path in (SITE / dirname).rglob("*"):
            if path.is_file():
                archive.write(path, "website/" + str(path.relative_to(SITE)))
    # No deployed identity or credentials in a distributable starter.
    archive.writestr("website/.openai/hosting.json", json.dumps({"d1": None, "r2": "BUCKET"}) + "\n")
    for name in ("PHASE1.md", "phase1-index.xlsx", "phase1-index.csv", "phase1-index.jsonl"):
        archive.write(SITE / "downloads" / name, "website/downloads/" + name)
    archive.writestr("website/.gitignore", "dist/\nwork/\nnode_modules/\n")
    assert archive.testzip() is None
lines = []
for name in ("phase1-source.zip", "phase1-index.xlsx", "phase1-index.csv", "phase1-index.jsonl"):
    path = SITE / "downloads" / name
    lines.append(hashlib.sha256(path.read_bytes()).hexdigest() + "  " + name)
(SITE / "downloads/phase1-SHA256SUMS").write_text("\n".join(lines) + "\n")
print("Phase 1 source ZIP and checksum manifest:", out.stat().st_size, "bytes")
