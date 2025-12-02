import json
from typing import List, Dict, Any

from langchain_text_splitters import MarkdownHeaderTextSplitter


def chunk_markdown(md_text: str, chunk_output_path: str = "chunks.json") -> List[Dict[str, Any]]:
    """
    Usa MarkdownHeaderTextSplitter per dividere il markdown
    in chunk per heading (#, ##, ###) e salva il risultato in JSON.

    Ritorna anche la lista di chunk, così puoi testarla facilmente
    senza leggere/scrivere file quando fai unit test.
    """
    headers_to_split_on = [
        ("#", "H1"),
        ("##", "H2"),
        ("###", "H3"),
    ]

    splitter = MarkdownHeaderTextSplitter(
        headers_to_split_on=headers_to_split_on,
        strip_headers=False,  # mantieni il titolo nel contenuto
    )

    docs = splitter.split_text(md_text)

    chunks: List[Dict[str, Any]] = []
    for i, doc in enumerate(docs):
        chunks.append(
            {
                "id": i,
                "content": doc.page_content,
                "metadata": doc.metadata,
            }
        )

    # scrittura su file (sovrascrive comunque)
    with open(chunk_output_path, "w", encoding="utf-8") as f:
        json.dump(chunks, f, ensure_ascii=False, indent=2)

    print(f"Successfully saved {len(chunks)} chunks to {chunk_output_path}")
    return chunks
