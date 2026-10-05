# Implementation progress

Source of truth: [`IMPLEMENTATION.md`](./IMPLEMENTATION.md).
Repository: `ilfenomeno-gif/jarvis-ultimate`.

## M0 — Repository discovery and baseline

Stato: DONE
Branch: `feat/m00-repo-discovery`
File toccati: `IMPLEMENTATION.md` (copiato senza modifiche), `docs/REPO_MAP.md`,
`docs/impl/M00-discovery.md`, `PROGRESS.md`, `OPEN_QUESTIONS.md`
Verifica: PASS — documentazione controllata; baseline eseguita prima delle
modifiche. Python 3.13.7, Qt 6.11.2, PyQt6 6.11.0 su Windows. Jarvis è rimasto
avviato, la finestra `JARVIS — MARK LII` è stata enumerata, discovery plugin:
18 attivi / 0 rifiutati; GEV pronto e MCP con 30 tool. Warning preesistenti:
contesto DPI Qt non modificabile, output audio saltato e connessione Gemini
ancora in corso durante la finestra di osservazione.
Convalida: PASS — tutte le ipotesi richieste sono classificate e documentate
con i percorsi reali in `docs/REPO_MAP.md`.
Problemi aperti: la connessione Gemini e il percorso audio non sono stati
validati end-to-end in questa baseline; consultare `OPEN_QUESTIONS.md`.
Recap: struttura reale, entry point, UI Qt, stack GEV, registrazione strumenti
Gemini e plugin sono stati mappati. Il documento guida è stato confrontato
byte-per-byte con la copia nella root.

## M1 — Browser integrato

Stato: BLOCKED
Branch: `feat/m01-integrated-browser`
File toccati: `docs/impl/M01-integrated-browser.md`, `core/browser_url.py`,
`tests/test_browser_url.py`, `ui.py`, `main.py`, `tests/fixtures/`,
`tests/serve_fixtures.py`, `tests/test_fixtures.py`, `PROGRESS.md`
Verifica: PASS — suite cumulativa M1-M3 115/115, test fixture 4/4,
compileall helper, Problems/Pylance e `git diff --check` senza errori. Server
loopback smoke: 5 pagine HTTP 200; pagina lunga >=500 parole.
Convalida: BLOCKED — fixture HTTP locale aggiunta, ma non è stata aperta
nell'app: nessun processo Jarvis era attivo e la connessione Gemini non è stata
verificata. I precedenti harness Qt/WebEngine isolati avevano terminato con
`0xC0000409`.
Problemi aperti: navigazione, cronologia, chiusura e redirect da provare nella
finestra Jarvis con server `tests/serve_fixtures.py`.
Recap: browser integrato e fixture deterministiche pronti; non dichiarata DONE
senza evidenza funzionale nell'app.

## M2 — Interazione attiva

Stato: BLOCKED
Branch: `feat/m02-web-interaction`
File toccati: `core/browser_interaction.py`,
`tests/test_browser_interaction.py`, `ui.py`, `main.py`,
`docs/impl/M02-web-interaction.md`, `tests/fixtures/snake.html`,
`tests/fixtures/page_simple.html`, `tests/serve_fixtures.py`, `PROGRESS.md`
Verifica: PASS — suite cumulativa M1-M3 115/115, compileall helper,
Pylance/Problems senza errori, `git diff --check` pulito; fixture link/Snake
servite HTTP 200.
Convalida: PASS parziale per whitelist, JSON escaping, signal Qt e fallback
quando il dispatch JS fallisce; Snake, click link, fallback su gioco reale e
smoke GEV restano BLOCKED.
Problemi aperti: manca una sessione Jarvis/Gemini attiva e osservabile.
Recap: interazione implementata e fixture Snake/link disponibili; non
dichiarato DONE senza evidenza live.

## M3 — Screen reader personale

Stato: BLOCKED
Branch: `feat/m03-screen-reader`
File toccati: `core/page_reader.py`, `core/accessibility.py`, `ui.py`, `main.py`,
`tests/test_page_reader.py`, `docs/impl/M03-screen-reader.md`,
`docs/REPO_MAP.md`, `OPEN_QUESTIONS.md`, `PROGRESS.md`,
`tests/fixtures/page_long.html`, `tests/fixtures/page_empty.html`,
`tests/serve_fixtures.py`, `tests/test_fixtures.py`
Verifica: PASS — suite cumulativa M1-M3 115/115, compileall helper,
Pylance/Problems senza errori, `git diff --check` pulito; import main PASS con
37 tool univoci; pagina lunga verificata >=500 parole.
Convalida: PASS parziale per testo vuoto/enorme, segmentazione, worker, stop
fake, callback Qt e gate audio; BLOCKED per voce live e sovrapposizione reale.
Problemi aperti: non ci sono ancora prove audio/WebEngine live; `pyttsx3` è
installato ma il backend audio host non aveva prodotto audio nella baseline.
Recap: aggiunte fixture lunga/vuota (oltre 500 parole nella lunga); non
dichiarato DONE senza ascolto nel Jarvis reale.

## M4 — Integrazione NVIDIA

Stato: BLOCKED
Branch: `feat/m04-moonlight-sunshine` (separato; non attivo in questo ciclo)
File toccati: implementazione Moonlight provvisoria già presente nel branch
separato; nessun file M4 modificato in questo ciclo.
Verifica: non applicabile
Convalida: BLOCKED per scelta non ricevuta e prerequisiti Moonlight/Sunshine
assenti.
Problemi aperti: scelta A/B/C richiesta in `OPEN_QUESTIONS.md`; branch
Moonlight preesistente non confermato né unito.
Recap: M4 saltata secondo STEP 0; nessuna scelta è attribuita all'utente.

## Prossimo passo

M0 DONE; M1–M3 BLOCKED in attesa delle convalide nell'app. `.env` non presente;
il repository usa `config/api_keys.json` e il campo chiave è configurato, ma
non sono state verificate via richiesta autenticata la chiave o l'accessibilità
del modello. La documentazione pubblica elenca ancora il modello 2.5 Live
configurato, quindi non è stata fatta una modifica speculativa. M4 è stata
saltata: attendere la scelta A/B/C.
