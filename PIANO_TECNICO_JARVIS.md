# Piano Tecnico e Analisi di Progetto: Potenziamento di JARVIS

Questo documento contiene l'analisi del progetto, la diagnostica dell'attuale architettura e un piano tecnico progettuale per rendere Jarvis significativamente più intelligente nell'interazione con il sistema operativo, le applicazioni, il browser e la lettura dello schermo.

## Analisi e Diagnostica Attuale

Dalla scansione del codice sorgente (es. `send_message.py`, `screen_processor.py`, `open_app.py`, `browser_control.py`), emergono le seguenti criticità e limitazioni dell'approccio attuale:

1. **Automazione Cieca (Blind Automation):** Molte funzioni di controllo (come invio messaggi o apertura app) si basano su `pyautogui` con attese fisse (`time.sleep`) e sequenze di tasti predefinite (es. `win`, incolla nome, `enter`). Se il PC è lento o un popup si intromette, l'automazione fallisce.
2. **Interazione col Browser:** Attualmente Jarvis fatica a contestualizzare dinamicamente una pagina web già aperta. Non possiede un meccanismo robusto per mappare gli elementi visivi del browser in coordinate cliccabili in tempo reale.
3. **Lettura Schermo Limitata:** Il processamento dello schermo è basilare. Serve un sistema di "Visual Grounding" che associ il testo o gli elementi dell'interfaccia a coordinate X/Y precise.
4. **Gestione Giochi (Installazione/Avvio):** Basarsi solo sui percorsi fissi o sui click pre-programmati rende difficile interagire con client complessi (es. Steam, Epic Games, Battle.net) dove i tasti cambiano posizione o lingua.

## Proposed Changes (Piano Tecnico)

Il progetto prevede l'implementazione di un motore di **Agentic Computer Control** (Controllo Computerizzato Agente) basato su input multimodali.

### 1. Modulo di "Visual Grounding" (Lettura Schermo Avanzata)

- Sostituiremo le macro "cieche" con una libreria di visione informatica o un OCR avanzato (Tesseract/EasyOCR) integrato con il modello multimodale.
- **Flusso:** Jarvis scatterà uno screenshot, identificherà le coordinate dei bottoni (es. "Installa", "Invia", la barra degli indirizzi di Chrome) e cliccherà *esattamente* su quelle coordinate invece di usare `Tab` o tempistiche fisse.

### 2. Gestione Intelligente del Browser e delle App

- **Browser:** Integrazione con protocolli di automazione (es. Playwright/Selenium) o estensioni per leggere il DOM e analizzare la pagina *già aperta* dall'utente. Se non è possibile usare il DOM, Jarvis userà il modulo Visual Grounding per leggere lo schermo, identificare i campi di testo e i link, ed emulare il mouse in modo chirurgico.
- **App & Messaggi:** Prima di inviare un messaggio su Whatsapp/Telegram, Jarvis verificherà visivamente che la chat corretta sia in focus, digitando il messaggio e premendo Invia solo dopo conferma visiva.

### 3. Procedure di Installazione e Avvio Giochi

- Implementazione di flussi adattivi: Jarvis capirà visivamente in quale launcher si trova. Se vede il pulsante "Installa" o "Gioca", calcolerà la posizione e cliccherà. Includeremo la gestione dinamica degli errori (es. "Spazio insufficiente sul disco" letto tramite OCR).

### Fasi di Implementazione

1. **Aggiornamento Core:** Miglioramento di `screen_processor.py` aggiungendo logica OCR per estrarre il testo e le coordinate (BBox).
2. **Refactoring Automazioni:** Sostituzione dei `time.sleep()` in `send_message.py` e `open_app.py` con cicli di attesa basati su conferme visive.
3. **Integrazione Browser e Giochi:** Aggiunta di funzioni specializzate in `browser_control.py` e `game_updater.py` per interagire con l'UI analizzata.

IMPORTANT

**User Review Required** Questo piano modificherà profondamente il modo in cui Jarvis muove il mouse e legge lo schermo, rendendolo molto più autonomo ma anche richiedendo una maggiore potenza di calcolo (per analizzare gli screenshot in tempo reale). Sei d'accordo con questo approccio architetturale basato sulla visione e sui clic precisi (Computer Vision/OCR)?

## Open Questions

- Vuoi che l'interazione con le pagine web avvenga puramente tramite analisi visiva (screenshot + clic simulati) o preferisci che Jarvis usi librerie web nascoste per "leggere" nativamente il codice della pagina web (DOM)?
- Quale motore OCR o multimodale vuoi che Jarvis utilizzi per la lettura dello schermo locale (es. Tesseract installato localmente, o invio degli screen a un'API AI)?

## Verification Plan

1. **Test Singoli Clic:** Chiederemo a Jarvis di cliccare l'icona di Google Chrome sul desktop.
2. **Test Lettura Browser:** Con una pagina aperta su Chrome, chiederemo a Jarvis di leggerla, riassumerla e cliccare su un articolo specifico visibile a schermo.
3. **Test Messaggistica:** Chiederemo l'invio di un messaggio di test tramite l'app Desktop di Telegram/Whatsapp e valuteremo se Jarvis riesce a posizionarsi sulla barra di testo corretta senza errori.

## Stato di Implementazione e Diagnostica Automatica

Questa sezione viene aggiornata insieme alle modifiche del progetto e contiene solo risultati verificati.

### Completato

- `core.guardrails.resolve_safe_path()` espande variabili d'ambiente Windows (`%USERPROFILE%`) e `~`, rimuovendo anche virgolette esterne dai percorsi copiati dalla chat.
- Le trascrizioni cumulative Gemini Live vengono unite senza ripetere frammenti già ricevuti, riducendo echi e duplicazioni nel log e nella memoria di sessione.
- Il prompt e le regole autorizzano opinioni personali motivate: JARVIS distingue giudizi da fatti e non inventa esperienze personali.
- `core/intent_router.py` classifica i target come gioco/app, file/documento o ambiguo prima dell'esecuzione dei tool.
Per integrare queste funzioni direttamente come metodi nativi all'interno della classe principale del tuo assistente in jarvis-mio, puoi strutturare il codice creando una classe dedicata o aggiungendo i metodi direttamente al core del tuo Jarvis.

Ecco come puoi implementare l'accessibilità (Screen Reader, OCR e comandi da tastiera) come funzioni interne native:

Python
import threading
import time
import keyboard
import pyautogui
import pytesseract
from PIL import Image
import pyttsx3

class JarvisAccessibility:
    def __init__(self, jarvis_instance=None):
        self.jarvis = jarvis_instance  # Riferimento al core di Jarvis (se vuoi passare dati o loggare)
        
        # Inizializzazione del motore vocale nativo
        self.engine = pyttsx3.init()
        self.is_active = True
        
        # Configura i comandi nativi all'avvio del modulo
        self._register_native_hotkeys()

    def speak(self, text):
        """Funzione nativa di Screen Reader / Sintesi Vocale."""
        print(f"[Jarvis ScreenReader]: {text}")
        # Gestione per evitare conflitti di thread con il TTS
        self.engine.say(text)
        self.engine.runAndWait()

    def ocr_screen(self):
        """Funzione nativa OCR: legge il testo visibile sullo schermo."""
        self.speak("Analisi visiva dello schermo in corso...")
        try:
            screenshot = pyautogui.screenshot()
            text = pytesseract.image_to_string(screenshot, lang='ita')
            
            if text.strip():
                # Pulizia del testo e lettura
                clean_text = " ".join(text.split())
                self.speak("Ecco cosa ho trovato sullo schermo: " + clean_text[:300]) # Legge i primi 300 caratteri per evitare blocchi lunghi
            else:
                self.speak("Non ho rilevato alcun testo leggibile sullo schermo.")
        except Exception as e:
            self.speak("Errore durante l'acquisizione OCR dello schermo.")
            print(f"Errore OCR: {e}")

    def click_and_type(self, target_text, text_to_type):
        """Funzione nativa di interazione: cerca un testo sullo schermo e ci interagisce."""
        self.speak(f"Cerco l'elemento {target_text} sullo schermo...")
        # Nota: Qui puoi integrare una ricerca basata su OCR per trovare le coordinate del testo
        # Per semplicità, simuliamo un'azione rapida da tastiera/mouse
        pyautogui.write(text_to_type)
        self.speak("Fatto.")

    def _register_native_hotkeys(self):
        """Registra le scorciatoie globali che attivano le funzioni native di Jarvis."""
        try:
            # Ctrl + Alt + R -> Attiva la lettura OCR dello schermo
            keyboard.add_hotkey('ctrl+alt+r', self.ocr_screen)
            
            # Ctrl + Alt + S -> Legge lo stato di Jarvis
            keyboard.add_hotkey('ctrl+alt+s', lambda: self.speak("I sistemi di accessibilità di Jarvis sono operativi."))
            
            print("[Jarvis] Scorciatoie di accessibilità native registrate con successo.")
        except Exception as e:
            print(f"Impossibile registrare le hotkey globali: {e}")

    def run_listener(self):
        """Mantiene attivo il listener dei comandi da tastiera in background."""
        while self.is_active:
            time.sleep(1)

# Esempio di integrazione nel main del tuo progetto jarvis-mio
if __name__ == "__main__":
    print("Avvio del core di Jarvis con modulo di accessibilità nativo...")
    
    # Inizializza il modulo
    accessibility = JarvisAccessibility()
    accessibility.speak("Jarvis online con supporto accessibilità integrato.")
    
    # Avvia il loop di ascolto tastiera in un thread separato per non bloccare l'assistente
    listener_thread = threading.Thread(target=accessibility.run_listener, daemon=True)
    listener_thread.start()
    
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        accessibility.is_active =iccation = False
        print("Arresto di Jarvis in corso...")
Come collegarlo alla struttura esistente di jarvis-mio:
Crea un file accessibility.py (o inserisci la classe JarvisAccessibility dentro i tuoi moduli esistenti).

Istanzialo nel file principale (es. main.py o jarvis.py) quando avvii l'applicazione.

Usando threading, il sistema di scorciatoie da tastiera (ctrl+alt+r per l'OCR dello schermo, ecc.) girerà in background permettendoti di richiamare le funzioni di accessibilità in qualsiasi momento, indipendentemente da cosa sta facendo il resto del programma.- I titoli di gioco esatti passano al launcher corretto; i nomi parziali ambigui vengono bloccati con una domanda formale invece di essere cercati alla cieca.
- Una categoria esplicitamente pronunciata dall'utente viene salvata in `memory/long_term.json` come associazione persistente `target_intent_<nome>`; i test usano mock e non modificano la memoria reale.
- Le ricerche generiche non possono più assorbire una richiesta esplicita di gioco, e i tool file non indovinano in caso ambiguo.
- `file_controller.py` indicizza automaticamente ogni file trovato o letto con chiavi `file_path_<nome>` e percorso assoluto in memoria lunga.
- Le aperture successive con solo nome o parola chiave consultano prima l'indice; se il percorso memorizzato non esiste più, la ricerca ricorsiva può ricostruire l'associazione.
- `game_updater.py` legge `appmanifest_*.acf`, ricostruisce la cartella `Steam\common\<installdir>` e individua gli eseguibili locali dei giochi installati.
- `computer_control.py` usa ora il testo OCR locale per `screen_find` e `screen_click` prima del fallback Gemini, permettendo di trovare etichette come `Play`, `Gioca` e `Invia` senza coordinate indovinate.
- `youtube_video.py` applica la riproduzione completa: estrae il primo risultato pertinente, apre il link `watch` e restituisce il link diretto; se l'estrazione o l'apertura fallisce, apre e restituisce la ricerca YouTube mirata.
- `core/prompt.txt` contiene una direttiva globale di esecuzione end-to-end: nessun successo dichiarato per azioni parziali, URL mirati per i contenuti, verifica osservabile e fallback funzionale trasparente.
- L'avvio Steam dei giochi usa prima l'eseguibile locale (con Steam avviato in background per la licenza); per Victoria 3 privilegia `binaries\win64\v3.exe` e salva il percorso trovato in memoria lunga.
- Diagnostica reale del PC: Steam trovato in `C:\Program Files (x86)\Steam`, ma `Victoria 3` non risulta attualmente installato o non ha un manifest rilevabile; nessun percorso `.exe` è stato inventato o salvato.
- Pulizia memoria verificata: `memory/long_term.json` non contiene associazioni Victoria 3 verso file locali o percorsi errati.
- La priorità di avvio giochi è ora esplicita: Steam/Epic e `game_updater` precedono sempre ricerca file e ricerca generica.
- Rimosso il residuo obsoleto `target_intent_victoria_3 = game:launcher`; `Victoria` resta ambiguo, mentre `Victoria 3` con richiesta Steam viene instradato esplicitamente a Steam.
- Aggiunto `core/prompt_router.py` con profili dinamici `developer_mode`, `strategic_mode`, `quick_command` e `standard_assistant`, caricati da `core/prompts/` con fallback sicuro.
- Collegato come sorgente documentata il repository prompt [`ilfenomeno-gif/repo-prompt`](https://github.com/ilfenomeno-gif/repo-prompt); i profili locali restano prioritari e il runtime non scarica contenuti remoti automaticamente.
- Integrati nel cuore permanente di `core/prompt.txt` gli otto principi adattati del repository: selezione tool, chiarificazione, comunicazione strutturata, contesto, iterazione, verifica, automazione graduata e rifinitura umana.
- I comandi testuali ricevono il profilo dinamico prima dell'esecuzione; i comandi vocali restano protetti dal system prompt e dall'intent router dei tool. Il ragionamento interno non viene esposto all'utente.
- OCR: `pytesseract`, PyAutoGUI e Pillow installati nell'ambiente `.venv`; l'eseguibile nativo Tesseract resta una dipendenza Windows separata. Il comando Python globale usato in precedenza da JARVIS deve usare lo stesso ambiente o installare il wrapper anche lì.
- `screen_processor.py` espone OCR opzionale con testo, confidence e bounding box in coordinate assolute.
- Il grounding prova prima l'OCR locale e usa Gemini come fallback per elementi non testuali o quando l'OCR non e disponibile.
- L'attesa OCR termina immediatamente quando il backend non e installato; non introduce ritardi artificiali.
- `send_message.py` non considera riuscito il click del campo messaggio se non ha ottenuto coordinate verificate.
- `open_app.py` riconosce varianti vocali di GeoGuessr e i giochi Steam.
- L'avvio dei giochi Steam segue il flusso interattivo: avvio Steam, focus della finestra, ricerca nella Libreria e click visuale su `Play`, `Gioca`, `Launch` o `Avvia`.
- `browser_control.py` mantiene il percorso DOM-first con fallback a visione per la lettura della pagina attiva.
- `game_updater.py` usa il grounding visuale per i pulsanti del launcher e verifica errori di spazio insufficiente quando l'OCR e disponibile.

### Test automatici eseguiti

Comando: `python -m unittest discover -s tests -v`

Risultato verificato: **28 test superati**. I test coprono anche la direttiva globale di completamento end-to-end.

Compilazione verificata con Python 3.13: `main.py` e i moduli di automazione compilano senza errori.

### Diagnostica dell'ambiente corrente

- Python: 3.13.7 su Windows 11.
- Disponibili: `pyautogui`, `pygetwindow`, `mss`, Pillow, Playwright, `psutil`, `google.genai`.
- Non disponibili nell'interprete usato da JARVIS: modulo Python `pytesseract` ed eseguibile Tesseract.
- Il rilevamento ora verifica entrambi i componenti separatamente e disabilita l'OCR senza introdurre attese false quando manca l'eseguibile.
- Conseguenza: il grounding OCR locale non e ancora attivo; il fallback Gemini resta operativo.
- Steam non e nel `PATH`; il rilevamento usa comunque registro Windows e percorsi standard (`Program Files`, `C:\Steam`, ecc.).
- Startup diagnostico verificato: `main.py` resta attivo oltre 6 secondi e inizializza plugin, audio e dashboard senza errori applicativi.
- Rimane un warning Qt non bloccante relativo a `SetProcessDpiAwarenessContext` e ai permessi DPI di Windows.
- Startup diagnostic successivo ai fix: processo vivo oltre 5 secondi; plugin, audio e dashboard inizializzati, nessun crash applicativo.

### Test manuali ancora necessari

Questi test richiedono la GUI reale e non vengono simulati automaticamente per evitare azioni indesiderate:

1. Aprire un gioco installato tramite Steam e verificare ricerca Libreria e click `Play`.
2. Aprire Chrome, leggere la pagina attiva tramite DOM e verificare il fallback visivo su una pagina non accessibile al DOM.
3. Inviare un messaggio di prova solo dopo aver confermato visivamente chat, destinatario e campo di testo.

### Prossimo incremento

Installare e validare Tesseract nell'interprete Python 3.13 corretto, aggiungere test con screenshot sintetici per OCR, introdurre un controllo post-click del processo di gioco e validare il clic reale su Steam/Telegram/Chrome. Il piano non considera conclusa l'automazione finche questi test manuali non avranno esito positivo.

## Analisi Diagnostica Completa del Progetto

### Architettura verificata

- `main.py` è l'entrypoint: inizializza Qt, audio, Gemini Live, memoria, plugin, dashboard e task di monitoraggio.
- `core/` contiene guardrail subprocess, memoria, conferme, undo, prompt statico e routing dinamico dei prompt.
- `actions/` contiene i tool operativi per file, browser, desktop, messaggistica, OCR/visione, giochi, sistema, web e sviluppo.
- `plugins/` viene scoperta e validata all'avvio; i nomi che collidono con tool core vengono rifiutati.
- `dashboard/` espone il controllo remoto locale con token temporanei e cifratura dei messaggi.

### Finding critici risolti

1. Il guard globale dei subprocess bloccava `steam.exe`, `cmd.exe`, `netsh` e gli eseguibili dei giochi. La whitelist ora include i comandi supportati e consente eseguibili `.exe` solo in librerie Steam/Epic riconoscibili.
2. L'avvio URL Windows usava `shell=True`, incompatibile con il guard. `open_app.py` usa ora `os.startfile()` per URI e percorsi Windows interessati.
3. Il controllo giochi, file, OCR e prompt dinamici era coperto da test isolati ma non da una diagnosi globale. Ora sono presenti test di contratto per routing, launcher, memoria, OCR, sicurezza e profili prompt.

### Rischi residui

- Il dashboard tenta ancora un comando `.bat` con `shell=True` per la configurazione firewall; il guard lo rifiuta intenzionalmente e il codice passa al fallback UAC `ShellExecuteW`. La configurazione automatica può quindi richiedere privilegi amministrativi.
- L'OCR locale richiede l'eseguibile nativo Tesseract oltre al pacchetto Python `pytesseract`; senza di esso viene usato Gemini.
- L'interazione PyAutoGUI e il click Steam dipendono dalla finestra attiva, dalla lingua dei pulsanti e dalla risoluzione DPI. Il percorso ha attese/grounding, ma richiede ancora prova GUI reale.
- Il dashboard è raggiungibile sulla rete locale; token, chiavi TLS e regole firewall devono essere trattati come superficie di sicurezza separata.
- Le chiamate Gemini, DDG, Playwright e TTS dipendono da rete, API key, quota e sessioni browser; i fallback riducono ma non eliminano questi vincoli.

### Verifica globale eseguita

- **44** file Python importati senza errori.
- `compileall` sull'intero progetto superato.
- **25/25** test automatici superati.
- Memoria lunga invariata durante i test.
- Startup reale verificato: processo vivo oltre 6 secondi con plugin, audio e dashboard inizializzati.
- Warning Qt `SetProcessDpiAwarenessContext` rilevato, non bloccante e legato ai permessi DPI di Windows.

### Ordine consigliato dei prossimi test manuali

1. Con Steam aperto e un gioco realmente installato, verificare risoluzione manifest, avvio eseguibile locale e presenza Steam per la licenza.
2. Con Tesseract installato, mostrare un pulsante `Play` o `Gioca` e verificare `screen_find`/`screen_click` su una schermata controllata.
3. Aprire una pagina in Chrome e verificare DOM-first, fallback visivo e comportamento su elemento non trovato.
4. Eseguire un messaggio di prova con destinatario non ambiguo e confermare che chat e campo di testo siano identificati prima dell'invio.
