# Open questions

## M0 — Baseline

- La finestra Jarvis e il plugin GEV sono stati osservati all'avvio; la
  connessione Gemini era ancora in stato `Connecting...` al termine
  dell'osservazione. Il backend audio MME ha segnalato che l'output host non
  produceva audio e lo ha saltato. Ripetere una verifica funzionale vocale/audio
  dopo i cicli UI; non si presume che l'audio funzioni.
- Qt ha emesso `SetProcessDpiAwarenessContext() failed: Accesso negato`; la
  finestra è stata comunque enumerata e il processo è rimasto attivo. Registrato
  come warning baseline, da distinguere da eventuali regressioni.

## M4 — Scelta integrazione NVIDIA (bloccante)

Prima di implementare M4, indicare quale direzione desidera:

- **A — G-Assist:** ponte tra Jarvis e NVIDIA G-Assist; richiede che G-Assist
  sia installato e configurato.
- **B — Moonlight/Sunshine:** Jarvis avvia Moonlight e seleziona/avvia giochi;
  verificare disponibilità di Sunshine lato host (NVIDIA GameStream è dismesso).
- **C — Altro:** descrivere l'integrazione desiderata (overlay, registrazione,
  metriche prestazioni o altro).

**Domanda:** quale opzione scegliere per M4: A, B o C? Per C specificare il
risultato atteso.

Stato: BLOCKED fino alla risposta; nessun codice NVIDIA viene implementato in
anticipo.

## M1 — Convalida browser integrato (bloccante)

- L'app Jarvis aggiornata si avvia e il plugin GEV/MCP è pronto, ma Gemini Live
  resta in `Connecting...`; il comando testuale controllato non raggiunge il
  dispatch tool.
- Tre harness Qt/WebEngine isolati sono terminati con codice nativo Windows
  `0xC0000409` prima di produrre risultati.
- I test unitari coprono parsing URL, allow-list, signal wrapper e ripristino
  stack simulato; non provano il caricamento HTTP reale né cronologia.

**Domanda:** appena la sessione Gemini è collegata o il runtime Qt/WebEngine è
disponibile per test interattivi, verificare nel Jarvis i criteri browser in
`docs/impl/M01-integrated-browser.md` (YouTube/example.com, back/forward/reload,
close e rifiuto schemi). Non servono nuove chiavi o modifiche a `.env` per
implementazione; non registrare segreti nei log.

Stato: BLOCKED; il codice resta committato in branch M1 ma la meccanica non è
DONE.

## M2 — Convalida interazione browser (bloccante)

- I test automatici verificano whitelist, payload JavaScript JSON-escaped,
  wrapper signal, schema tools e fallback `QTest` quando il dispatch JavaScript
  fallisce.
- Non è stato verificato il comportamento contro una pagina reale: nessuna
  sessione Jarvis/Gemini era disponibile nel controllo finale; l'uso standalone
  di Qt/WebEngine ha già mostrato un crash nativo Windows `0xC0000409` nel ciclo
  M1.
- Un dispatch JavaScript riuscito non dimostra che un gioco accetti l'evento
  sintetico (`isTrusted=false`); il fallback Qt scatta solo su fallimento del
  dispatch, per evitare doppie pressioni non sicure.

**Azione di convalida futura:** con Jarvis e GEV/browser funzionanti, testare
Snake con freccia su, click su link visibile e pagina che richiede input
`isTrusted`; verificare che link ambiguo/non trovato non venga cliccato.

Stato: BLOCKED; non serve una scelta per proseguire con M3.
