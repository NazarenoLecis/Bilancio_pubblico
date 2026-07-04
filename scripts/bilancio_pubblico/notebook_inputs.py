"""Helper per rendere i notebook autosufficienti.

I notebook usano questo modulo nella prima cella. Se l'export di sezione non
esiste, il modulo richiama la pipeline Python del repo e materializza l'input
necessario.
"""

import json
from pathlib import Path

import pandas as pd

from bilancio_pubblico.pipeline import run
from bilancio_pubblico.section_export import SECTION_EXPORT_DIR, materialize_section_outputs
from bilancio_pubblico.section_schema import normalize_section_ids
from bilancio_pubblico.utils import BASE_DIR, SOURCE_DATA_JSON_PATH


DEFAULT_REFRESH = False
DEFAULT_FORCE_DOWNLOAD = False


def section_json_path(section_id):
    return SECTION_EXPORT_DIR / f"{section_id}.json"


def ensure_section_input(section_id, refresh=DEFAULT_REFRESH, force=DEFAULT_FORCE_DOWNLOAD):
    """Garantisce che il JSON della sezione sia disponibile.

    Regole operative:
    - se il file `sections/<section_id>.json` esiste e `force=False`, non fa nulla;
    - se manca il file di sezione ma esiste `source-data.json`, materializza solo la sezione;
    - se manca anche `source-data.json`, esegue la pipeline completa e poi materializza la sezione;
    - se `force=True`, riesegue la pipeline completa.
    """
    selected = normalize_section_ids([section_id])
    normalized_id = selected[0]
    section_path = section_json_path(normalized_id)

    if section_path.exists() and not force:
        return section_path

    if SOURCE_DATA_JSON_PATH.exists() and not force:
        materialize_section_outputs(sections=[normalized_id])
        return section_path

    run(refresh)
    materialize_section_outputs(sections=[normalized_id])
    return section_path


def ensure_all_inputs(refresh=DEFAULT_REFRESH, force=DEFAULT_FORCE_DOWNLOAD):
    """Garantisce che tutti e quattro i JSON di sezione siano disponibili."""
    section_ids = normalize_section_ids("all")
    paths = [section_json_path(section_id) for section_id in section_ids]
    if all(path.exists() for path in paths) and not force:
        return paths
    if SOURCE_DATA_JSON_PATH.exists() and not force:
        materialize_section_outputs(sections="all")
        return paths
    run(refresh)
    materialize_section_outputs(sections="all")
    return paths


def load_section(section_id, refresh=DEFAULT_REFRESH, force=DEFAULT_FORCE_DOWNLOAD):
    """Carica una sezione, creando l'input quando necessario."""
    selected = normalize_section_ids([section_id])
    normalized_id = selected[0]
    section_path = ensure_section_input(normalized_id, refresh=refresh, force=force)
    payload = json.loads(section_path.read_text(encoding="utf-8"))
    return payload.get("section", payload)


def load_source_payload(refresh=DEFAULT_REFRESH, force=DEFAULT_FORCE_DOWNLOAD):
    if force or not SOURCE_DATA_JSON_PATH.exists():
        run(refresh)
        materialize_section_outputs(sections="all")
    return json.loads(SOURCE_DATA_JSON_PATH.read_text(encoding="utf-8"))


def frame(rows):
    return pd.DataFrame(rows or [])


def print_input_status(section_id):
    path = section_json_path(section_id)
    source_exists = SOURCE_DATA_JSON_PATH.exists()
    section_exists = path.exists()
    return {
        "project_root": str(BASE_DIR),
        "source_json": str(SOURCE_DATA_JSON_PATH),
        "source_exists": source_exists,
        "section_json": str(path),
        "section_exists": section_exists,
    }
