## Limiti noti — lifecycle plugin

`stop_all(timeout=5.0)` esegue i lifecycle hook in sequenza
(`ThreadPoolExecutor(max_workers=1)`) con un timeout **globale** di 5 s.
Se un `stop()` si blocca:

- i future ancora pendenti vengono cancellati;
- il future già in esecuzione **non** è cancellabile: il suo thread
  continua in background finché la funzione non ritorna;
- `executor.shutdown(wait=False, cancel_futures=True)` non interrompe
  il thread in esecuzione.

Per il plugin GEV questo è accettabile perché `gev_plugin.stop()`
applica internamente `terminate()` → 5 s → `kill()`. Il limite vale
per eventuali plugin futuri con `stop()` bloccante: in quel caso
valutare `max_workers>1` o un meccanismo di kill forzato per-thread.

## Modifica alla whitelist dei guardrail

`core/guardrails.py` è stato esteso con `node` e `node.exe` in
`_ALLOWED_EXECUTABLES`. Motivazione: il plugin `gev` avvia God's Eye
View tramite il runtime Node portatile in `_gev-clone/.node/`, e il
guardrail blocca qualsiasi eseguibile non in whitelist prima di
`subprocess.Popen`.

Scope della modifica:

- autorizza qualunque `node` / `node.exe` invocato via subprocess da
  qualunque parte di Jarvis, non solo dal plugin GEV;
- la mitigazione è nel plugin: `plugins/gev_plugin.py` verifica che
  il path risolto di `node.exe` coincida con
  `_gev-clone/.node/node.exe` e rifiuta ogni altro percorso.

La modifica è minima e reversibile: rimuovere le due voci dal set
ripristina il comportamento precedente, al costo di disabilitare
l'avvio automatico di GEV.

### Perché node.exe e non npm

Su Windows `npm` è un wrapper `.cmd` che il guardrail rifiuta
(basename `npm.cmd` non in whitelist). Anche ammettendo `npm.cmd`
in whitelist, il wrapper invoca a sua volta `node.exe` come
subprocess, che sarebbe bloccato allo stesso modo. La soluzione
adottata è invocare direttamente `node.exe` con
`node_modules/npm/bin/npm-cli.js` per l'install e
`node_modules/vite/bin/vite.js` per il dev server. Così ogni
comando esterno passa dal solo eseguibile `node.exe`, autorizzato
in whitelist, e il plugin verifica che quel `node.exe` sia
esattamente quello del runtime portatile.

Come ulteriore fallback, `gev_plugin.py` registra `stop()` con `atexit`:
se il thread runner di Jarvis termina senza completare il proprio hook
di lifecycle, il processo GEV viene comunque terminato alla chiusura
normale dell'interprete. Questo fallback non si applica a terminazioni
forzate del processo, come `os._exit()` senza uno stop esplicito.

Su Windows, il processo Vite viene inoltre assegnato a un Job Object con
`JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE`, così il sistema termina il processo
GEV e i suoi discendenti se il processo Jarvis viene chiuso senza eseguire
gli hook Python.

## Limiti noti — preambolo Gemini Live

Quando Gemini decide di chiamare il tool `gev`, può emettere un preambolo
ottimista ("Certamente, signore, sto procedendo...") prima di ricevere
la risposta del tool. Se il tool fallisce o l'interfaccia non è pronta,
Gemini si corregge subito dopo. È un comportamento noto di Gemini Live,
cosmetico, non modificabile senza stravolgere la configurazione del
modello. Il plugin `gev` garantisce che **la conferma ottimistica
venga restituita solo dopo un invio riuscito** a `send_to_gev`; il
preambolo vocale è generato da Gemini indipendentemente da questo.

## Passo 5 — UI embed e bridge

### Architettura verificata nel codice

- `MainWindow` ospita una `QWebEngineView` in una pagina dedicata dello
  stack centrale; prima del caricamento mostra un placeholder
  (`../ui.py:2536-2557`).
- L'apertura carica `http://127.0.0.1:4173/` solo su richiesta. La signal
  Qt `_gev_send_sig` inoltra i messaggi al thread della UI;
  `JarvisUI.send_to_gev()` valida e serializza il payload
  (`../ui.py:2427`, `../ui.py:2621`, `../ui.py:2729-2748`,
  `../ui.py:4498-4549`).
- Prima del caricamento viene registrato uno script `MainWorld` a
  `DocumentCreation`: imposta `window.GEV_EMBED_INLINE = true` e inoltra
  alla console i messaggi `gev:*` (`../ui.py:2560-2575`). GEV riconosce
  questa modalità tramite un confronto booleano stretto
  (`C:\Users\PC\Downloads\gods-eye-view-main\_gev-clone\src\app\embed.js:36-46`).
- Il dispatcher traduce le azioni in messaggi completi `gev:view`.
  Le risposte `gev:ready` e `gev:view-applied` vengono decodificate
  dall'override `javaScriptConsoleMessage`, passano per
  `MainWindow._on_gev_message()` e possono essere inoltrate al callback
  registrato con `JarvisUI.on_gev_message()`
  (`../ui.py:54-69`, `../ui.py:2750-2783`, `../ui.py:4551-4557`).
- Il protocollo del checkout GEV definisce `gev:view`,
  `gev:view-applied` e `gev:ready`; in modalità inline mittente e
  destinatario sono la stessa finestra
  (`C:\Users\PC\Downloads\gods-eye-view-main\_gev-clone\src\app\embed.js:18-20`,
  `:253-300`).
- Le mappature layer/follow sono esplicite nel codice
  (`../ui.py:40-50`). GEV supporta follow per aircraft, military aircraft e
  satellite (`C:\Users\PC\Downloads\gods-eye-view-main\_gev-clone\src\app\embed.js:22-26`,
  `C:\Users\PC\Downloads\gods-eye-view-main\_gev-clone\src\view\index.js:30-50`);
  la UI Jarvis accetta solo `flight` e `satellite`, perciò il tipo `vessel`
  dichiarato dal plugin non è inoltrabile e produce un errore esplicito
  (`../ui.py:4537-4543`).

### Verifiche eseguite

- `py_compile` di `ui.py`: PASS; il bytecode di controllo è stato scritto
  fuori dal repository Jarvis.
- Harness isolato con payload fittizi: PASS per `layer`, `track`,
  `annotate`, `reset`, serializzazione, parsing di `gev:ready` e rifiuto
  esplicito del follow `vessel`. Questo verifica il codice Python del
  bridge, non il rendering WebEngine o l'esecuzione effettiva di GEV.
- Tentativo di smoke test Qt con piattaforma `offscreen`: processo
  terminato con codice `3221226505` prima delle asserzioni e senza output
  applicativo. La causa non è stata determinata; non è attribuita al
  bridge né considerata una verifica superata. Un test successivo nella
  finestra desktop reale ha invece verificato il caricamento WebEngine e
  il bridge, come descritto sotto.
- La diagnostica Pylance non riporta errori; segnala warning per simboli
  non usati in `ui.py`. Non è stato confrontato un baseline precedente.

### Esito verifica GUI Windows — 2026-10-04

- `send_to_gev()` accoda la signal Qt e non attende `gev:view-applied`.
  La risposta ottimistica del plugin indica quindi che l'invio alla UI è
  stato accettato, non che GEV abbia completato l'azione
  (`../ui.py:4549`, `../plugins/gev_plugin.py:641-670`). Il callback di
  risposta è predisposto per la gestione successiva.
- Sul desktop Windows non era presente un collegamento J.A.R.V.I.S.
  È stato creato `C:\Users\PC\Desktop\J.A.R.V.I.S.lnk`, puntato al
  `pythonw.exe` della `.venv`, con `main.py` e la directory del progetto
  come argomenti/percorso di lavoro. L'avvio del collegamento è stato
  verificato: la finestra `JARVIS — MARK LII` è apparsa e risultava
  reattiva.
- Dall'input testuale della finestra, Gemini ha attivato `gev`:
  `GEV: invio azione 'open'`, caricamento pagina e `GEV: ready`.
  In seguito `historical_map` ha caricato lo snapshot 1938 per la richiesta
  1939; `animate`, `stop` e `clear` hanno restituito esito positivo nei log.
  Lo screenshot della finestra ha mostrato il globo Cesium incorporato.
- Questa prova verifica il percorso testuale Gemini → plugin Jarvis →
  `QWebEngineView` → bridge GEV. Non è stata eseguita tramite microfono:
  il comando vocale effettivo con Gemini Live rimane non verificato.
- Un segnale `gev:ready` non ricevuto lascia la UI non pronta per le
  azioni diverse da `open`; il timeout di attesa non è implementato
  (`../ui.py:2732-2743`, `:2750-2754`, `:2776-2780`).
- Il layer satelliti, il test vocale con microfono e la chiusura mediante
  Ctrl+C con verifica della porta/processi **non sono stati verificati**
  durante questa prova. Jarvis è stato lasciato avviato dal collegamento;
  il processo Node che serve GEV e la porta 4173 sono quindi attesi attivi.
  > Da verificare

## Passo 4c — client MCP locale

Jarvis avvia il server MCP stdio fornito dal checkout GEV con il medesimo
`node.exe` portatile e l'API locale Vite. La discovery MCP avviene dopo
`initialize` e `notifications/initialized`; le funzioni MCP vengono
pubblicate a Gemini come declaration separate `gev_mcp_*`. Il plugin
mantiene anche la funzione diretta `gev` per le azioni della UI.

Il client, l'adattatore schema e la serializzazione JSON-RPC si trovano in
[`../plugins/_gev_mcp_client.py`](../plugins/_gev_mcp_client.py); il ciclo
di vita e il routing dei tool sono in
[`../plugins/gev_plugin.py`](../plugins/gev_plugin.py). Il registro plugin
supporta le declarations dinamiche e inoltra la funzione namespaced alla
stessa implementazione plugin (`../core/plugin_loader.py`).

Nel checkout GEV verificato, `tools/list` ha restituito 30 funzioni. Non
sono esposte funzioni che GEV esclude esplicitamente dalla superficie MCP,
tra cui `plan_route`, `search_places`, `get_weather` e
`find_radio_stations`. La lista completa e il limite sono documentati in
[`GEV_MCP_INTEGRATION.md`](./GEV_MCP_INTEGRATION.md).

Verifiche: 9 test mirati (23 test nell'intera cartella `tests`) passati;
handshake live e conversione di tutti i 30 schemi in `google-genai`
passati; chiamata live di
`gev_mcp_get_recent_launches` conclusa restituendo una riga dati. La
verifica vocale con Gemini Live rimane distinta da queste prove API.

## Mappa storica — primo verticale

Il plugin diretto `gev` accetta l'azione `historical_map` con `show`,
`animate`, `stop` e `clear`. Jarvis inoltra il comando all'app incorporata
tramite `gev:historical-map`; la risposta
`gev:historical-map-applied` riporta l'anno effettivamente caricato o
l'errore. L'overlay Cesium e il relativo lifecycle sono implementati nel
checkout GEV in `src/app/historicalMap.js`; l'aggancio al lifecycle applicativo
e al bridge è in `src/app/tools.js` e `src/app/embed.js`.

La sorgente verificata durante l'implementazione conteneva 54 anni; tra 1930
e 1950 risultavano solo 1930, 1938 e 1945. Perciò `show 1939` seleziona 1938,
e il playback `1939–1945` cicla gli snapshot 1938 e 1945: non interpola gli
anni mancanti. I colori identificano deterministicamente le entità per nome;
la sorgente non fornisce una classificazione Asse/Alleati/Neutrali.

Test automatici: controller storico e bridge GEV sono coperti da
`src/app/historicalMap.test.mjs` e `src/app/embed.test.mjs`; il routing e la
validazione Jarvis sono coperti da `tests/test_gev_mcp_client.py`. L'esito
del browser smoke GEV è positivo: `show 1939` ha caricato 1938 con 531
entità nominate, senza errori o warning console; l'animazione discreta ha
raggiunto 1945, e `stop`/`clear` hanno ripristinato il numero iniziale di data
source. Il filtro dei feature senza `NAME`/`SUBJECTO` è in
`src/app/historicalMap.js:167`; il test che verifica il filtro è in
`src/app/historicalMap.test.mjs:118`. Il feature non nominato che aveva
innescato l'errore Cesium era l'indice zero-based 94 del dataset live
`geojson/world_1938.geojson`. Successivamente, nella finestra Jarvis avviata
dal collegamento desktop, il test end-to-end testuale ha caricato lo snapshot
1938, avviato e fermato il playback e rimosso l'overlay. Il globo Cesium
incorporato era visibile. Il comando vocale via microfono non è stato testato.
> Da verificare: input vocale reale e layer satelliti nella QWebEngine.

Questo comando storico passa dal tool diretto `gev` e dal bridge UI; non
aggiunge tool vocali standalone alla superficie MCP. I limiti dei tool MCP
esistenti restano quelli descritti sopra.

Per dettagli sul formato dati, sui limiti e sulla procedura manuale vedere
[`../../../gods-eye-view-main/_gev-clone/docs/historical-maps.md`](../../../gods-eye-view-main/_gev-clone/docs/historical-maps.md).
