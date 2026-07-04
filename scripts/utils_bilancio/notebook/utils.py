"""Utilità condivise per i workflow dei notebook di questo repository."""

from pathlib import Path
import subprocess
import sys


def discover_repo_root():
    """Trova la radice del repository Bilancio pubblico dalla directory corrente."""
    current = Path.cwd().resolve()
    for candidate in [current, *current.parents]:
        if (candidate / "scripts" / "utils_bilancio").is_dir():
            return candidate

    raise ModuleNotFoundError(
        "Impossibile trovare la radice del repository. Avvia il notebook dalla cartella del progetto Bilancio_pubblico."
    )


def section_path(repo_root, section_id):
    return (
        repo_root
        / "data"
        / "export"
        / "bilancio-pubblico"
        / "sections"
        / f"{section_id}.json"
    )


def ensure_section_loaded(repo_root, section_id, refresh=False, force_download=False):
    """Esegue la pipeline della sezione se necessario e restituisce il path del file JSON."""
    sections_file = section_path(repo_root, section_id)

    if force_download or refresh or not sections_file.exists():
        command = [
            sys.executable,
            str(repo_root / "scripts" / "run_sections.py"),
            "--sections",
            section_id,
        ]
        if refresh or force_download:
            command.append("--refresh")

        print("Eseguo:", " ".join(command))
        result = subprocess.run(command, cwd=repo_root, check=False)
        if result.returncode != 0:
            raise RuntimeError(
                f"Impossibile aggiornare la sezione {section_id}: codice {result.returncode}"
            )
    else:
        print(f"Cache presente: {sections_file}")

    return sections_file


def setup_notebook_section(
    section_id,
    refresh=False,
    force_download=False,
    include_source_payload=False,
):
    """Prepara l'ambiente del notebook e carica i dati della sezione."""
    repo_root = discover_repo_root()
    scripts_dir = repo_root / "scripts"
    scripts_path = str(scripts_dir.resolve())

    if scripts_path not in sys.path:
        sys.path.insert(0, scripts_path)

    from utils_bilancio.notebook.inputs import frame, load_section, print_input_status

    ensure_section_loaded(
        repo_root,
        section_id,
        refresh=refresh,
        force_download=force_download,
    )

    section = load_section(section_id, refresh=refresh, force=force_download)
    status = print_input_status(section_id)

    payload = {
        "repo_root": str(repo_root),
        "section": section,
        "status": status,
        "frame": frame,
        "section_file": str(section_path(repo_root, section_id)),
    }

    if include_source_payload:
        from utils_bilancio.notebook.inputs import load_source_payload

        payload["source_payload"] = load_source_payload(
            refresh=refresh,
            force=force_download,
        )

    return payload
