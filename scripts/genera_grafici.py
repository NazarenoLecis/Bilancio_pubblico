"""Interfaccia di avvio progetto Bilancio pubblico.

Questo file non contiene logica di elaborazione complessa.
Il suo unico compito è:
- indicare come deve partire la run (`FORZA_AGGIORNAMENTO`)
- chiamare la funzione `run` del pipeline con quel flag

Come si usa:
- apri questo file e imposta FORZA_AGGIORNAMENTO
- esegui: `python3 scripts/genera_grafici.py`

Valori accettati:
- False: usa i dati salvati in `data/raw` quando disponibili.
- True: riscarica i dati da tutte le fonti ufficiali.
"""

from bilancio_pubblico.pipeline import run


FORZA_AGGIORNAMENTO = False


def genera_tutta_la_pubb(forza_aggiornamento=False) -> None:
    """Esegue tutta la pipeline.

    Parametro:
    - forza_aggiornamento (bool):
      False -> usa cache locale, True -> forza il refresh da API.
    """
    run(forza_aggiornamento)


def main():
    # Punto singolo di ingresso: da qui parte la pipeline completa.
    # Cambia solo FORZA_AGGIORNAMENTO in testa se vuoi forzare la risorsa remota.
    genera_tutta_la_pubb(FORZA_AGGIORNAMENTO)


if __name__ == "__main__":
    main()
