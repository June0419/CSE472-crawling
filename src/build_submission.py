"""Build a Gradescope-ready ZIP containing only required, safe project files."""

from __future__ import annotations

import zipfile
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[1]
OUTPUT_PATH = ROOT_DIR / "output" / "submission" / "CSE472_Project1_Submission.zip"

INCLUDE_PATTERNS = [
    "README.md",
    "requirements.txt",
    ".env.example",
    "data/posts.json",
    "data/users.json",
    "src/*.py",
    "output/networks/*.gexf",
    "output/networks/*.graphml",
    "output/networks/*.csv",
    "output/networks/network_summary.txt",
    "output/gephi/*.gephi",
    "output/gephi/*.gexf",
    "output/gephi/*.png",
    "output/analysis/*.csv",
    "output/analysis/*.md",
    "output/analysis/*.txt",
    "output/figures/*.png",
    "output/pdf/CSE472_Project1_Report.pdf",
]


def _selected_files() -> list[Path]:
    files: set[Path] = set()
    for pattern in INCLUDE_PATTERNS:
        files.update(path for path in ROOT_DIR.glob(pattern) if path.is_file())
    return sorted(files, key=lambda path: path.relative_to(ROOT_DIR).as_posix())


def main() -> None:
    files = _selected_files()
    required = {
        ROOT_DIR / "data" / "posts.json",
        ROOT_DIR / "data" / "users.json",
        ROOT_DIR / "output" / "pdf" / "CSE472_Project1_Report.pdf",
    }
    missing = required - set(files)
    if missing:
        raise FileNotFoundError(f"Required submission files are missing: {sorted(missing)}")
    if any(path.name == ".env" for path in files):
        raise RuntimeError("Refusing to package the private .env file.")
    if any(path.suffix.lower() == ".java" for path in files):
        raise RuntimeError("Submission must contain Python source only, not Java source.")

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    manifest = [path.relative_to(ROOT_DIR).as_posix() for path in files]
    with zipfile.ZipFile(OUTPUT_PATH, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for path, relative in zip(files, manifest):
            archive.write(path, relative)
        archive.writestr(
            "submission_manifest.txt",
            "CSE 472 Project I submission contents\n"
            + "=" * 40
            + "\n"
            + "\n".join(manifest)
            + "\n",
        )
    print(f"Packaged {len(files)} files into {OUTPUT_PATH}")


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        raise SystemExit(f"Submission packaging failed: {exc}") from exc
