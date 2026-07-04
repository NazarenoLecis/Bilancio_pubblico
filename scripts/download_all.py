"""Rigenera tutti i dati del progetto in un solo pass.

Esegue la pipeline completa (grafici + cache + export JSON normalizzato),
materializza le quattro sezioni e scrive un manifest dei file pronti per essere
raccolti dalla pipeline dati.
"""

import json
from datetime import datetime, timezone
import sys

from utils_bilancio.generali.section_export import (
    SECTION_EXPORT_DIR,
    SECTION_MANIFEST_PATH,
    materialize_section_outputs,
)
from utils_bilancio.generali.pipeline import run
from utils_bilancio.generali.section_schema import SECTION_BY_ID, list_section_ids
from utils_bilancio.generali.costanti import SOURCE_DATA_JSON_PATH


EXPORT_DIR = SOURCE_DATA_JSON_PATH.parent
MANIFEST_PATH = EXPORT_DIR / "download-manifest.json"


def build_file_entry(path, role, endpoint_hint=None, section_id=None):
    entry = {
        "path": str(path),
        "name": path.name,
        "role": role,
        "endpoint_hint": endpoint_hint,
    }
    if section_id:
        entry["section_id"] = section_id
        entry["section_label"] = SECTION_BY_ID[section_id]["label"]
        entry["notebook"] = SECTION_BY_ID[section_id]["notebook"]
    return entry


def build_download_manifest():
    entries = []
    if SOURCE_DATA_JSON_PATH.exists():
        entries.append(build_file_entry(SOURCE_DATA_JSON_PATH, role="source_json"))
    for section_id in list_section_ids():
        path = SECTION_EXPORT_DIR / f"{section_id}.json"
        if path.exists():
            entries.append(build_file_entry(path, role="section_json", section_id=section_id))
    if SECTION_MANIFEST_PATH.exists():
        entries.append(build_file_entry(SECTION_MANIFEST_PATH, role="section_manifest"))
    return sorted(entries, key=lambda item: (item["role"], item.get("section_id") or "", item["name"]))


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
    materialize_section_outputs(sections="all")
    manifest_path = write_download_manifest()
    return manifest_path


def parse_command_line(arguments):
    refresh = False
    for argument in arguments:
        if argument == "--refresh":
            refresh = True
        else:
            raise ValueError(f"Argomento non riconosciuto: {argument}")
    return {"refresh": refresh}


def main():
    try:
        options = parse_command_line(sys.argv[1:])
    except ValueError as exc:
        print(f"Errore: {exc}")
        sys.exit(2)
    manifest_path = download_all(refresh=options["refresh"])
    print(f"Manifest di upload scritto in: {manifest_path}")


if __name__ == "__main__":
    main()
