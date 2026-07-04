# Bilancio pubblico

Progetto Python per generare grafici social-format sulla situazione del fisco italiano, con fonte e dicitura `Elaborazione di Nazareno Lecis`.

L'obiettivo è avere un flusso semplice, ripetibile e leggibile:

- dati da fonti ufficiali,
- grafici su entrate, spesa, patrimonio, successioni e bilanci regionali,
- serie consultabili in valori correnti, reali, pro capite e in quota di PIL quando disponibili,
- output tracciabili con manifest grafici, JSON completo, JSON per sezione e notebook di controllo.

## Come avviare

```bash
python3 scripts/genera_grafici.py
```

Il file `scripts/genera_grafici.py` espone un'unica variabile di controllo:

```python
FORZA_AGGIORNAMENTO = False
```

- `False`: usa la cache locale in `data/raw` quando disponibile.
- `True`: forza la riscarica da tutte le fonti.

## Run delle quattro sezioni

Lo schema operativo del repo è basato su quattro sezioni:

1. `italia`
2. `confronto_europeo`
3. `confronto_ocse`
4. `regioni`

Per runnarle tutte:

```bash
python3 scripts/run_sections.py --sections all
```

Per runnarne solo alcune:

```bash
python3 scripts/run_sections.py --sections italia,regioni
```

Per riscrivere solo gli export di sezione da un `source-data.json` già presente:

```bash
python3 scripts/run_sections.py --sections all --skip-pipeline
```

Per forzare il refresh da tutte le fonti:

```bash
python3 scripts/run_sections.py --sections all --refresh
```

La pipeline dati viene eseguita una volta. Le sezioni vengono materializzate dopo la generazione del JSON sorgente.

## Cosa succede quando parte lo script

1. prepara le cartelle e lo stile grafico;
2. pulisce gli output precedenti dichiarati;
3. carica i dati (MEF, Eurostat, OCSE, dichiarazioni, OpenBDAP/RGS);
4. genera i grafici in ordine: entrate, spesa, patrimonio, bilanci regionali, confronti internazionali;
5. arricchisce le serie di spesa e i bilanci regionali con denominatori utili;
6. scrive:
   - `grafici/manifest.csv`;
   - `data/export/bilancio-pubblico/source-data.json` con i dati completi normalizzati;
   - `data/export/bilancio-pubblico/sections/*.json` con i quattro export di sezione;
   - `data/export/bilancio-pubblico/sections/download-manifest.json` con il manifest delle sezioni;
   - `data/export/bilancio-pubblico/download-manifest.json` con i file da passare alla pipeline dati.

## Output prodotti

- `grafici/`: immagini PNG verticali.
- `grafici/manifest.csv`: elenco dei file prodotti, fonte e data aggiornamento.
- `data/raw/`: cache dati (API esterne).
- `data/export/bilancio-pubblico/source-data.json`: payload completo/intermedio per la pipeline dati.
- `data/export/bilancio-pubblico/sections/italia.json`: export sezione Italia.
- `data/export/bilancio-pubblico/sections/confronto_europeo.json`: export sezione confronto europeo.
- `data/export/bilancio-pubblico/sections/confronto_ocse.json`: export sezione confronto OCSE.
- `data/export/bilancio-pubblico/sections/regioni.json`: export sezione Regioni.
- `data/export/bilancio-pubblico/download-manifest.json`: elenco file pronti per `nazarenolecis-data-pipeline`.

Il formato pubblico per la dashboard (`bilancio-pubblico/dashboard.json` su R2) viene creato nel repository `nazarenolecis-data-pipeline`.

Per un export completo da linea comando:

```bash
python3 scripts/download_all.py
```

Per forzare il refresh da tutte le API:

```bash
python3 scripts/download_all.py --refresh
```

## Notebook

I notebook sono in `notebooks/`:

- `01_italia.ipynb`
- `02_confronto_europeo.ipynb`
- `03_confronto_ocse.ipynb`
- `04_regioni.ipynb`

La prima cella di ogni notebook richiama il codice Python del repo tramite `bilancio_pubblico.notebook_inputs`.

Il comportamento è questo:

1. se il JSON della sezione esiste, il notebook lo legge;
2. se manca il JSON della sezione ma esiste `source-data.json`, il notebook materializza solo quella sezione;
3. se manca anche `source-data.json`, il notebook esegue la pipeline completa e poi materializza la sezione;
4. se `FORCE_DOWNLOAD = True`, il notebook riesegue la pipeline anche quando l'input esiste.

I flag nella prima cella sono:

```python
REFRESH = False
FORCE_DOWNLOAD = False
```

Per forzare il refresh dal notebook:

```python
REFRESH = True
FORCE_DOWNLOAD = True
```

## Struttura del codice

- `scripts/genera_grafici.py`: entrypoint semplice, senza parser.
- `scripts/run_sections.py`: CLI per materializzare tutte o alcune sezioni.
- `scripts/download_all.py`: export completo e manifest dei file scaricabili.
- `scripts/bilancio_pubblico/section_schema.py`: schema operativo delle quattro sezioni.
- `scripts/bilancio_pubblico/section_export.py`: costruzione di `section_index`, `sections`, JSON separati e manifest sezioni.
- `scripts/bilancio_pubblico/notebook_inputs.py`: helper usato dai notebook per generare o caricare gli input.
- `scripts/bilancio_pubblico/utils.py`: costanti, path, download/caching, stile grafico, utilità salvataggio e formatter.
- `scripts/bilancio_pubblico/data_extraction.py`: funzioni di estrazione e normalizzazione dati nazionali e internazionali.
- `scripts/bilancio_pubblico/regional_budgets.py`: caricamento OpenBDAP/FET dei bilanci regionali, normalizzazione e append al JSON.
- `scripts/bilancio_pubblico/regional_normalization.py`: denominatori regionali e normalizzazioni pro capite/kmq.
- `scripts/bilancio_pubblico/spending_adjustments.py`: popolazione, HICP, metriche di spesa reali e pro capite, riferimento SIOPE.
- `scripts/bilancio_pubblico/pipeline.py`: orchestrazione completa del flusso.
- `scripts/bilancio_pubblico/chart_generation/italia_entrate.py`: grafici Italia su entrate, IRPEF, redditi, successioni.
- `scripts/bilancio_pubblico/chart_generation/italia_uscite.py`: grafici Italia su spesa per funzione e spesa totale.
- `scripts/bilancio_pubblico/chart_generation/italia_patrimonio.py`: grafici patrimonio familiare.
- `scripts/bilancio_pubblico/chart_generation/regioni.py`: grafici su spese, entrate, missioni e saldi regionali.
- `scripts/bilancio_pubblico/chart_generation/confronti_europa.py`: confronti UE e paesi europei.
- `scripts/bilancio_pubblico/chart_generation/confronti_oecd.py`: confronti con OCSE.

## Sezione bilanci regionali

La sezione regionale usa OpenBDAP/RGS come fonte. Il codice usa gli endpoint pubblici FET della pagina Finanza degli Enti Territoriali e normalizza i dati per Regione, anno e voce contabile.

I grafici regionali generati, quando la fonte restituisce dati leggibili, sono:

- `21_bilanci_regionali_spesa_per_regione.png`
- `22_bilanci_regionali_entrate_per_regione.png`
- `23_bilanci_regionali_spesa_per_missione.png`
- `24_bilanci_regionali_saldi_per_regione.png`

Nel JSON viene aggiunta la chiave `regional_budgets`, con:

- metadati dei dataset OpenBDAP caricati;
- eventuali errori di ricerca o lettura;
- spese per Regione;
- spese per missione;
- spese per titolo;
- entrate per Regione;
- entrate per titolo;
- saldi per Regione;
- dettaglio dei saldi.

Nella sezione `sections.regioni` vengono aggiunti anche aggregati derivati: entrate finali, entrate correnti, componenti per titolo, spese finali e saldo finale.

## Metriche reali e pro capite

Le serie di spesa COFOG mantengono il valore nominale originale in `mld` e aggiungono campi derivati:

- `pil`: valore in percentuale del PIL, già scaricato da Eurostat `gov_10a_exp`;
- `population`: popolazione residente usata come denominatore;
- `euro_per_capita`: euro correnti per abitante;
- `mld_2024`: miliardi di euro a prezzi dell'ultimo anno comune disponibile, costruiti con HICP all-items;
- `euro_2024_per_capita`: euro reali per abitante.

La chiave JSON `spending_metric_options` descrive le metriche che la dashboard può mostrare. La fonte primaria della classificazione per funzione resta Eurostat COFOG. Popolazione e HICP servono solo per normalizzare la stessa serie.

## SIOPE

SIOPE viene registrato nel JSON come fonte di riferimento per i flussi di cassa degli enti pubblici. È distinto da Eurostat COFOG: SIOPE misura incassi, pagamenti e disponibilità liquide; Eurostat COFOG misura la spesa delle amministrazioni pubbliche secondo la contabilità nazionale.

Nel JSON la chiave `siope_reference` conserva URL, perimetro e nota metodologica. L'integrazione diretta dei CSV SIOPE può essere aggiunta in una fase successiva, per una sezione specifica sui flussi di cassa degli enti territoriali.

## Fonti dati

- MEF - API Entrate tributarie erariali e territoriali.
- MEF - Statistiche delle dichiarazioni 2025 (anno d'imposta 2024).
- MEF - Appendici statistiche alle entrate tributarie, dicembre 2025.
- Eurostat `gov_10a_taxag` (pressione fiscale/contributiva).
- Eurostat `gov_10a_exp` (spesa pubblica COFOG).
- Eurostat `demo_pjan` (popolazione residente).
- Eurostat `prc_hicp_aind` (HICP all-items, indice annuale).
- Banca d'Italia, conti distributivi sulla ricchezza delle famiglie.
- OCSE, Revenue Statistics 2025.
- OCSE, National Accounts Statistics.
- OpenBDAP/RGS, bilanci degli enti della PA, dati di consuntivo regionali.
- SIOPE - Banca d'Italia/RGS, incassi e pagamenti degli enti pubblici.

## Note metodologiche

- Le mappe di entrate e i focus su tipologie fiscali seguono scelte comunicative per chiarezza visiva.
- Le somme sono coerenti con le unità riportate nelle singole fonti; i confronti internazionali usano la medesima logica usata nei grafici.
- I valori OCSE usano il dato disponibile 2024 e includono la voce “Media OCSE” calcolata sui paesi con dato completo.
- La sezione regionale dipende dalla disponibilità dei file tabellari OpenBDAP/FET. Se la fonte cambia struttura, la pipeline registra l'errore nel JSON senza bloccare i grafici nazionali.
- Le serie reali sono deflazionate con HICP all-items. Per analisi tecniche su spesa pubblica reale si può valutare anche un deflatore di contabilità nazionale.
- I grafici includono sempre fonte e firma in basso.

## Le variabili/concetti utili

- `FORZA_AGGIORNAMENTO` in `scripts/genera_grafici.py`.
- `SECTION_SCHEMA` in `scripts/bilancio_pubblico/section_schema.py`.
- `SOURCE_*` in `scripts/bilancio_pubblico/utils.py`: testo sorgenti da riportare in calce.
- `SOURCE_OPENBDAP_REGIONI` in `scripts/bilancio_pubblico/regional_budgets.py`: fonte della sezione regionale.
- `SPENDING_METRIC_OPTIONS` in `scripts/bilancio_pubblico/spending_adjustments.py`: metriche disponibili per la dashboard.
- `SIOPE_REFERENCE` in `scripts/bilancio_pubblico/spending_adjustments.py`: metadati SIOPE e nota metodologica.
- `GENERATED_FILES` in `scripts/bilancio_pubblico/utils.py`: elenco file gestiti nella pulizia e output.
- `PEER_GEOS` e `OECD_MEMBER_AREAS`: elenchi paesi per i confronti.

## Note operative

Il percorso base del progetto è:

```text
/home/nazareno/PycharmProjects/Fisco
```
