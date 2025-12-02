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
Agisci come un software OCR professionale. Trascrivi il testo nell'immagine carattere per carattere. NON correggere errori di battitura o grammaticali (es. se leggi 'impaginazione', non scrivere 'immaginazione'). Mantieni la formattazione originale. Non aggiungere nulla oltre al testo rilevato.
```

### Token usati
```json
{'input_tokens': 25580, 'output_tokens': 493, 'total_tokens': 26073}
```

### Testo rilevato
```text
001. 01MNVPC – Computer Grafica
002. (Ingegneria Del Cinema E Dei Mezzi Di Comunicazione - Torino)
003. 
004. 1 Luglio 2025
005. 
006. Ti hanno affidato il compito di sviluppare un prototipo frontend per una piattaforma che mostra
007. attività commerciali e servizi locali (come caffetterie, cliniche, palestre) su una mappa. L’app
008. recupera i servizi disponibili in una determinata area e permette agli utenti di esaminarli, filtrarli e
009. visualizzarne i dettagli.
010. 
011. Il tuo obiettivo è implementare una parte di questa app – e fare scelte architettonali importanti
012. come parte dell’esercizio.
013. 
014. Cosa devi costruire
015. NON devi implementare l’intera applicazione – solo una funzionalità specifica a scelta.
016. 
017. Devi:
018. 
019. 1. Scegliere una delle tre funzionalità seguenti da implementare:
020.    o “Esplora servizi vicini” – vista mappa, filtro per categoria e lista
021.    o “Dettaglio servizio e percorso” – pagina dettagli + distanza e percorso fino al servizio
022.    o “Dashboard dei preferiti” – stato locale + persistenza dei preferiti
023. 
024. 2. Documentare in 2-3 frasi:
025.    o Perché hai scelto questa funzionalità
026.    o Quali componenti o pattern di gestione dello stato hai considerato e utilizzato
027. 
028. 3. Implementare la funzionalità scelta con:
029.    o Navigazione con React Router
030.    o Componenti Material UI
031.    o Gestione dello stato
032.    o Uso dei dati contenuti nel file JSON simile a quello fornito
033.    o Mappa con marker relativi ai servizi
034. 
035. Poiché l’applicazione è destinata ad essere usata in una pluralità di contesti, abbi cura di gestire
036. una corretta immaginazione su cellulari, tablet e pc desktop.
037. 
038. Criteri di valutazione
039. ● Architettura chiara e ragionata                     20%
040. ● Implementazione della funzionalità scelta           30%
041. ● Gestione stato (context/useState)                   10%
042. ● Uso di MUI e chiarezza visiva                        10%
043. ● Integrazione mappa e localizzazione                 10%
044. ● Organizzazione del codice                            10%
045. ● Documentazione delle decisioni                      10%
```
