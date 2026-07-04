# Notebook sezioni bilancio pubblico

I notebook leggono gli export generati dal repo e servono per controllare i dati, visualizzare grafici e aggiungere contesto analitico.

Prima di aprirli, genera i dati:

```bash
python3 scripts/run_sections.py --sections all
```

Se `source-data.json` esiste gia' e vuoi solo riscrivere i file di sezione:

```bash
python3 scripts/run_sections.py --sections all --skip-pipeline
```

Notebook disponibili:

- `01_italia.ipynb`
- `02_confronto_europeo.ipynb`
- `03_confronto_ocse.ipynb`
- `04_regioni.ipynb`

I notebook cercano prima i file separati in:

```text
data/export/bilancio-pubblico/sections/
```

Se quei file non esistono, leggono la sezione corrispondente da:

```text
data/export/bilancio-pubblico/source-data.json
```
