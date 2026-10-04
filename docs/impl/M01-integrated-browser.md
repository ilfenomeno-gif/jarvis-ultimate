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
  QWebEngine browser e GEV restino widget distinti.
- Gemini/tool: declaration `open_website`, dispatch, errore esplicito su input
  invalido e nessuna azione widget fuori dal thread GUI.
- Regression: `pytest` mirato (poi suite Jarvis); GEV lifecycle e test già
  presenti.
- Smoke: avvio Jarvis dopo modifica, finestra e plugin GEV pronti. Audio/Live
  Gemini si riportano solo se effettivamente osservati.

## 5. Criteri di accettazione (checklist PASS/FAIL)

- [ ] "Apri YouTube" carica YouTube in un QWebEngineView dentro Jarvis.
- [ ] `example.com` apre una pagina nel browser integrato.
- [ ] Indietro, avanti, ricarica e chiudi funzionano; chiudi ripristina la vista
  precedente.
- [ ] `file://`, `javascript:`, `data:`, FTP e schemi non HTTP(S) sono rifiutati.
- [ ] Parametri e testo URL non diventano codice JavaScript eseguibile.
- [ ] GEV rimane isolato e funzionante.
- [ ] Tutte le chiamate widget provenienti dal dispatch attraversano segnali
  Qt e slot GUI.

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
  test focused finale **20/20 PASS**; Pylance syntax e problemi senza errori.
- Convalida: non ancora eseguita.

## 9. Recap finale

Da compilare dopo implementazione, test e convalida di tutti i criteri.
