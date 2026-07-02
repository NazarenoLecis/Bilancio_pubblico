"""Rigenera tutti i dati del progetto in un solo pass.

Esegue la pipeline completa (grafici + cache + export JSON normalizzato)
e scrive un manifest dei file pronti per essere raccolti dalla pipeline dati.
"""

import json
from datetime import datetime, timezone

from bilancio_pubblico.pipeline import run
from bilancio_pubblico.utils import SOURCE_DATA_JSON_PATH


EXPORT_DIR = SOURCE_DATA_JSON_PATH.parent
MANIFEST_PATH = EXPORT_DIR / "download-manifest.json"


def _build_file_entry(path, role, endpoint_hint=None):
    return {
        "path": str(path),
        "name": path.name,
        "role": role,
        "endpoint_hint": endpoint_hint,
    }


def build_download_manifest():
    entries = []
    if SOURCE_DATA_JSON_PATH.exists():
        entries.append(
            _build_file_entry(
                SOURCE_DATA_JSON_PATH,
                role="source_json",
            )
        )
    return sorted(entries, key=lambda item: (item["role"], item["name"]))


def write_download_manifest():
    entries = build_download_manifest()
    payload = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "total_files": len(entries),
        "files": entries,
    }
    MANIFEST_PATH.parent.mkdir(parents=True, exist_ok=True)
    MANIFEST_PATH.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return str(MANIFEST_PATH)


def download_all(refresh=False):
    run(refresh)
    manifest_path = write_download_manifest()
    return manifest_path


def main():
    from argparse import ArgumentParser

    parser = ArgumentParser(description="Scarica/regenera tutti i dati del progetto Bilancio pubblico.")
    parser.add_argument(
        "--refresh",
        action="store_true",
        help="Forza il refresh da API per ogni fonte dati.",
    )
    args = parser.parse_args()
    manifest_path = download_all(refresh=args.refresh)
    print(f"Manifest di upload scritto in: {manifest_path}")


if __name__ == "__main__":
    main()
