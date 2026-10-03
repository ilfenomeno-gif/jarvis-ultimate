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
