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

Stato: IN_PROGRESS
Branch: `feat/m01-integrated-browser`
File toccati: `docs/impl/M01-integrated-browser.md`, `core/browser_url.py`,
`tests/test_browser_url.py`, `PROGRESS.md`
Verifica: GO di fattibilità; test URL focused 20/20 PASS.
Convalida: non iniziata.
Problemi aperti: test reale Qt/WebEngine ancora da eseguire.
Recap: browser separato dal GEV, URL HTTP(S) e segnali Qt definiti nel piano.

## M2 — Interazione attiva

Stato: TODO
Branch: `feat/m02-web-interaction`
File toccati: nessuno
Verifica: non iniziata
Convalida: non iniziata
Problemi aperti: nessuno oltre alla diagnosi da completare nel ciclo M2.
Recap: dipende dal browser integrato M1.

## M3 — Screen reader personale

Stato: TODO
Branch: `feat/m03-screen-reader`
File toccati: nessuno
Verifica: non iniziata
Convalida: non iniziata
Problemi aperti: nessuno oltre alla diagnosi da completare nel ciclo M3.
Recap: dipende dal browser integrato M1.

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

Completare implementazione, verifica e convalida M1; poi iniziare M2.
