# 10. Using the API

Strata exposes three API styles on the same port. All `/v1/*` routes need the API key from the run config.

| Endpoint | Style | Notes |
|---|---|---|
| `POST /v1/chat/completions` | OpenAI Chat Completions | Streaming, tools, `reasoning_effort` |
| `POST /v1/responses` | OpenAI Responses | Streaming SSE events (`response.output_text.delta` etc.), reasoning items. Works with Codex-style clients |
| `POST /v1/messages` | Anthropic Messages | Tools (`tool_use` / `tool_result`). Base URL for Anthropic clients is the server root, without `/v1` |
| `GET /v1/models` | OpenAI | |
| `GET /health` | | No key needed. Shows whether the model is loaded |
| `POST /load`, `POST /unload?wait=N` | | Manual load control |

## Examples

Chat Completions:

```
curl -s http://192.168.1.50:8080/v1/chat/completions \
  -H "Authorization: Bearer <API_KEY>" -H "Content-Type: application/json" \
  -d '{"model":"x","messages":[{"role":"user","content":"Write a bash one-liner that prints the 5 largest files under /var/log."}],
       "reasoning_effort":"low","max_tokens":2000,"temperature":0.6,"top_p":0.95,"top_k":20}'
```

The `model` field is ignored (one model per server). The reply has `message.content` and, separately, `message.reasoning_content`.

Responses API:

```
curl -s http://192.168.1.50:8080/v1/responses \
  -H "Authorization: Bearer <API_KEY>" -H "Content-Type: application/json" \
  -d '{"model":"x","input":"Reply with exactly: pong","reasoning":{"effort":"low"},"max_output_tokens":200}'
```

Anthropic Messages with a tool:

```
curl -s http://192.168.1.50:8080/v1/messages \
  -H "x-api-key: <API_KEY>" -H "anthropic-version: 2023-06-01" -H "Content-Type: application/json" \
  -d '{"model":"x","max_tokens":1000,"messages":[{"role":"user","content":"Weather in Berlin, celsius?"}],
       "tools":[{"name":"get_weather","description":"Current weather","input_schema":{"type":"object",
         "properties":{"city":{"type":"string"},"unit":{"type":"string","enum":["c","f"]}},"required":["city","unit"]}}]}'
```

All three styles passed the tool-calling tests in the benchmark ([12-results.md](12-results.md)).

## Reasoning effort

`reasoning_effort` (`low`, `medium`, `high`, `xhigh`) controls how long the model thinks. The default here is the model's own (`xhigh`-like). For coding work:

- `low` is fast and solved most tasks in the benchmark.
- `xhigh` costs 5 to 10 times the tokens. It rescued some hard tasks that `low` failed, and broke at least one that `low` passed. See the results.

## Sampling

The benchmark used `temperature 0.6, top_p 0.95, top_k 20, min_p 0`, which is Qwen's recommended setting for thinking mode.

## Prompt caching (prefix reuse)

Strata keeps the KV cache of the previous request and reuses the longest matching prefix. Test: a 3,403-token system prompt, three different short questions.

| Request | Prompt tokens reused | Wall time |
|---|---|---|
| 1st (cold) | 0 | 6.0 s |
| 2nd | 3,385 | 0.49 s |
| 3rd | 3,385 | 0.49 s |

The reuse is reported in `usage.prompt_tokens_details.cached_tokens`. This is what matters for chat, coding agents and tools: they resend the same growing conversation every turn. It is exact prefix reuse, not a semantic cache, so a changed system prompt or tool list invalidates it.

## Connecting tools

`strata connect <app>` prints ready-made settings for supported clients (for example `strata connect opencode`). For anything OpenAI-compatible, the base URL is `http://<host>:8080/v1` and the key is the Bearer token.
