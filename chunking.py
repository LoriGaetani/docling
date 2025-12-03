
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

    In output genera JSON con:
      - prev: porzione iniziale del chunk usata come overlap col precedente
      - focus: parte centrale (senza overlap) da usare per l'estrazione
      - next: porzione finale del chunk usata come overlap col successivo
    """
    print("Starting smart chunking with LangChain/Transformers (focus/prev/next)...")

    # Parametri di chunking in token
    chunk_size_tokens = 2048
    chunk_overlap_tokens = 200

    # 1. Setup Tokenizer
    try:
        tokenizer = AutoTokenizer.from_pretrained("sentence-transformers/all-MiniLM-L6-v2")
    except Exception as e:
        print(f"Error loading tokenizer: {e}")
        return

    # 2. Setup Splitter specifico per Markdown
    text_splitter = RecursiveCharacterTextSplitter.from_huggingface_tokenizer(
        tokenizer,
        chunk_size=chunk_size_tokens,
        chunk_overlap=chunk_overlap_tokens,
        separators=["\n\n", "\n", " ", ""],
    )

    # 3. Creazione del Documento LangChain basato sulla stringa pulita
    doc_object = Document(page_content=markdown_text)

    # 4. Splitting
    chunks = text_splitter.split_documents([doc_object])

    # 5. Preparazione Output JSON con prev/focus/next
    chunks_data: List[Dict[str, Any]] = []

    for i, chunk in enumerate(chunks):
        full_text = chunk.page_content or ""
        full_text = full_text.strip()

        if not full_text:
            continue

        # Tokenizziamo il testo del chunk
        encoding = tokenizer(
            full_text,
            add_special_tokens=False,
            return_attention_mask=False,
            return_token_type_ids=False,
        )
        tokens = encoding["input_ids"]
        num_tokens = len(tokens)

        # Caso edge: chunk troppo corto per applicare overlap in modo sensato
        # In questo caso tutto il testo va in "focus" e prev/next restano vuoti
        if num_tokens <= 2 * chunk_overlap_tokens:
            prev_tokens = []
            next_tokens = []
            focus_tokens = tokens
        else:
            # Chunk "interni": hanno overlap sia davanti che dietro
            if i == 0:
                # Primo chunk: non esiste realmente un "prev" (niente overlap verso prima)
                prev_tokens = []
                focus_tokens = tokens[:-chunk_overlap_tokens]
                next_tokens = tokens[-chunk_overlap_tokens:]
            elif i == len(chunks) - 1:
                # Ultimo chunk: non esiste realmente un "next"
                prev_tokens = tokens[:chunk_overlap_tokens]
                focus_tokens = tokens[chunk_overlap_tokens:]
                next_tokens = []
            else:
                # Chunk in mezzo: overlap davanti (prev) e dietro (next)
                prev_tokens = tokens[:chunk_overlap_tokens]
                focus_tokens = tokens[chunk_overlap_tokens:-chunk_overlap_tokens]
                next_tokens = tokens[-chunk_overlap_tokens:]

        # Decodifica delle varie parti
        def decode_tokens(tok_list: List[int]) -> str:
            if not tok_list:
                return ""
            return tokenizer.decode(tok_list, skip_special_tokens=True).strip()

        prev_text = decode_tokens(prev_tokens)
        focus_text = decode_tokens(focus_tokens)
        next_text = decode_tokens(next_tokens)

        # Safety: se per qualche motivo la focus è vuota, ripieghiamo sull'intero testo
        if not focus_text:
            focus_text = full_text
            prev_text = ""
            next_text = ""

        chunk_record: Dict[str, Any] = {
            "id": i,
            "prev": prev_text,
            "focus": focus_text,
            "next": next_text,
            "metadata": {
                "source": source_name,
                # Grandezza del chunk originale (non splittato in prev/focus/next)
                "chunk_size_chars": len(full_text),
            },
        }

        chunks_data.append(chunk_record)

    # 6. Salvataggio su file
    out_path_obj = Path(output_path)
    out_path_obj.parent.mkdir(parents=True, exist_ok=True)

    with open(out_path_obj, "w", encoding="utf-8") as f:
        json.dump(chunks_data, f, ensure_ascii=False, indent=2)

    print(f"Generati {len(chunks_data)} chunk (con prev/focus/next) salvati in {output_path}")


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