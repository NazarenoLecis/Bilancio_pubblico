# Export a sezioni

Il repo continua a produrre il JSON storico in `data/export/bilancio-pubblico/source-data.json`.

In aggiunta, dopo la pipeline viene aggiunta una vista logica a quattro sezioni:

1. `italia`
2. `confronto_europeo`
3. `confronto_ocse`
4. `regioni`

Questa estensione non modifica la dashboard. Serve a rendere piu' leggibile l'export dati e a preparare eventuali viste future senza rompere le chiavi gia' usate.

## Chiavi aggiunte

`section_index` contiene l'indice ordinato delle sezioni, con etichetta, descrizione, perimetro e fonti principali.

`sections` contiene i payload raggruppati per sezione.

Le chiavi legacy restano al primo livello del JSON.

## Sezione Italia

La sezione `italia` raggruppa KPI, entrate, spese, distribuzione IRPEF, patrimonio, successioni e serie storiche nazionali.

Le fonti principali sono MEF, Eurostat, Banca d'Italia e UPB.

## Sezione confronto europeo

La sezione `confronto_europeo` raggruppa i confronti Eurostat.

Contiene pressione fiscale, spesa pubblica, spesa sociale e dettaglio COFOG per paese.

## Sezione confronto OCSE

La sezione `confronto_ocse` raggruppa il payload OCSE gia' prodotto dal repo.

Contiene entrate per categoria, spese per funzione, pressione fiscale totale, spesa pubblica totale e imposte su successioni e donazioni.

## Sezione regioni

La sezione `regioni` raggruppa i dati OpenBDAP/FET su Regioni e province autonome.

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

Crea anche `saldo_finale`, calcolato come entrate finali meno spese finali. Le spese finali sono i titoli 1-3. Debito, anticipazioni e partite di giro restano disponibili come voci separate.

Gli aggregati regionali mantengono, quando disponibili, euro pro capite ed euro per kmq.

## Esecuzione

Le due entrypoint standard aggiungono automaticamente la vista a sezioni:

```bash
python3 scripts/genera_grafici.py
python3 scripts/download_all.py
```

Il modulo puo' anche essere eseguito da codice:

```python
from bilancio_pubblico.section_export import append_sectioned_export_to_source_json

append_sectioned_export_to_source_json()
```
