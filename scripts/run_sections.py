"""Run ed export delle sezioni del progetto Bilancio pubblico.

Uso principale:

python3 scripts/run_sections.py --sections all
python3 scripts/run_sections.py --sections italia,regioni
python3 scripts/run_sections.py --sections all --skip-pipeline

Senza `--skip-pipeline` la pipeline dati viene eseguita una sola volta e poi
vengono materializzate le sezioni richieste. Con `--skip-pipeline` vengono
riscritti solo i file di sezione a partire dal `source-data.json` gia' presente.
"""

import json
import sys

from utils_bilancio.generali.pipeline import run
from utils_bilancio.generali.section_export import materialize_section_outputs
from utils_bilancio.generali.section_schema import list_section_ids, normalize_section_ids


def run_sections(sections="all", refresh=False, skip_pipeline=False):
    selected = normalize_section_ids(sections)
    if not skip_pipeline:
        run(refresh)
    return materialize_section_outputs(sections=selected)


def parse_command_line(arguments):
    options = {
        "sections": "all",
        "refresh": False,
        "skip_pipeline": False,
    }
    index = 0
    while index < len(arguments):
        argument = arguments[index]
        if argument == "--sections":
            if index + 1 >= len(arguments):
                raise ValueError("Manca il valore dopo --sections")
            options["sections"] = arguments[index + 1]
            index += 2
        elif argument.startswith("--sections="):
            options["sections"] = argument.split("=", 1)[1]
            index += 1
        elif argument == "--refresh":
            options["refresh"] = True
            index += 1
        elif argument == "--skip-pipeline":
            options["skip_pipeline"] = True
            index += 1
        else:
            allowed = "all, " + ", ".join(list_section_ids())
            raise ValueError(f"Argomento non riconosciuto: {argument}. Sezioni valide: {allowed}")
    return options


def main():
    try:
        options = parse_command_line(sys.argv[1:])
    except ValueError as exc:
        print(f"Errore: {exc}")
        sys.exit(2)
    result = run_sections(
        options["sections"],
        refresh=options["refresh"],
        skip_pipeline=options["skip_pipeline"],
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
