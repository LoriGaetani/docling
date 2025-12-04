from dataclasses import dataclass
from typing import Optional



@dataclass
class ExtractionRequested:

    job_id: str
    collection_id: int
    file_id: str
    # optional for direct text input (per l'input di testo diretto)
    bucket: Optional[str] = None
    object_key: Optional[str] = None
    # direct text field (campo di testo diretto)
    direct_text: Optional[str] = None
    file_name: Optional[str] = None
    model_name: Optional[str] = None
    prompt: Optional[str] = None