# Analisi claim fiscali

Sintesi operativa dei claim del report e dei grafici prodotti.

| Claim | Stato | Dato usato | Output |
|---|---|---:|---|
| Italia gia' ad alta pressione fiscale | Supportato | Italia 42,5% nel 2024; UE 40,3%; area euro 40,7% | 09_pressione_fiscale_confronto_ue_2024.png |
| Italia con spesa pubblica elevata | Supportato, ma aggiornare il numero del dossier | Eurostat API al 10 giugno 2026: Italia 50,4% del PIL nel 2024; UE 49,1% | 10_spesa_pubblica_confronto_ue_2024.png |
| La protezione sociale pesa molto sul bilancio | Supportato | Italia 21,3% del PIL nel 2024; UE 19,6% | 11_protezione_sociale_confronto_ue_2024.png |
| Le entrate principali arrivano soprattutto da redditi delle persone, consumi e imprese | Supportato come aggregazione delle principali voci MEF, non come totale esaustivo | MEF entrate erariali e territoriali 2025 | 12_tipi_entrate_tributarie_2025.png |
| La spesa totale cresce in valore nominale e resta molto elevata in rapporto al PIL | Supportato | Serie Eurostat spesa totale S13, 1995-2024 | 13_spesa_totale_italia_1995_2024.png |
| Il patrimonio familiare e' molto concentrato | Supportato | Banca d'Italia DWA IV trim. 2025: top 10% al 60,6%, meta' meno abbiente al 7,2% | 14_distribuzione_patrimonio_famiglie_2025.png |
| Le successioni rendono poco rispetto al totale delle entrate | Supportato | MEF Appendici statistiche dicembre 2025: 1.081 milioni, +6,8% sul 2024 | 15_successioni_donazioni_2025.png |
| Nel confronto OCSE l'Italia e' sopra media per pressione fiscale | Supportato | OCSE Revenue Statistics 2024: Italia 42,8%; media OCSE 34,2% | 18_ocse_pressione_fiscale_totale_2024.png |
| Le successioni in Italia pesano meno della media OCSE | Supportato | OCSE Revenue Statistics 2024: Italia 0,05%; media OCSE 0,15% | 19_ocse_successioni_donazioni_2024.png |
| Nel confronto OCSE la spesa pubblica italiana e' sopra media | Supportato | OCSE National Accounts 2024: Italia 50,4%; media OCSE 44,8% | 20_ocse_spesa_totale_2024.png |

Nota: il dossier indicava la spesa pubblica italiana al 54,9% del PIL nel 2023. La chiamata Eurostat usata qui, eseguita il 10 giugno 2026 su `gov_10a_exp`, restituisce 53,6% per il 2023 e 50,4% per il 2024. Per pubblicazioni esterne conviene citare il dato aggiornato e la data di estrazione.

Nota entrate: il grafico 12 aggrega gruppi comunicativi delle principali voci fiscali. Non e' una riclassificazione ufficiale esaustiva e non deve essere letto come somma dell'intero gettito tributario.

Nota OCSE: i confronti OCSE usano la media semplice dei paesi membri con dato disponibile nel 2024. Le categorie OCSE sono armonizzate e non coincidono sempre con le singole imposte nazionali MEF.
