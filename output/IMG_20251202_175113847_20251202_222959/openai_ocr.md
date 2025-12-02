# OCR report (OpenAI)

> Docling OCR engine: **easyocr** (enabled: True)

> External OCR engine: **openai:gpt-4o-mini**

File: `dataset/IMG_20251202_175113847.jpg`

## OpenAI OCR (gpt-4o-mini)

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
{'input_tokens': 25658, 'output_tokens': 479, 'total_tokens': 26137}
```

### Testo rilevato
```text
001. 01MNVPC – Computer Grafica
002. (Ingengeria Del Cinema E Dei Mezzi Di Comunicazione - Torino)
003. 
004. 1 Luglio 2025
005. 
006. Ti hanno affidato il compito di sviluppare un prototipo frontend per una piattaforma che mostra attività commerciali e servizi locali (come caffetterie, cliniche, palestre) su una mappa. L’app recupera i servizi disponibili in una determinata area e permette agli utenti di esaminarli, filtrarli e visualizzarne i dettagli.
007. 
008. Il tuo obiettivo è implementare una parte di questa app – e fare scelte architettonali importanti come parte dell’esercizio.
009. 
010. Cosa devi costruire
011. NON devi implementare l’intera applicazione – solo una funzionalità specifica a scelta.
012. 
013. Devi:
014. 
015. 1. Scegliere una delle tre funzionalità seguenti da implementare:
016.    o “Esplora servizi vicini” – vista mappa, filtro per categoria e lista
017.    o “Dettaglio servizio e percorso” – pagina dettagli + distanza e percorso fino al servizio
018.    o “Dashboard dei preferiti” – stato locale + persistenza dei preferiti
019. 
020. 2. Documentare in 2-3 frasi:
021.    o Perché hai scelto questa funzionalità
022.    o Quali componenti o pattern di gestione dello stato hai considerato e utilizzato
023. 
024. 3. Implementare la funzionalità scelta con:
025.    o Navigazione con React Router
026.    o Componenti Material UI
027.    o Gestione dello stato
028.    o Uso dei dati contenuti nel file JSON simile a quello fornito
029.    o Mappa con marker relativi ai servizi
030. 
031. Poiché l’applicazione è destinata ad essere usata in una pluralità di contesti, abbi cura di gestire una corretta immaginazione su cellulari, tablet e pc desktop.
032. 
033. Criteri di valutazione
034. ● Architettura chiara e ragionata 20%
035. ● Implementazione della funzionalità scelta 30%
036. ● Gestione stato (context/useState) 10%
037. ● Uso di MUI e chiarezza visiva 10%
038. ● Integrazione mappa e localizzazione 10%
039. ● Organizzazione del codice 10%
040. ● Documentazione delle decisioni 10%
```
