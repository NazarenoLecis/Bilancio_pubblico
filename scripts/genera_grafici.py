import argparse

from fisco.pipeline import run


def main():
    parser = argparse.ArgumentParser(description="Genera grafici sul fisco italiano con fonti ufficiali.")
    parser.add_argument("--refresh", action="store_true", help="Riscarica i dati invece di usare la cache locale.")
    args = parser.parse_args()
    run(args.refresh)


if __name__ == "__main__":
    main()
