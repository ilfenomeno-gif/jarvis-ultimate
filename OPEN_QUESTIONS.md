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
