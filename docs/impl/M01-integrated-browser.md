# M01 — Integrated browser

## Obiettivo

Aprire nomi di siti e URL HTTP(S) dentro Jarvis, offrendo indietro, avanti,
ricarica e chiusura con ritorno alla vista precedente. Tenere il browser
separato dalla pagina GEV e dal suo lifecycle.

## 1. Diagnosi (stato reale del repo, rischi, dipendenze)

- `ui.py:2415` definisce `MainWindow`; `ui.py:2541` e `ui.py:2545` creano
  gli stack esistenti. `_center_split` mostra HUD/camera/GEV sopra il pannello
  `QTextEdit`.
- `QWebEngineView` è già disponibile nel venv ed è usata in `ui.py:2551` per
  GEV. Un secondo widget browser è quindi fattibile senza nuove dipendenze.
- `JarvisUI` espone metodi thread-safe via signal (`_content_sig`,
  `_gev_send_sig`); Gemini dispatcha gli strumenti in `main.py:_execute_tool`.
  L'implementazione deve usare lo stesso confine segnali/slot.
- `actions/browser_control.py` esegue automazione Playwright/browser esterno;
  non è il browser integrato richiesto. Lo strumento core `open_website`
  sarà distinto e dichiarato in `main.py`.
- Il browser non deve condividere o rimpiazzare il `QWebEnginePage` GEV. I
  redirect/navigazioni browser devono bloccare schemi diversi da HTTP(S).
- Nessuna dipendenza nuova richiesta. Ambiente verificato: Python 3.13.7,
  PyQt6 6.11.0, Qt/WebEngine 6.11.2.

## 2. Procedura (sotto-passi atomici: file → modifica → criterio di successo)

1. `core/browser_url.py` → normalizzare alias di sito e host senza schema,
   validare hostname/porta e consentire soltanto HTTP(S). Criterio: unit test
   pass per alias e URL validi, rifiuto esplicito degli schemi non ammessi.
2. `ui.py` → creare un contenitore browser dedicato con barra indirizzo,
   QWebEngineView e azioni indietro/avanti/ricarica/chiudi. Criterio: apertura e
   ritorno allo stack selezionato prima dell'apertura; `loadFinished` non
   riuscito produce stato/log esplicito.
3. `ui.py` → instradare le richieste browser da `JarvisUI` attraverso segnali
   collegati a slot GUI; isolare la pagina da GEV. Criterio: nessun accesso
   widget nel thread asyncio/plugin e le azioni GEV continuano a selezionare il
   proprio stack.
4. `main.py` → dichiarare `open_website(url)` e instradarlo a
   `JarvisUI.open_url_in_webview`; aggiornare la descrizione di `open_app` per
   evitare ambiguità. Criterio: Gemini può richiedere YouTube o un host; errori
   di validazione diventano risposta esplicita.
5. `tests/test_browser_url.py` e test UI mirati → proteggere normalizzazione e
   comportamenti non distruttivi. Criterio: suite focused verde.

## 3. Modifiche per file

- `core/browser_url.py` (nuovo): normalizzazione e allow-list schema URL.
- `ui.py`: widget browser dedicato, segnali/slot, cronologia, stato/caricamento.
- `main.py`: function declaration core, routing strumento, descrizione open_app.
- `tests/test_browser_url.py` (nuovo) e test UI mirati se compatibili col runner.
- `docs/impl/M01-integrated-browser.md`, `PROGRESS.md`: piano ed evidenza.

## 4. Test plan (automatici + manuali)

- Unit: alias `YouTube`, URL `example.com`, HTTP e HTTPS; valori vuoti,
  `file://`, `javascript:`, `data:`, `ftp://`, URL senza host, credenziali e
  porte non valide.
- UI: load di una pagina HTTP locale controllata; indietro/avanti/ricarica;
  chiusura che ripristina HUD o GEV; URL invalido non naviga; verifica che
  QWebEngine browser e GEV restino widget distinti. Harness Qt/WebEngine
  isolato ha terminato con crash nativo; resta necessario il test interattivo
  nell'app funzionante.
- Gemini/tool: declaration `open_website`, dispatch, errore esplicito su input
  invalido e nessuna azione widget fuori dal thread GUI.
- Regression: `pytest` mirato (poi suite Jarvis); GEV lifecycle e test già
  presenti.
- Smoke: avvio Jarvis dopo modifica, finestra e plugin GEV pronti. Audio/Live
  Gemini si riportano solo se effettivamente osservati.

## 5. Criteri di accettazione (checklist PASS/FAIL)

- [ ] YouTube/example.com e cronologia browser funzionano nel WebEngine live:
  bloccato dalla sessione Gemini non connessa e dal crash dei test runtime.
- [x] `file://`, `javascript:`, `data:`, FTP e altri schemi sono rifiutati dal
  normalizzatore; test focused passati.
- [x] La richiesta URL dal wrapper Jarvis passa attraverso un signal Qt; test
  unitario pass.
- [x] La logica stack conserva e ripristina la vista precedente; test unitario
  con doppia apertura pass.
- [x] GEV resta su widget/pagina distinti; app avviata dopo le modifiche, GEV
  pronto con 30 tool MCP.
- [ ] Nessuna navigazione malevola è stata eseguita nel WebEngine live;
  l'allow-list dei redirect è implementata, ma non esiste ancora evidenza runtime.

## 6. Analisi di fattibilità del presente file (checklist GO/NO-GO + esito)

- [x] Componenti e percorsi verificati nel codice reale; i file nuovi sono
  marcati come da creare.
- [x] PyQt6/WebEngine sono presenti nell'ambiente corrente.
- [x] Nessuna sovrapposizione prevista col bridge GEV: browser e GEV hanno
  pagine e stack indipendenti.
- [x] Test automatici eseguibili localmente; una pagina HTTP locale copre il
  test UI senza dipendere da provider/API remoti.
- [x] Rollback definito.

**Esito: GO.**

## 7. Rollback (come tornare indietro)

Commit inversi del branch `feat/m01-integrated-browser`, in ordine. Non
modificare o eliminare file locali di configurazione; nessun force-push o
riscrittura della history.

## 8. Registro esecuzione (data, esito verifica, esito convalida)

- 2026-10-04: diagnosi eseguita su checkout reale; GO prima dell'implementazione.
- 2026-10-04: `core/browser_url.py` e `tests/test_browser_url.py` implementati;
  primo run 19/20 ha rilevato `localhost:porta/percorso`, correzione applicata;
  test URL iniziale **20/20 PASS**.
- 2026-10-04: completati UI Qt, dichiarazione/dispatch `open_website`,
  navigazione sicura e unit test; suite Jarvis **73/73 PASS**, compileall PASS,
  Pylance syntax/problemi senza errori.
- 2026-10-04: smoke app aggiornata mostra `JARVIS — MARK LII`; GEV/MCP pronto
  con 30 tool. La sessione Gemini resta `Connecting...`; il comando testo non
  dispatcha tool perché `JarvisLive._on_text_command` ritorna senza sessione.
- 2026-10-04: tre prove runtime Qt/WebEngine isolate terminate con crash nativo
  Windows `0xC0000409`, prima di produrre risultati; harness temporanei non
  sono stati mantenuti. Navigazione e history reali non sono state convalidate.
- Convalida: **BLOCKED**, in attesa di sessione Gemini attiva o verifica UI
  interattiva con ambiente Qt/WebEngine funzionante.

## 9. Recap finale

Il browser integrato è implementato, con URL HTTP(S) validati, dichiarazione
Gemini, segnali Qt, pagina distinta da GEV e controlli UI. Test focused/suite
e avvio Jarvis passano. I criteri di navigazione live, YouTube, history e
redirect non sono stati convalidati: la sessione Gemini non era disponibile e
i test runtime WebEngine isolati hanno terminato con `0xC0000409`. Stato M1:
**BLOCKED**, non DONE; completare la prova manuale prima di promuoverlo.
