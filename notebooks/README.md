# Notebook sezioni bilancio pubblico

I notebook leggono gli export generati dal repo e servono per controllare i dati, visualizzare grafici e aggiungere contesto analitico.

La prima cella di ogni notebook richiama il codice Python del repo tramite:

```python
from bilancio_pubblico.notebook_inputs import load_section
```

Se il file JSON della sezione non esiste, il notebook genera automaticamente l'input:

1. se esiste `source-data.json`, materializza solo la sezione richiesta;
2. se manca anche `source-data.json`, esegue la pipeline completa e poi materializza la sezione;
3. se `FORCE_DOWNLOAD = True`, riesegue la pipeline anche quando l'input esiste.

I flag iniziali sono:

```python
REFRESH = False
FORCE_DOWNLOAD = False
```

Per forzare il refresh delle fonti dal notebook, imposta entrambi in modo coerente nella prima cella:

```python
REFRESH = True
FORCE_DOWNLOAD = True
```

Puoi comunque generare tutti gli input prima di aprire i notebook:

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

Se quei file non esistono, li creano richiamando il codice Python del repo.
