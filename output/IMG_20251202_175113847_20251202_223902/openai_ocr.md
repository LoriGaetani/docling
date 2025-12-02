# OCR report (OpenAI)

> Docling OCR engine: **easyocr** (enabled: True)

> External OCR engine: **openai:gpt-4o**

File: `dataset/IMG_20251202_175113847.jpg`

## OpenAI OCR (gpt-4o)

### Configurazione
- **Temperature**: 0.0 (Deterministic)
- **Detail**: High

### Prompt usato
```text

                You are an OCR engine specializing in verbatim transcription.
                Your goal is absolute fidelity to the visual text, not grammatical accuracy.
                
                Strict rules:
                1. Transcribe the text EXACTLY as it appears in the image.
                2. DO NOT correct typos, grammar, or syntax errors (e.g., if it says 'architectural,' do not write 'architectural').
                3. DO NOT expand abbreviations.
                4. Respect the structure of lines and lists.
                5. If a word is ambiguous or cut off, write what you see, don't guess.
                6. Do not add comments, preambles, or salutations. Return ONLY the transcribed text.
                
```

### Token usati
```json
{'input_tokens': 922, 'output_tokens': 476, 'total_tokens': 1398}
```

### Testo rilevato
```text
001. 01MNVPC – Computer Grafica  
002. (Ingegneria Del Cinema E Dei Mezzi Di Comunicazione - Torino)
003. 
004. 1 Luglio 2025
005. 
006. Ti hanno affidato il compito di sviluppare un prototipo frontend per una piattaforma che mostra attività commerciali e servizi locali (come caffetterie, cliniche, palestre) su una mappa. L’app recupera i servizi disponibili in una determinata area e permette agli utenti di esaminarli, filtrarli e visualizzarne i dettagli.
007. 
008. Il tuo obiettivo è implementare una parte di questa app – e fare scelte architetturali importanti come parte dell’esercizio.
009. 
010. Cosa devi costruire
011. 
012. NON devi implementare l’intera applicazione — solo una funzionalità specifica a scelta.
013. 
014. Devi:
015. 
016. 1. Scegliere una delle tre funzionalità seguenti da implementare:
017.    o “Esplora servizi vicini” – vista mappa, filtro per categoria e lista
018.    o “Dettaglio servizio e percorso” – pagina dettagli + distanza e percorso fino al servizio
019.    o “Dashboard dei preferiti” – stato locale + persistenza dei preferiti
020. 
021. 2. Documentare in 2–3 frasi:
022.    o Perché hai scelto questa funzionalità
023.    o Quali componenti o pattern di gestione dello stato hai considerato e utilizzato
024. 
025. 3. Implementare la funzionalità scelta con:
026.    o Navigazione con React Router
027.    o Componenti Material UI
028.    o Gestione dello stato
029.    o Uso dei dati contenuti nel file JSON simile a quello fornito
030.    o Mappa con marker relativi ai servizi
031. 
032. Poiché l’applicazione è destinata ad essere usata in una pluralità di contesti, abbi cura di gestire una corretta impaginazione su cellulari, tablet e pc desktop.
033. 
034. Criteri di valutazione
035. • Architettura chiara e ragionata 20%
036. • Implementazione della funzionalità scelta 30%
037. • Gestione stato (context/useState) 10%
038. • Uso di MUI e chiarezza visiva 10%
039. • Integrazione mappa e localizzazione 10%
040. • Organizzazione del codice 10%
041. • Documentazione delle decisioni 10%
```
