# Notebook del progetto

In questi notebook trovi analisi pronte per lavorare subito sui quattro JSON
di sezione in `data/export/bilancio-pubblico/sections/`.

I dati completi sono caricati automaticamente: la cella **Scaricamento dati**
usa `scripts/run_sections.py`, mentre la cella **Import e caricamento** usa gli
helper in `utils_bilancio.notebook`.

## Cosa usare, quando usarlo

- `01_italia.ipynb` → quadro nazionale completo (entrate, spese, pressione,
  distribuzioni)
- `02_confronto_europeo.ipynb` → benchmark con UE/Europei, anche COFOG
- `03_confronto_ocse.ipynb` → confronto OCSE con anno/i più recenti e serie
  storiche per categoria
- `04_regioni.ipynb` → rendiconti regionali OpenBDAP e flussi SIOPE con
  normalizzazioni (mld, valori reali, euro per abitante, per km², % PIL regionale)

## Avvio rapido (stessa regola per tutti)

1. Apri il notebook.
2. Spiegazione: la prima parte descrive cosa stai caricando.
3. Esegui la cella **"Scaricamento dati"**:
   - ricalca sezione + fonti quando serve;
   - se i file esistono e `REFRESH`/`FORCE_DOWNLOAD` sono `False`, usa la cache.
4. Esegui la cella **"Import e caricamento"**: inserisce il path del progetto e carica `section`.
5. Leggi i markdown esplicativi delle sezioni.
6. Cambia i parametri che trovi nelle celle di analisi (metrica, anno, top, regioni, metriche disponibili).
7. Esegui le celle grafiche.

Subito dopo la cella di import c'è anche la sezione **Elenco opzioni disponibili**: eseguila prima di impostare `MEASURE`, `METRIC`, `YEAR`, `TOP`, `REGION`, perimetri SIOPE o codici OCSE/COFOG, così hai i valori ammessi dalla tua run (case e caratteri corretti).

Per aggiornare i dati da remoto:

```bash
REFRESH = True
FORCE_DOWNLOAD = True
```

I notebook non richiedono più configurazioni di path avanzate: la cella di
download prova automaticamente il repository corrente e, se necessario,
usa gli helper condivisi in `scripts/utils_bilancio/notebook/`.

## Generazione dati da terminale

```bash
python3 scripts/run_sections.py --sections all
python3 scripts/run_sections.py --sections all --skip-pipeline
python3 scripts/run_sections.py --sections all --refresh
python3 scripts/download_all.py
python3 scripts/download_all.py --refresh
```

## Parametri comuni presenti nei notebook

Nella maggior parte dei notebook trovi blocchi con variabili come:

- `YEAR` → anno da analizzare
- `TOP` → numero elementi da mostrare nelle classifiche
- `METRIC` → metrica da visualizzare
- `COLUMNS` / `MEASURE` / `NORMALIZATION` → scelta della colonna/normalizzazione
- `SIOPE_YEARS` nel notebook Regioni → `""` per tutti gli anni previsti, `"2024"` per test veloce, `"2019-2024"` per intervallo, `"2019,2021,2024"` per anni separati
- `SIOPE_PERIMETER`, `SIOPE_FLOW`, `SIOPE_METRIC`, `SIOPE_CODE` nel notebook Regioni → valori da copiare dalla cella opzioni

Se una cella stampa **"Nessun dato"** significa che quel dataset in quel punto
non era stato popolato nella tua run corrente; prova a rilanciare una
materializzazione completa delle sezioni.

## Nota importante

Le dashboard sono più leggere e dedicate; i notebook sono pensati per analisi
esplorative intense: puoi produrre facilmente molti grafici variando i pochi
parametri sopra e riutilizzando le celle di utilità (helper).

## Sezione Italia

- `01_italia.ipynb`

## Confronto europeo

- `02_confronto_europeo.ipynb`

## Confronto OCSE

- `03_confronto_ocse.ipynb`

## Regioni

- `04_regioni.ipynb`

## Come usare i notebook

In ogni notebook trovi due flag all'inizio:
`REFRESH` e `FORCE_DOWNLOAD`.

Imposta entrambi a `False` per usare la cache locale.
Imposta entrambi a `True` per rigenerare da fonti e aggiornare i CSV.

### Comandi utili
```bash
python3 scripts/run_sections.py --sections all
python3 scripts/run_sections.py --sections all --skip-pipeline
python3 scripts/run_sections.py --sections all --refresh
python3 scripts/download_all.py
python3 scripts/download_all.py --refresh
```
