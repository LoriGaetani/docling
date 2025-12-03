
from typing import List, Dict, Any, Union
from pathlib import Path

import langchain_text_splitters
from langchain_text_splitters import MarkdownHeaderTextSplitter
from transformers import AutoTokenizer

#TODO devo passare tutto il testo al chunker e non un pezzo alla volta
def generate_markdown_chunks(doc, output_path: Union[str, Path]):
    print("Exporting to Markdown and chunking...")

    # 1. Esportazione "Magica" in Markdown
    # Questo risolve il problema delle tabelle mancanti e delle ripetizioni.
    full_markdown_text = doc.export_to_markdown()

    # 2. Setup Tokenizer
    tokenizer = AutoTokenizer.from_pretrained("sentence-transformers/all-MiniLM-L6-v2")

    # 3. Setup Splitter specifico per Markdown
    # LangChain ha uno splitter che capisce la sintassi Markdown (capisce dove finisce una tabella o un header)
    text_splitter = RecursiveCharacterTextSplitter.from_huggingface_tokenizer(
        tokenizer,
        chunk_size=2048,
        chunk_overlap=200,
        separators=["\n\n", "\n", " ", ""],  # Standard separators
        # Opzionale: se volessi usare from_language per splittare sugli header markdown
        # ma con i tokenizers di HF a volte è meglio rimanere sul semplice character splitter
    )

    # 4. Creazione del Documento Unico
    # Nota: Con l'export markdown globale, perdiamo la mappatura precisa "frase -> numero pagina",
    # ma guadagniamo enormemente in qualità del testo.
    doc_object = Document(page_content=full_markdown_text)

    # 5. Splitting
    chunks = text_splitter.split_documents([doc_object])

    # 6. Preparazione Output
    chunks_data = []
    for i, chunk in enumerate(chunks):
        chunks_data.append({
            "id": i,
            "text": chunk.page_content,
            "metadata": {
                "source": "docling_markdown_export",
                "chunk_size_chars": len(chunk.page_content)
            }
        })

    # Salvataggio
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(chunks_data, f, ensure_ascii=False, indent=2)

    print(f"Generati {len(chunks_data)} chunk in Markdown di alta qualità.")


from typing import Union, List, Dict, Any
from pathlib import Path
import json
from docling.chunking import HybridChunker


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