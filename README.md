# Bilancio pubblico

Progetto Python per generare grafici social-format sulla situazione del fisco italiano, con fonte e dicitura "Elaborazione di Nazareno Lecis".

## Come generare

```bash
python3 scripts/genera_grafici.py
```

Per riscaricare i dati invece di usare la cache locale:

```bash
python3 scripts/genera_grafici.py --refresh
```

Output:

- `grafici/`: PNG finali in formato verticale.
- `grafici/manifest.csv`: elenco dei grafici e fonti.
- `data/raw/`: cache dei dati scaricati.
- `analisi_claims.md`: sintesi dei claim verificati e cautele.

## Struttura

- `scripts/genera_grafici.py`: comando principale, con opzione `--refresh`.
- `scripts/fisco/utils.py`: percorsi, costanti, cache HTTP, stile grafico, salvataggio PNG e manifest.
- `scripts/fisco/data_extraction.py`: estrazione e normalizzazione dati MEF, Eurostat, OCSE e dichiarazioni.
- `scripts/fisco/pipeline.py`: ordine di esecuzione, manifest e analisi dei claim.
- `scripts/fisco/chart_generation/italia_entrate.py`: grafici solo Italia su entrate, IRPEF, redditi, salari/capitali e successioni.
- `scripts/fisco/chart_generation/italia_uscite.py`: grafici solo Italia su spesa per funzione e spesa totale.
- `scripts/fisco/chart_generation/italia_patrimonio.py`: grafici solo Italia sul patrimonio.
- `scripts/fisco/chart_generation/confronti_europa.py`: confronti Eurostat con UE e paesi europei.
- `scripts/fisco/chart_generation/confronti_oecd.py`: confronti OCSE per entrate, spesa e successioni.

## Fonti dati

- MEF - Dipartimento delle Finanze, API Entrate tributarie erariali.
- MEF - Dipartimento delle Finanze, API Entrate tributarie territoriali.
- MEF - Dipartimento delle Finanze, Appendici statistiche al bollettino entrate tributarie, dicembre 2025.
- MEF - Dipartimento delle Finanze, Statistiche dichiarazioni 2025, anno d'imposta 2024.
- Eurostat `gov_10a_taxag`, pressione fiscale e contributiva.
- Eurostat `gov_10a_exp`, spesa pubblica per funzione COFOG.
- Banca d'Italia, Conti distributivi sulla ricchezza delle famiglie italiane.
- OCSE, Revenue Statistics 2025, Comparative tax revenues.
- OCSE, National Accounts Statistics, Table 1100 COFOG e Table 0101 GDP.

## Note metodologiche

- Il grafico sulle imposte principali combina entrate erariali e territoriali per includere IRAP.
- Il focus sui tipi di entrate aggrega gruppi comunicativi delle principali voci fiscali: redditi delle persone, consumi, imprese, immobili/patrimonio e capitale finanziario. La voce immobili/patrimonio include anche successioni e donazioni. Non e' una riclassificazione ufficiale esaustiva dell'intero gettito tributario.
- Il focus sul patrimonio usa le statistiche Banca d'Italia aggiornate al quarto trimestre 2025.
- Il focus sulle successioni usa la tabella 22 delle appendici statistiche MEF di dicembre 2025.
- I confronti OCSE usano dati 2024 dove disponibili. Per i grafici "media OCSE" viene calcolata una media semplice dei paesi OCSE con dato disponibile; le categorie OCSE armonizzate non coincidono sempre con le singole imposte nazionali MEF.
