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
`tests/test_browser_url.py`, `ui.py`, `main.py`, `PROGRESS.md`
Verifica: PASS parziale — suite 73/73, compileall, syntax/Pylance; smoke app
con finestra Jarvis e GEV/MCP pronto.
Convalida: BLOCKED — nessuna navigazione browser verificabile; Gemini è rimasto
`Connecting...` e tre harness Qt/WebEngine hanno terminato con `0xC0000409`.
Problemi aperti: serve sessione Live attiva o verifica interattiva WebEngine per
YouTube/example.com, history e redirect.
Recap: implementata vista browser separata, signal Qt, tool Gemini e allow-list
HTTP(S); non dichiarata DONE senza evidenza funzionale.

## M2 — Interazione attiva

Stato: BLOCKED
Branch: `feat/m02-web-interaction`
File toccati: `core/browser_interaction.py`,
`tests/test_browser_interaction.py`, `ui.py`, `main.py`,
`docs/impl/M02-web-interaction.md`, `PROGRESS.md`
Verifica: PASS — suite completa 99/99, compileall modificati, Pylance/Problems
senza errori, `git diff --check` pulito.
Convalida: PASS parziale per whitelist, JSON escaping, signal Qt e fallback
quando il dispatch JS fallisce; interazione live Snake/link, fallback quando
un gioco ignora silenziosamente l'evento e smoke GEV restano BLOCKED.
Problemi aperti: manca una sessione Jarvis/Gemini utilizzabile; il runtime
WebEngine live resta bloccato dal crash nativo già rilevato in M1.
Recap: implementati `press_key`/`click_link` per il browser integrato; non
dichiarato DONE senza evidenza live.

## M3 — Screen reader personale

Stato: BLOCKED
Branch: `feat/m03-screen-reader`
File toccati: `core/page_reader.py`, `core/accessibility.py`, `ui.py`, `main.py`,
`tests/test_page_reader.py`, `docs/impl/M03-screen-reader.md`,
`docs/REPO_MAP.md`, `OPEN_QUESTIONS.md`, `PROGRESS.md`
Verifica: PASS — suite completa 111/111, compileall file M3, Pylance/Problems
senza errori, `git diff --check` pulito; import main PASS con 37 tool univoci.
Convalida: PASS parziale per testo vuoto/enorme, segmentazione, worker,
stop fake, callback Qt e gate audio. BLOCKED per voce live, interazione browser
e conflitto audio sul dispositivo reale.
Problemi aperti: output audio host non produceva audio nella baseline; M1
browser/Gemini live è tuttora bloccato. `pyttsx3` è installato, ma non si è
eseguito TTS reale né si è stampata/modificata alcuna credenziale.
Recap: letto DOM in callback async, max 20.000 caratteri/chunk <=800, pyttsx3
in worker con event loop esterno e stop sullo stesso thread; l'audio Gemini
viene drenato durante la lettura. Non dichiarato DONE senza prova audio reale.

## M4 — Integrazione NVIDIA

Stato: BLOCKED
Branch: non creato
File toccati: nessuno
Verifica: non applicabile
Convalida: non applicabile
Problemi aperti: scelta utente richiesta; domanda e opzioni in
`OPEN_QUESTIONS.md`.
Recap: nessuna implementazione prima di una risposta esplicita.

## Prossimo passo

M0–M3 sono DONE o BLOCKED; attendere scelta utente M4. Riprendere i criteri
live M1–M3 quando browser, sessione Gemini e output audio sono disponibili.
