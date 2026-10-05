# Open questions

## Gemini — connessione Live (blocco trasversale M1-M3)

- `.env` non è presente. Il repository carica la credenziale da
  `config/api_keys.json`; verifica locale non espositiva: file JSON valido e
  campo `gemini_api_key` non vuoto. Nessun valore è stato letto o stampato.
- La chiamata diretta autenticata a Gemini non è stata eseguita: validità
  della chiave e accessibilità del modello non sono confermate. Non dichiarare
  la chiave scaduta senza un errore di autenticazione osservato; se Jarvis lo
  mostra, l'utente deve rigenerarla.
- Il modello Live configurato nel sorgente è
  `models/gemini-2.5-flash-native-audio-preview-12-2025`. Non c'era un processo
  Jarvis attivo né un log recente `JARVIS online`; disponibilità corrente del
  modello non verificata tramite una sessione autenticata. La documentazione
  pubblica Gemini lo elenca ancora tra i modelli Live e non lo marca come
  deprecato; raccomanda Gemini 3.8 Live come default per nuove integrazioni.
  Fonte: https://ai.google.dev/gemini-api/docs/models e
  https://ai.google.dev/gemini-api/docs/live-api/capabilities.
- Per riprovare: avviare Jarvis e controllare localmente la connessione senza
  copiare chiavi o log che le contengano. Se il log riporta modello non
  disponibile, aggiornare a un modello Live stabile supportato e annotare il
  cambio in `PROGRESS.md`.

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
anticipo in questo branch. L'implementazione Moonlight precedente rimane
isolata in `feat/m04-moonlight-sunshine`, non confermata e non unita; in questo
ciclo M4 è stata saltata.

## M1 — Convalida browser integrato (bloccante)

- La precedente prova dell'app riportava Gemini Live in `Connecting...`, ma
  in questo ciclo non c'era un processo Jarvis attivo. La credenziale è
  configurata nel file locale previsto dal repository; non è stata fatta una
  chiamata autenticata diretta.
- Tre harness Qt/WebEngine isolati erano terminati con codice nativo Windows
  `0xC0000409`; le nuove fixture HTTP locali evitano dipendenze da siti remoti,
  ma non sostituiscono la prova nella finestra Jarvis reale.

**Azione:** avviare Jarvis, verificare localmente `JARVIS online`, quindi
servire `tests/fixtures/` e verificare nell'app i criteri in
`docs/impl/M01-integrated-browser.md` (pagina semplice, link, cronologia e
chiusura). Non registrare segreti nei log.

Stato: BLOCKED; il codice resta committato in branch M1 ma la meccanica non è
DONE.

## M2 — Convalida interazione browser (bloccante)

- I test automatici verificano whitelist, payload JavaScript JSON-escaped,
  wrapper signal, schema tools e fallback `QTest` quando il dispatch JavaScript
  fallisce.
- Le fixture locali esistono, ma non è stato verificato il comportamento in
  una pagina reale: nessuna sessione Jarvis/Gemini era attiva nel controllo.
- Un dispatch JavaScript riuscito non dimostra che un gioco accetti l'evento
  sintetico (`isTrusted=false`); il fallback Qt scatta solo su fallimento del
  dispatch, per evitare doppie pressioni non sicure.

**Azione di convalida futura:** con Jarvis e GEV/browser funzionanti, servire
le fixture e testare Snake, link visibile e fallback su pagina che richiede
input `isTrusted`; verificare che link ambiguo/non trovato non venga cliccato.

Stato: BLOCKED; non serve una scelta per proseguire con M3.

## M3 — Convalida voce screen reader (bloccante)

- I test coprono testo vuoto/lunghissimo, limite di estrazione, chunk <=800,
  worker separato, richiesta stop, engine fake pilotato solo dal thread worker
  e callback che sopprime l'audio Gemini.
- `pyttsx3` è importabile nell'interprete selezionato; il backend audio host
  della baseline però è stato saltato perché non produceva audio. Non è stata
  eseguita sintesi reale, perciò la risposta del dispositivo e l'interruzione
  audio in tempo reale con il driver Windows non sono note.
- Le fixture per testo lungo/vuoto sono disponibili, ma la lettura dipende dal
  browser M1 e da un dispositivo audio funzionante; nessuna prova live è stata
  eseguita.

**Azione di convalida futura:** con audio funzionante e una pagina aperta in
Jarvis, verificare lettura fluida, GUI reattiva, stop entro pochi secondi e
assenza di voce Gemini sovrapposta. Verificare pagina vuota e testo lungo anche
nel browser; i test unitari coprono già le funzioni di limite.

Stato: BLOCKED; nessuna nuova credenziale è richiesta, si può passare alla
scelta M4.
