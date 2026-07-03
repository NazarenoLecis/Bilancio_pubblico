# Bilancio pubblico

Progetto Python per generare grafici social-format sulla situazione del fisco italiano, con fonte e dicitura `Elaborazione di Nazareno Lecis`.

L'obiettivo è avere un flusso semplice, ripetibile e leggibile:

- dati da fonti ufficiali,
- grafici su entrate, spesa, patrimonio, successioni e bilanci regionali,
- output tracciabili con manifest grafici e JSON dashboard.

## Come avviare

```bash
python3 scripts/genera_grafici.py
```

Il file [scripts/genera_grafici.py](/home/nazareno/PycharmProjects/Fisco/scripts/genera_grafici.py) espone un'unica variabile di controllo:

```python
FORZA_AGGIORNAMENTO = False
```

- `False`: usa la cache locale in `data/raw` quando disponibile.
- `True`: forza la riscarica da tutte le fonti.

## Cosa succede quando parte lo script

1. prepara le cartelle e lo stile grafico;
2. pulisce gli output precedenti dichiarati;
3. carica i dati (MEF, Eurostat, OCSE, dichiarazioni, OpenBDAP/RGS);
4. genera i grafici in ordine: entrate, spesa, patrimonio, bilanci regionali, confronti internazionali;
5. scrive:
   - [grafici/manifest.csv](/home/nazareno/PycharmProjects/Fisco/grafici/manifest.csv)
   - [data/export/bilancio-pubblico/source-data.json](/home/nazareno/PycharmProjects/Fisco/data/export/bilancio-pubblico/source-data.json) con i dati completi normalizzati.
   - [data/export/bilancio-pubblico/download-manifest.json](/home/nazareno/PycharmProjects/Fisco/data/export/bilancio-pubblico/download-manifest.json) con i file da passare alla pipeline dati.

## Output prodotti

- `grafici/`: immagini PNG verticali.
- `grafici/manifest.csv`: elenco dei file prodotti, fonte e data aggiornamento.
- `data/raw/`: cache dati (API esterne).
- `data/export/bilancio-pubblico/source-data.json`: payload completo/intermedio per la pipeline dati.
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

## Struttura del codice

- [scripts/genera_grafici.py](/home/nazareno/PycharmProjects/Fisco/scripts/genera_grafici.py): entrypoint semplice, senza parser.
- [scripts/bilancio_pubblico/utils.py](/home/nazareno/PycharmProjects/Fisco/scripts/bilancio_pubblico/utils.py): costanti, path, download/caching, stile grafico, utilità salvataggio e formatter.
- [scripts/bilancio_pubblico/data_extraction.py](/home/nazareno/PycharmProjects/Fisco/scripts/bilancio_pubblico/data_extraction.py): tutte le funzioni di estrazione e normalizzazione dati nazionali e internazionali.
- [scripts/bilancio_pubblico/regional_budgets.py](/home/nazareno/PycharmProjects/Fisco/scripts/bilancio_pubblico/regional_budgets.py): ricerca OpenBDAP/RGS via CKAN, caricamento bilanci regionali, normalizzazione e append al JSON dashboard.
- [scripts/bilancio_pubblico/pipeline.py](/home/nazareno/PycharmProjects/Fisco/scripts/bilancio_pubblico/pipeline.py): orchestrazione completa del flusso.
- [scripts/bilancio_pubblico/chart_generation/italia_entrate.py](/home/nazareno/PycharmProjects/Fisco/scripts/bilancio_pubblico/chart_generation/italia_entrate.py): grafici Italia su entrate, IRPEF, redditi, successioni.
- [scripts/bilancio_pubblico/chart_generation/italia_uscite.py](/home/nazareno/PycharmProjects/Fisco/scripts/bilancio_pubblico/chart_generation/italia_uscite.py): grafici Italia su spesa per funzione e spesa totale.
- [scripts/bilancio_pubblico/chart_generation/italia_patrimonio.py](/home/nazareno/PycharmProjects/Fisco/scripts/bilancio_pubblico/chart_generation/italia_patrimonio.py): grafici patrimonio familiare.
- [scripts/bilancio_pubblico/chart_generation/regioni.py](/home/nazareno/PycharmProjects/Fisco/scripts/bilancio_pubblico/chart_generation/regioni.py): grafici su spese, entrate, missioni e saldi regionali.
- [scripts/bilancio_pubblico/chart_generation/confronti_europa.py](/home/nazareno/PycharmProjects/Fisco/scripts/bilancio_pubblico/chart_generation/confronti_europa.py): confronti UE e paesi europei.
- [scripts/bilancio_pubblico/chart_generation/confronti_oecd.py](/home/nazareno/PycharmProjects/Fisco/scripts/bilancio_pubblico/chart_generation/confronti_oecd.py): confronti con OCSE.

## Sezione bilanci regionali

La sezione regionale usa OpenBDAP/RGS come fonte. Il codice interroga il catalogo CKAN di OpenBDAP con query su bilanci degli enti della PA, Regioni e consuntivi. Quando trova una risorsa tabellare leggibile, normalizza i dati per Regione, anno e voce contabile.

I grafici regionali generati, quando la fonte restituisce dati leggibili, sono:

- `21_bilanci_regionali_spesa_per_regione.png`
- `22_bilanci_regionali_entrate_per_regione.png`
- `23_bilanci_regionali_spesa_per_missione.png`
- `24_bilanci_regionali_saldi_per_regione.png`

Nel JSON dashboard viene aggiunta la chiave `regional_budgets`, con:

- metadati dei dataset OpenBDAP caricati;
- eventuali errori di ricerca o lettura;
- spese per Regione;
- spese per missione;
- entrate per Regione;
- entrate per titolo;
- saldi per Regione;
- dettaglio dei saldi.

## Fonti dati

- MEF - API Entrate tributarie erariali e territoriali.
- MEF - Statistiche delle dichiarazioni 2025 (anno d'imposta 2024).
- MEF - Appendici statistiche alle entrate tributarie, dicembre 2025.
- Eurostat `gov_10a_taxag` (pressione fiscale/contributiva).
- Eurostat `gov_10a_exp` (spesa pubblica COFOG).
- Banca d'Italia, conti distributivi sulla ricchezza delle famiglie.
- OCSE, Revenue Statistics 2025.
- OCSE, National Accounts Statistics.
- OpenBDAP/RGS, bilanci degli enti della PA, dati di consuntivo regionali.

## Note metodologiche

- Le mappe di entrate e i focus su tipologie fiscali seguono scelte comunicative per chiarezza visiva.
- Le somme sono coerenti con le unità riportate nelle singole fonti; i confronti internazionali usano la medesima logica usata nei grafici.
- I valori OCSE usano il dato disponibile 2024 e includono la voce “Media OCSE” calcolata sui paesi con dato completo.
- La sezione regionale dipende dalla disponibilità dei file tabellari nel catalogo OpenBDAP. Se il catalogo cambia nome alle risorse, la pipeline registra l'errore nel JSON senza bloccare i grafici nazionali.
- I grafici includono sempre fonte e firma in basso.

## Le variabili/concetti utili

- `FORZA_AGGIORNAMENTO` in `scripts/genera_grafici.py`.
- `SOURCE_*` in `scripts/bilancio_pubblico/utils.py`: testo sorgenti da riportare in calce.
- `SOURCE_OPENBDAP_REGIONI` in `scripts/bilancio_pubblico/regional_budgets.py`: fonte della sezione regionale.
- `GENERATED_FILES` in `scripts/bilancio_pubblico/utils.py`: elenco file gestiti nella pulizia e output.
- `PEER_GEOS` e `OECD_MEMBER_AREAS`: elenchi paesi per i confronti.

## Note operative

Il percorso base del progetto è:

```text
/home/nazareno/PycharmProjects/Fisco
```
