# openai_ocr_report.py

import base64
import os
from mimetypes import guess_type
from pathlib import Path
from typing import List, Optional, Tuple, Any

from openai import OpenAI


# ---------------------------------------------------------
#  Helper: convertire un’immagine locale in data URL base64
# ---------------------------------------------------------
def _image_to_data_url(image_path: str) -> str:
    mime_type, _ = guess_type(image_path)
    if mime_type is None:
        mime_type = "application/octet-stream"

    with open(image_path, "rb") as image_file:
        b64 = base64.b64encode(image_file.read()).decode("utf-8")

    return f"data:{mime_type};base64,{b64}"


# ---------------------------------------------------------
#  OCR OpenAI — Versione Ottimizzata per Accuratezza
# ---------------------------------------------------------
def openai_ocr_text_from_image(
        image_path: str,
        model: str = "gpt-4o",  # CONSIGLIO: Usa gpt-4o per massima precisione, gpt-4o-mini per velocità
        instructions: Optional[str] = None,
) -> Tuple[List[str], str, str, Any]:
    # Prompt "Pedante" di default se non fornito
    if instructions is None:
        instructions = (
            """
                You are an OCR engine specializing in verbatim transcription.
                Your goal is absolute fidelity to the visual text, not grammatical accuracy.
                
                Strict rules:
                1. Transcribe the text EXACTLY as it appears in the image.
                2. DO NOT correct typos, grammar, or syntax errors (e.g., if it says 'architectural,' do not write 'architectural').
                3. DO NOT expand abbreviations.
                4. Respect the structure of lines and lists.
                5. If a word is ambiguous or cut off, write what you see, don't guess.
                6. Do not add comments, preambles, or salutations. Return ONLY the transcribed text.
                """
        )

    if not os.getenv("OPENAI_API_KEY"):
        raise RuntimeError("OPENAI_API_KEY non impostata nell'ambiente.")

    client = OpenAI()
    data_url = _image_to_data_url(image_path)

    print("\n================ OPENAI OCR REQUEST ================")
    print(f"MODEL : {model}")
    print(f"PROMPT: {instructions}")
    print("====================================================\n")

    try:
        # Sintassi standard OpenAI v1.x
        response = client.chat.completions.create(
            model=model,
            messages=[
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": instructions},
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": data_url,
                                "detail": "high"  # Importante: forza alta risoluzione per leggere testi piccoli
                            },
                        },
                    ],
                }
            ],
            temperature=0.0,  # FONDAMENTALE: Azzera la creatività per evitare allucinazioni
            max_tokens=4096,
        )
    except Exception as e:
        print(f"API Error: {e}")
        raise e

    # ----------- ESTRAZIONE TESTO OCR -----------------
    # In chat completions, il contenuto è in choices[0].message.content
    text = response.choices[0].message.content

    # Pulizia eventuale di backticks markdown se il modello li aggiunge
    if text.startswith("```"):
        lines_temp = text.splitlines()
        # Rimuove la prima riga se è ``` o ```text
        if lines_temp[0].startswith("```"):
            lines_temp = lines_temp[1:]
        # Rimuove l'ultima riga se è ```
        if lines_temp and lines_temp[-1].strip() == "```":
            lines_temp = lines_temp[:-1]
        text = "\n".join(lines_temp)

    raw_lines = [l for l in
                 text.splitlines()]  # Manteniamo anche le righe vuote per la formattazione? Se no: if l.strip()
    lines = [f"{i + 1:03d}. {l}" for i, l in enumerate(raw_lines)]

    # ----------- TOKENS -------------------------------
    token_info = None
    if response.usage:
        token_info = {
            "input_tokens": response.usage.prompt_tokens,
            "output_tokens": response.usage.completion_tokens,
            "total_tokens": response.usage.total_tokens,
        }

    print("\n================ OPENAI OCR RESPONSE ================")
    print(f"MODEL        : {model}")
    print(f"OCR LINES    : {len(lines)}")
    print(f"TOKENS       : {token_info}")
    print("====================================================\n")

    return lines, instructions, model, token_info


# ---------------------------------------------------------
#  Costruzione markdown finale
# ---------------------------------------------------------
def build_openai_ocr_markdown(
        image_path: str,
        model: str = "gpt-4o",
) -> str:
    try:
        lines, prompt, used_model, token_info = openai_ocr_text_from_image(
            image_path,
            model=model,
        )
    except Exception as e:
        print(f"Error in OpenAI OCR: {e}")
        return (
            f"## OpenAI OCR ({model})\n"
            f"```text\nError: {e}\n```\n"
        )

    md = []
    md.append(f"## OpenAI OCR ({used_model})\n")
    md.append("### Configurazione")
    md.append(f"- **Temperature**: 0.0 (Deterministic)")
    md.append(f"- **Detail**: High")

    md.append("\n### Prompt usato")
    md.append("```text")
    md.append(prompt)
    md.append("```\n")

    md.append("### Token usati")
    md.append("```json")
    md.append(str(token_info))
    md.append("```\n")

    md.append("### Testo rilevato")
    md.append("```text")
    md.extend(lines)
    md.append("```\n")

    # Stampa a console per debug rapido
    print("\n--- OCR TEXT ---")
    for line in lines:
        print(line)

    return "\n".join(md)


# ---------------------------------------------------------
#  Entry point
# ---------------------------------------------------------
def run_openai_ocr_report_if_needed(
        file_path: str,
        ocr_enabled: bool,
        docling_ocr_engine_name: str,
        run_dir: Path,
        model: str = "gpt-4o",
) -> None:
    ext = Path(file_path).suffix.lower()
    image_exts = {".png", ".jpg", ".jpeg", ".tif", ".tiff", ".bmp", ".webp"}

    ocr_md_path = run_dir / "openai_ocr.md"

    if ext in image_exts and ocr_enabled:
        print(f"Running OpenAI OCR ({model}) on {file_path}...")
        body = build_openai_ocr_markdown(file_path, model=model)

        header = (
            f"# OCR report (OpenAI)\n\n"
            f"> Docling OCR engine: **{docling_ocr_engine_name}** (enabled: {ocr_enabled})\n\n"
            f"> External OCR engine: **openai:{model}**\n\n"
            f"File: `{file_path}`\n\n"
        )

        with open(ocr_md_path, "w", encoding="utf-8") as f:
            f.write(header + body)

        print(f"Saved OpenAI OCR markdown to {ocr_md_path}")

    else:
        print("OpenAI OCR skipped (file not an image or OCR disabled).")