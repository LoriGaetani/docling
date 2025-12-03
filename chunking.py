
from typing import List, Dict, Any, Union
from pathlib import Path
import json

import langchain_text_splitters
from docling_core.transforms.chunker import HybridChunker
from langchain_text_splitters import MarkdownHeaderTextSplitter
from transformers import AutoTokenizer

#TODO devo passare tutto il testo al chunker e non un pezzo alla volta
def generate_markdown_chunks_from_string(
        markdown_text: str,
        output_path: Union[str, Path],
        source_name: str = "docling_clean_smart"
):
    """
    Esegue il chunking semantico/strutturale su una stringa Markdown già pulita.
    Usa LangChain e HuggingFace Tokenizer per rispettare i limiti di token e la struttura del documento.
    """
    print("Starting smart chunking with LangChain/Transformers...")

    # 1. Setup Tokenizer
    # Usa un modello piccolo e veloce adatto per RAG multilingua/inglese
    try:
        tokenizer = AutoTokenizer.from_pretrained("sentence-transformers/all-MiniLM-L6-v2")
    except Exception as e:
        print(f"Error loading tokenizer: {e}")
        return

    # 2. Setup Splitter specifico per Markdown
    # RecursiveCharacterTextSplitter cerca di splittare prima sui doppi a capo (paragrafi),
    # poi sui singoli a capo, poi spazi, ecc., preservando la struttura.
    text_splitter = RecursiveCharacterTextSplitter.from_huggingface_tokenizer(
        tokenizer,
        chunk_size=2048,  # Dimensione target del chunk in token (o caratteri approssimati dal tokenizer)
        chunk_overlap=200,  # Sovrapposizione per mantenere il contesto tra i chunk
        separators=["\n\n", "\n", " ", ""],
    )

    # 3. Creazione del Documento LangChain basato sulla stringa pulita
    doc_object = Document(page_content=markdown_text)

    # 4. Splitting
    chunks = text_splitter.split_documents([doc_object])

    # 5. Preparazione Output JSON
    chunks_data = []
    for i, chunk in enumerate(chunks):
        chunks_data.append({
            "id": i,
            "text": chunk.page_content,
            "metadata": {
                "source": source_name,
                "chunk_size_chars": len(chunk.page_content)
            }
        })

    # 6. Salvataggio su file
    out_path_obj = Path(output_path)
    out_path_obj.parent.mkdir(parents=True, exist_ok=True)

    with open(out_path_obj, "w", encoding="utf-8") as f:
        json.dump(chunks_data, f, ensure_ascii=False, indent=2)

    print(f"Generati {len(chunks_data)} chunk di alta qualità salvati in {output_path}")


def generate_docling_chunks(doc, output_path: Union[str, Path]):
    """
    Genera chunk strutturati usando HybridChunker di Docling.
    Corretta per gestire l'estrazione dei numeri di pagina dai doc_items.
    """
    print("Generating structural chunks with HybridChunker...")

    #model to count the number of tokens
    tokenizer = AutoTokenizer.from_pretrained("sentence-transformers/all-MiniLM-L6-v2", model_max_length=2048)

    # Configura il chunker
    chunker = HybridChunker(
        tokenizer=tokenizer,
        merge_peers=True
    )

    # Genera i chunk
    chunk_iter = chunker.chunk(doc)

    chunks_data = []
    for i, chunk in enumerate(chunk_iter):

        # 1. Recuperiamo i numeri di pagina dagli elementi originali
        page_numbers = set()

        # I doc_items sono gli oggetti originali (testo, tabelle) inclusi in questo chunk
        if hasattr(chunk.meta, 'doc_items'):
            for item in chunk.meta.doc_items:

                # Estrai numero di pagina dalla provenienza (prov)
                if hasattr(item, 'prov') and item.prov is not None:
                    # In alcune versioni è page_no, in altre page_number.
                    # Docling usa tipicamente item.prov.page_no (1-based)
                    if hasattr(item.prov, 'page_no'):
                        page_numbers.add(item.prov.page_no)


        # 3. Costruzione dell'oggetto
        chunks_data.append({
            "id": i,
            "text": chunk.text,
            "metadata": {
                # Titoli gerarchici
                "headings": chunk.meta.headings if hasattr(chunk.meta, 'headings') and chunk.meta.headings else [],

                # Lista ordinata dei numeri di pagina univoci trovati
                "page_numbers": sorted(list(page_numbers)),
            }
        })

    # Salvataggio
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(chunks_data, f, ensure_ascii=False, indent=2)

    print(f"Successfully saved {len(chunks_data)} structural chunks to {output_path}")



from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter


def generate_langchain_chunks(doc, output_path: Union[str, Path]):
    print("Generating merged chunks...")

    # 1. Setup Tokenizer e Splitter
    tokenizer = AutoTokenizer.from_pretrained("sentence-transformers/all-MiniLM-L6-v2")

    text_splitter = RecursiveCharacterTextSplitter.from_huggingface_tokenizer(
        tokenizer,
        chunk_size=2048,  # Ora questo limite sarà rispettato davvero
        chunk_overlap=200,  # Sovrapposizione utile per non perdere contesto tra un taglio e l'altro
        separators=["\n\n", "\n", " ", ""]
    )

    # 2. FASE CRUCIALE: Aggregazione del testo
    # Invece di creare 68 documenti, ne creiamo UNO solo gigante.
    # Usiamo doc.export_to_markdown() se disponibile, oppure concateniamo manualmente.
    # La concatenazione manuale ci permette di pulire un po' l'input.

    full_text_parts = []

    # Raccogliamo anche tutti i numeri di pagina per averli nei metadata globali
    all_page_numbers = set()

    for item in doc.texts:
        text_clean = item.text.strip()

        # Filtro opzionale: rimuove le intestazioni ripetitive di ogni pagina
        if text_clean in ["Comando Provinciale Carabinieri", "Imperia", "Nucleo Investigativo"]:
            continue

        if text_clean:
            full_text_parts.append(text_clean)

            # Tracking pagine
            if hasattr(item, 'prov') and item.prov is not None:
                if hasattr(item.prov, 'page_no'):
                    all_page_numbers.add(item.prov.page_no)

    # Uniamo tutto con doppi a capo per simulare paragrafi
    full_text_content = "\n\n".join(full_text_parts)

    # Creiamo UN SOLO Documento LangChain
    single_big_doc = Document(
        page_content=full_text_content,
        metadata={
            "source_pages": sorted(list(all_page_numbers))
        }
    )

    # 3. Splitting
    # Ora il splitter riceve un testo enorme e sarà costretto a tagliare solo
    # quando raggiunge i 2048 token.
    final_chunks = text_splitter.split_documents([single_big_doc])

    # 4. Formattazione Output
    chunks_data = []
    for i, split_doc in enumerate(final_chunks):
        chunks_data.append({
            "id": i,
            "text": split_doc.page_content,
            "metadata": {
                # Nota: Splittando un blocco unico, perdiamo la precisione
                # della pagina esatta per ogni chunk. Qui riportiamo il range totale.
                # Per una precisione pagina-per-chunk servirebbe una logica molto più complessa.
                "source_doc_pages": split_doc.metadata.get("source_pages", [])
            }
        })

    # Salvataggio
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(chunks_data, f, ensure_ascii=False, indent=2)

    print(f"Success! Merged text into {len(final_chunks)} chunks (Target size: 2048 tokens).")