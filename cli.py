import argparse
import sys

from docparser.core import process_batch_or_file


def main():
    parser = argparse.ArgumentParser(description="CLI Client per DocParser Library")

    # Aggiorniamo l'help per dire che accetta anche cartelle
    parser.add_argument("input_path", help="Path del file o della cartella da processare")
    parser.add_argument("--rapidocr", action="store_true", help="Usa RapidOCR invece di EasyOCR")
    parser.add_argument("--openai", action="store_true", help="Usa OpenAI per report extra")
    parser.add_argument("--output", default="output", help="Cartella di destinazione")

    args = parser.parse_args()

    try:
        # Chiamiamo la funzione che gestisce sia file singolo che cartella
        results = process_batch_or_file(
            input_path=args.input_path,
            output_root=args.output,
            use_rapidocr=args.rapidocr,
            use_openai=args.openai
        )

        if results:
            print(f"\n[DONE] Completati con successo {len(results)} documenti.")
            sys.exit(0)
        else:
            print("\n[WARNING] Nessun documento processato correttamente.")
            sys.exit(1)

    except KeyboardInterrupt:
        print("\n[STOP] Elaborazione interrotta dall'utente.")
        sys.exit(1)
    except Exception as e:
        print(f"\n[FATAL ERROR] Errore imprevisto nel client: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()