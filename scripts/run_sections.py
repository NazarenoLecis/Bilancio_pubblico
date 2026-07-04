"""Run ed export delle sezioni del progetto Bilancio pubblico.

Uso principale:

python3 scripts/run_sections.py --sections all
python3 scripts/run_sections.py --sections italia,regioni
python3 scripts/run_sections.py --sections all --skip-pipeline

Senza `--skip-pipeline` la pipeline dati viene eseguita una sola volta e poi
vengono materializzate le sezioni richieste. Con `--skip-pipeline` vengono
riscritti solo i file di sezione a partire dal `source-data.json` gia' presente.
"""

from argparse import ArgumentParser
import json

from bilancio_pubblico.pipeline import run
from bilancio_pubblico.section_export import materialize_section_outputs
from bilancio_pubblico.section_schema import list_section_ids, normalize_section_ids


def run_sections(sections="all", refresh=False, skip_pipeline=False):
    selected = normalize_section_ids(sections)
    if not skip_pipeline:
        run(refresh)
    return materialize_section_outputs(sections=selected)


def main():
    parser = ArgumentParser(description="Esegue/materializza una o piu' sezioni del progetto Bilancio pubblico.")
    parser.add_argument(
        "--sections",
        default="all",
        help=(
            "Sezioni da materializzare. Valori: all, "
            + ", ".join(list_section_ids())
            + ". Accetta anche liste separate da virgola."
        ),
    )
    parser.add_argument(
        "--refresh",
        action="store_true",
        help="Forza il refresh delle fonti quando la pipeline viene eseguita.",
    )
    parser.add_argument(
        "--skip-pipeline",
        action="store_true",
        help="Non rigenera i dati. Usa il source-data.json gia' esistente e riscrive solo gli export di sezione.",
    )
    args = parser.parse_args()
    result = run_sections(args.sections, refresh=args.refresh, skip_pipeline=args.skip_pipeline)
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
