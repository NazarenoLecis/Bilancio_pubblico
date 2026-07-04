# Export a sezioni

Il repo continua a produrre il JSON storico in `data/export/bilancio-pubblico/source-data.json`.

In aggiunta, dopo la pipeline viene aggiunta una vista logica a quattro sezioni:

1. `italia`
2. `confronto_europeo`
3. `confronto_ocse`
4. `regioni`

Questa estensione non modifica la dashboard. Serve a rendere piu' leggibile l'export dati, a produrre file separati per sezione e a preparare notebook di controllo.

## Schema centrale

Lo schema operativo e' in:

```text
scripts/utils_bilancio/generali/section_schema.py
```

Contiene:

- `SECTION_SCHEMA`, cioe' le quattro sezioni con id, label, ordine, perimetro, fonti principali, chiavi legacy, file di output e notebook associato;
- `SECTION_IDS`, cioe' l'ordine canonico delle sezioni;
- alias CLI come `all`, `tutte`, `italia`, `europa`, `ocse`, `regioni`;
- aggregati regionali di entrata e spesa.

Il codice operativo e' organizzato in sei aree sotto `scripts/utils_bilancio/`:
`generali`, `notebook`, `italia`, `europa`, `ocse`, `regioni`. Il livello alto
contiene solo cartelle di area: niente wrapper `.py`. Le costanti stanno in
`generali/costanti.py`; `generali/utils.py` contiene solo funzioni. Non vengono
usati file di inizializzazione dei pacchetti.

## Chiavi aggiunte al source JSON

`section_index` contiene l'indice ordinato delle sezioni, con etichetta, descrizione, perimetro e fonti principali.

`sections` contiene i payload raggruppati per sezione.

Le chiavi legacy restano al primo livello del JSON.

## File separati per sezione

Dopo la materializzazione vengono creati quattro file:

```text
data/export/bilancio-pubblico/sections/italia.json
data/export/bilancio-pubblico/sections/confronto_europeo.json
data/export/bilancio-pubblico/sections/confronto_ocse.json
data/export/bilancio-pubblico/sections/regioni.json
```

Viene creato anche il manifest specifico:

```text
data/export/bilancio-pubblico/sections/download-manifest.json
```

Il manifest generale `data/export/bilancio-pubblico/download-manifest.json` include il source JSON, i quattro section JSON e il manifest delle sezioni.

## Run delle sezioni

Per runnare tutto:

```bash
python3 scripts/run_sections.py --sections all
```

Per runnare solo alcune sezioni:

```bash
python3 scripts/run_sections.py --sections italia,regioni
```

Per riscrivere solo gli export di sezione da un `source-data.json` gia' presente:

```bash
python3 scripts/run_sections.py --sections all --skip-pipeline
```

Per forzare il refresh delle fonti:

```bash
python3 scripts/run_sections.py --sections all --refresh
```

La pipeline dati resta eseguita una sola volta. Le sezioni sono materializzate dopo la generazione del JSON sorgente.

## Download

Per produrre source JSON, quattro section JSON e manifest completo:

```bash
python3 scripts/download_all.py
```

Con refresh completo:

```bash
python3 scripts/download_all.py --refresh
```

## Notebook

I notebook sono in:

```text
notebooks/01_italia.ipynb
notebooks/02_confronto_europeo.ipynb
notebooks/03_confronto_ocse.ipynb
notebooks/04_regioni.ipynb
```

Ogni notebook segue la sequenza: spiegazione, cella **Scaricamento dati** con
`scripts/run_sections.py`, cella **Import e caricamento** con
`utils_bilancio.notebook`, poi analisi.

Il comportamento e' questo:

1. se il JSON della sezione esiste, il notebook lo legge;
2. se manca il JSON della sezione ma esiste `source-data.json`, il notebook materializza solo quella sezione;
3. se manca anche `source-data.json`, il notebook esegue la pipeline completa e poi materializza la sezione;
4. se `FORCE_DOWNLOAD = True`, il notebook riesegue la pipeline anche quando l'input esiste.

I flag iniziali sono:

```python
REFRESH = False
FORCE_DOWNLOAD = False
```

Per forzare il refresh dal notebook:

```python
REFRESH = True
FORCE_DOWNLOAD = True
```

## Sezione Italia

La sezione `italia` raggruppa KPI, entrate, spese, distribuzione IRPEF, patrimonio, successioni e serie storiche nazionali.

Le fonti principali sono MEF, Eurostat, Banca d'Italia e UPB.

## Sezione confronto europeo

La sezione `confronto_europeo` raggruppa i confronti Eurostat.

Contiene pressione fiscale, spesa pubblica, spesa sociale e dettaglio COFOG per paese.
Include sia snapshot sull'ultimo anno sia serie storiche in `peer_series` e
`peer_spending_functions_series`.

## Sezione confronto OCSE

La sezione `confronto_ocse` raggruppa il payload OCSE gia' prodotto dal repo.

Contiene entrate per categoria, spese per funzione, pressione fiscale totale, spesa pubblica totale e imposte su successioni e donazioni.

## Sezione regioni

La sezione `regioni` raggruppa i dati OpenBDAP/FET su Regioni e province autonome
e i flussi SIOPE di cassa per territorio.

Oltre alle chiavi gia' presenti in `regional_budgets`, la sezione crea aggregati derivati:

- `entrate_finali`, titoli 1-5
- `entrate_correnti`, titoli 1-3
- `entrate_tributarie_perequative`, titolo 1
- `trasferimenti_correnti`, titolo 2
- `entrate_extratributarie`, titolo 3
- `entrate_conto_capitale`, titolo 4
- `riduzione_attivita_finanziarie`, titolo 5
- `accensione_prestiti`, titolo 6
- `anticipazioni_tesoreria`, titolo 7
- `partite_giro`, titolo 9

Nel blocco `siope` espone anche:

- `by_region_year`
- `by_region_month`
- `by_region_code_year`
- `balances_by_region_year`
- `by_region_compartment_year`
- `entity_counts_by_region`

Per limitare gli anni SIOPE in fase di sviluppo:

```bash
BILANCIO_PUBBLICO_SIOPE_YEARS=2024 python3 scripts/run_sections.py --sections regioni --refresh
BILANCIO_PUBBLICO_SIOPE_YEARS=2019-2024 python3 scripts/run_sections.py --sections regioni --refresh
```

Crea anche `saldo_finale`, calcolato come entrate finali meno spese finali. Le spese finali sono i titoli 1-3. Debito, anticipazioni e partite di giro restano disponibili come voci separate.

Gli aggregati regionali mantengono, quando disponibili, euro pro capite ed euro per kmq.
