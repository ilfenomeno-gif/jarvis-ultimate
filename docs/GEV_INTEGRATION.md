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
