# OCR report (OpenAI)

> Docling OCR engine: **easyocr** (enabled: True)

> External OCR engine: **openai:gpt-4o-mini**

File: `dataset/IMG_20251202_175113847.jpg`

## OpenAI OCR (gpt-4o-mini)

### Prompt usato
```text
Trascrivi esattamente tutto il testo leggibile nell'immagine, riga per riga, senza aggiungere commenti o descrizioni.
```

### Token usati
```json
{'input_tokens': 25538, 'output_tokens': 487, 'total_tokens': 26025}
```

### Testo rilevato
```text
001. ```
002. 01MNVPC – Computer Grafica
003. (Ingegneria Del Cinema E Dei Mezzi Di Comunicazione - Torino)
004. 1 Luglio 2025
005. Ti hanno affidato il compito di sviluppare un prototipo frontend per una piattaforma che mostra attività commerciali e servizi locali (come caffetterie, cliniche, palestre) su una mappa. L’app recupera i servizi disponibili in una determinata area e permette agli utenti di esaminarli, filtrarli e visualizzarne i dettagli.
006. Il tuo obiettivo è implementare una parte di questa app – e fare scelte architettoniche importanti come parte dell’esercizio.
007. Cosa devi costruire
008. NON devi implementare l’intera applicazione – solo una funzionalità specifica a scelta.
009. Devi:
010. 1. Scegliere una delle tre funzionalità seguenti da implementare:
011.    - “Esplora servizi vicini” – vista mappa, filtro per categoria e lista
012.    - “Dettaglio servizio e percorso” – pagina dettagli + distanza e percorso fino al servizio
013.    - “Dashboard dei preferiti” – stato locale + persistenza dei preferiti
014. 2. Documentare in 2-3 frasi:
015.    - Perché hai scelto questa funzionalità
016.    - Quali componenti o pattern di gestione dello stato hai considerato e utilizzato
017. 3. Implementare la funzionalità scelta con:
018.    - Navigazione con React Router
019.    - Componenti Material UI
020.    - Gestione dello stato
021.    - Uso dei dati contenuti nel file JSON simile a quello fornito
022.    - Mappa con marker relativi ai servizi
023. Poiché l’applicazione è destinata ad essere usata in una pluralità di contesti, abbi cura di gestire una corretta immaginazione sui cellulari, tablet e pc desktop.
024. Criteri di valutazione
025. - Architettura chiara e ragionata                     20%
026. - Implementazione della funzionalità scelta         30%
027. - Gestione stato (context/useState)                  10%
028. - Uso di MUI e chiarezza visiva                        10%
029. - Integrazione mappa e localizzazione                10%
030. - Organizzazione del codice                             10%
031. - Documentazione delle decisioni                       10%
032. ```
```
