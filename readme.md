# JARVIS Mio

Assistente personale AI per desktop, progettato per ascoltare comandi vocali, comprendere il contesto dello schermo e svolgere azioni verificabili sul computer.

Questo repository contiene una versione personalizzata di JARVIS basata su Python, Gemini Live API e una HUD desktop in PyQt6. Il progetto unisce conversazione vocale in tempo reale, automazione del sistema operativo, memoria persistente, controllo del browser, strumenti per file e giochi e un dashboard remoto locale.

## Cosa fa

- Conversazione vocale bidirezionale con input da microfono e risposta audio.
- Routing degli intenti prima dell'esecuzione degli strumenti, con domande di chiarimento quando una richiesta e ambigua.
- Controllo di applicazioni, finestre, volume, luminosita, Wi-Fi, scorciatoie e alimentazione.
- Lettura dello schermo tramite OCR locale opzionale e fallback a visione multimodale.
- Apertura e controllo del browser con percorso DOM-first e fallback visivo.
- Ricerca, lettura, riepilogo, spostamento, copia e scrittura di file locali.
- Avvio e aggiornamento di giochi tramite Steam ed Epic, con rilevamento degli eseguibili installati.
- Invio assistito di messaggi, controllo di YouTube, ricerche web, meteo e ricerca voli.
- Memoria lunga locale con indicizzazione dei file, profili prompt e continuita della sessione.
- Undo per molte operazioni reversibili e conferma umana per spegnimento, riavvio e Wi-Fi.
- Plugin estendibili tramite un singolo file Python nella cartella `plugins/`.
- Dashboard web locale per il controllo remoto tramite token temporanei e connessione cifrata.
- Accessibilita opzionale: screen reader, OCR locale e scorciatoie globali configurabili.

## Architettura

```text
main.py                 Avvio e ciclo principale Gemini Live
ui.py                   HUD PyQt6, log, waveform e controlli
core/                   Audio, prompt, memoria, guardrail, conferme e undo
actions/                Strumenti operativi per sistema, browser, file e web
plugins/                Estensioni caricabili senza modificare il core
dashboard/              Server e interfaccia per il controllo remoto locale
memory/                 Gestione della memoria persistente locale
tests/                  Test automatici dei contratti di automazione
```

## Requisiti

- Windows 10/11, macOS o Linux.
- Python 3.11, 3.12 o una versione compatibile con le dipendenze installate.
- Microfono e altoparlanti per l'interazione vocale.
- Una chiave API Gemini configurata localmente.
- Tesseract OCR opzionale per il grounding locale dei testi sullo schermo.

## Installazione

```bash
git clone https://github.com/ilfenomeno-gif/jarvis-mio.git
cd jarvis-mio
python -m venv .venv
```

Su Windows:

```powershell
.\.venv\Scripts\Activate.ps1
```

Installare le dipendenze e i browser Playwright:

```bash
python -m pip install -r requirements.txt
python -m playwright install
```

Configurare la chiave API nel file locale `config/api_keys.json`, che e escluso dal controllo versione:

```json
{
  "GEMINI_API_KEY": "inserire-la-propria-chiave"
}
```

Avviare JARVIS con:

```bash
python main.py
```

In alternativa, `python setup.py` installa le dipendenze, prepara Playwright e verifica l'integrazione Windows quando disponibile.

## Sicurezza e privacy

- Le chiavi API, i certificati, la memoria lunga e i log locali sono esclusi dal repository.
- Le azioni irreversibili richiedono una conferma esplicita nell'interfaccia.
- I percorsi vengono validati dai guardrail prima delle operazioni sui file.
- La memoria viene conservata localmente in `memory/long_term.json` e non viene pubblicata.
- Il dashboard deve essere usato su una rete fidata; token e certificati non vanno condivisi.
- Le azioni automatiche possono interagire con applicazioni reali: verificare sempre destinatari, percorsi e finestre prima di operazioni sensibili.

## Test e verifica

Eseguire i test automatici con:

```bash
python -m unittest discover -s tests -v
```

Per verificare la sintassi dell'intero progetto:

```bash
python -m compileall .
```

Le prove GUI su Steam, browser e messaggistica richiedono ancora un ambiente interattivo reale. L'OCR locale richiede sia il pacchetto Python `pytesseract` sia l'eseguibile Tesseract installato nel sistema.

## Accessibilita

Il modulo [core/accessibility.py](core/accessibility.py) aggiunge un ponte opt-in per la lettura dello schermo:

- usa l'OCR locale su tutto lo schermo o su una regione `(x, y, larghezza, altezza)`;
- invia il testo al TTS gia configurato da JARVIS oppure a `pyttsx3` come fallback offline;
- usa `nvdaControllerClient.dll` quando NVDA e installato su Windows;
- registra `Ctrl+Alt+R` per leggere lo schermo e `Ctrl+Alt+S` per lo stato solo dopo una chiamata esplicita a `start_hotkeys()`;
- rimuove le scorciatoie con `stop_hotkeys()`.

Le hotkey globali non vengono attivate automaticamente all'avvio. Per NVDA e necessario rendere disponibile `nvdaControllerClient.dll`; per l'OCR servono `pytesseract` e l'eseguibile Tesseract.

## Documentazione tecnica

- [Piano tecnico e diagnostica](PIANO_TECNICO_JARVIS.md)
- [Profili prompt](core/prompts/)
- [Template per plugin](plugins/_template.py)
- [Test di automazione](tests/test_automation_contracts.py)

## Stato del progetto

Il progetto e in sviluppo attivo. La base include routing degli intenti, memoria locale, OCR opzionale, guardrail, undo, profili prompt, dashboard e strumenti per l'automazione desktop. Le integrazioni che dipendono da una GUI reale, da driver audio, da API esterne o da launcher installati devono essere validate sulla macchina dell'utente.

## Licenza

Consultare [LICENSE](LICENSE) per i termini di distribuzione del progetto.