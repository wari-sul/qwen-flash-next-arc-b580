# 09. On-demand loading and running two models on one card

## Load on demand, unload when idle

I did not want 47 GB of host RAM locked around the clock for a model I use a few hours a day. Strata's server supports Ollama-style behaviour through two keys in the run config:

```json
"lazy_load": true,
"idle_unload_s": 1200
```

- With `lazy_load`, `strata serve` starts the HTTP server immediately but does not load the model. `/health` answers, and the container can start at boot without touching the GPU or pinning any memory.
- The first request triggers the load. The client simply waits: the expert mirror takes about 13 s to pin and the whole load is roughly a minute here.
- After 20 minutes without requests the model unloads and the pinned memory goes back to the host. I verified the host returning to about 58 GB available after an unload.

Manual control:

```
curl -s -X POST -H "Authorization: Bearer <API_KEY>" http://127.0.0.1:8080/load
curl -s -X POST -H "Authorization: Bearer <API_KEY>" "http://127.0.0.1:8080/unload?wait=300"
curl -s http://127.0.0.1:8080/health          # contains "loaded": true / false
```

`strata profile set` rejected these keys in 0.2.3, so I edit the JSON file directly.

## Two models, one GPU, one rule

A single `strata serve` instance serves one model. There is no model switching inside one server (I checked the code and the 0.2.3.1 release notes). So I run two services:

| Service | Port | Model | Pinned RAM |
|---|---|---|---|
| `strata.service` | 8080 | DavidAU IQ3_S | ~47 GiB |
| `strata-coder.service` | 8081 | ISTA Coder IQ1_M | ~23 GiB |

Both lazy-load. The rule is that **only one may be loaded at a time**: both together would pin about 70 GiB on a 62 GiB host.

Strata has a `before_load` hook that runs a command before every load. Each service points it at the *other* port:

```json
"before_load": ["/usr/local/bin/strata-unload-peer", "8081", "/etc/strata/coder-iq1m-256k.json"],
"before_load_timeout_s": 330,
"before_load_strict": true
```

[strata-unload-peer](../configs/bin/strata-unload-peer) asks the peer to unload (waiting up to 300 s for in-flight requests), then polls the peer's `/health` until it reports `"loaded": false`. It exits 0 only if the peer is unloaded or not running. With `before_load_strict`, a failed hook blocks the load, so the two models can never be pinned at the same time.

In practice: send a request to `:8081` while `:8080` is loaded, and the Coder service unloads DavidAU first, then loads itself. The client sees one slow first response, then normal speed.

If you want a single endpoint, put a small reverse proxy in front that routes on the `model` field. I did not need one.

## Start at boot

Both units are `enabled`. Because of `lazy_load`, starting them at boot only starts two idle HTTP servers. Nothing is pinned until a request arrives.
