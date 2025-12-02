from mimetypes import guess_type
from typing import Union  # se non ce l'hai già
from PIL import Image     # pip install pillow
from pathlib import Path



def is_document_like_image(image_path: Union[str, Path]) -> bool:
    """
    Euristica veloce per capire se un'immagine assomiglia a un documento scansionato.

    True  = probabile foto/pdf di documento (foglio, contratto, ecc.)
    False = probabile foto di persone/paesaggi/oggetti vari
    """
    image_path = Path(image_path)

    try:
        with Image.open(image_path) as img:
            width, height = img.size
    except Exception:
        # Se non riesco a leggerla, non rischio OCR
        return False

    # Immagini troppo piccole: difficilmente un documento leggibile
    min_side = min(width, height)
    if min_side < 600:
        return False

    # Aspect ratio tipo foglio (A4 ≈ 1.41), teniamo un range largo
    aspect_ratio = max(width, height) / min(width, height)
    if not (0.7 <= aspect_ratio <= 1.9):
        # molto panoramica o molto stretta → più probabile foto
        return False

    return True


def should_enable_ocr_for_file(file_path: Union[str, Path]) -> bool:
    """
    Decide se ha senso abilitare l'OCR per questo file *a livello Docling*.

    - PDF      -> True  (Docling poi decide pagina per pagina dove usare OCR)
    - Immagine -> True  solo se l'immagine sembra un documento
    - Altro    -> False
    """
    file_path = Path(file_path)
    mime, _ = guess_type(file_path.name)

    # PDF: abilitiamo sempre OCR, Docling userà il text layer se c'è
    if mime == "application/pdf":
        return True

    # Immagini: usiamo l'euristica document-like
    if mime and mime.startswith("image/"):
        return is_document_like_image(file_path)

    # Altri formati: di default niente OCR
    return False
