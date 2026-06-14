<div align="center">

# Airforce API SDKs

**Official client libraries for the [api.airforce](https://api.airforce) AI gateway.**

One OpenAI-compatible API in front of many model providers — with usage-based billing,
smart routing, provider fallback, and media generation.

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![OpenAI compatible](https://img.shields.io/badge/API-OpenAI%20compatible-412991.svg)](docs/API_SURFACE.md)
[![Languages](https://img.shields.io/badge/languages-TS%20%7C%20Python%20%7C%20Go%20%7C%20Java-success.svg)](#languages)

</div>

---

## Why this SDK

`api.airforce` speaks the **OpenAI, Anthropic and Gemini** wire formats, so you can point an
existing client at it — but these SDKs add the gateway-specific power on top:

- 🔁 **Provider fallback** — pass a `models` array; the gateway routes to the first healthy
  model and bills only the one that answers.
- 🧭 **Smart routing** — public model names resolve to the best concrete provider; per-key
  channel/category preferences are respected.
- 🌊 **Streaming** — chat, messages, responses, gemini and video, exposed as native
  iterators in every language.
- 🎨 **Media** — image, audio (TTS / music / SFX / transcription / dubbing), video and voice
  cloning.
- 👤 **Full account surface** — usage, billing, API-key provisioning, 2FA, OAuth.
- 💸 **Usage & cost** — every response carries a `usage.cost` in credits.

## Languages

| Language | Directory | Package | Runtime |
| --- | --- | --- | --- |
| **TypeScript / JavaScript** | [`typescript/`](typescript/) | `@api-airforce/sdk` | Node 18+ · browsers · edge |
| **Python** (sync + async) | [`python/`](python/) | `airforce-api` | Python 3.8+ · httpx |
| **Go** | [`go/`](go/) | `github.com/ApiAirforce/api-airforce-sdk/go` | Go 1.21+ · stdlib only |
| **Java** | [`java/`](java/) | `com.airforce:airforce-api` | JDK 11+ · Jackson |
| **C# / .NET** | [`csharp/`](csharp/) | `Airforce` (NuGet) | .NET 8 · HttpClient |
| **Rust** | [`rust/`](rust/) | `airforce` (crates.io) | reqwest · Tokio |
| **Dart** | [`dart/`](dart/) | `airforce` (pub.dev) | Dart VM · Flutter |
| **PHP** | [`php/`](php/) | `api-airforce/sdk` (Composer) | PHP 8.1+ · cURL |

> **Status:** all eight implement the shared [API contract](docs/API_SURFACE.md) and ship a
> passing test suite. Not yet published to the package registries.

## Quickstart

The same request in every language — get an API key from your
[dashboard](https://api.airforce) and set `AIRFORCE_API_KEY`.

<details open>
<summary><b>TypeScript</b></summary>

```ts
import { Airforce } from "@api-airforce/sdk";

const airforce = new Airforce({ apiKey: process.env.AIRFORCE_API_KEY });
const res = await airforce.chat.create({
  model: "claude-opus-4.8",
  messages: [{ role: "user", content: "Hello!" }],
});
console.log(res.choices[0]?.message.content);
```

</details>

<details>
<summary><b>Python</b></summary>

```python
from airforce import Airforce

client = Airforce()  # reads AIRFORCE_API_KEY
res = client.chat.create(
    model="claude-opus-4.8",
    messages=[{"role": "user", "content": "Hello!"}],
)
print(res["choices"][0]["message"]["content"])
```

</details>

<details>
<summary><b>Go</b></summary>

```go
client := airforce.New() // reads AIRFORCE_API_KEY
res, _ := client.Chat.Create(ctx, airforce.ChatCompletionParams{
    Model:    "claude-opus-4.8",
    Messages: []airforce.ChatMessage{{Role: "user", Content: "Hello!"}},
})
fmt.Println(res.Choices[0].Message.Content)
```

</details>

<details>
<summary><b>Java</b></summary>

```java
Airforce client = Airforce.builder().build(); // reads AIRFORCE_API_KEY
JsonNode res = client.chat().create(Map.of(
    "model", "claude-opus-4.8",
    "messages", List.of(Map.of("role", "user", "content", "Hello!"))));
System.out.println(res.get("choices").get(0).get("message").get("content").asText());
```

</details>

See each language's `README.md` for streaming, media, account, billing and OAuth examples.

## Core concepts

| Concept | How it works |
| --- | --- |
| **Auth** | `Authorization: Bearer <api-key>` for `/v1/*`; account/billing endpoints use a session token (adopted automatically after `auth.login()`). |
| **Streaming** | Streaming methods return an iterator of typed events; iteration stops at the `[DONE]` sentinel. |
| **Fallback** | Add `models: [...]` (up to 3) for automatic cross-provider failover. |
| **Errors** | Typed errors per status (`401`, `402`, `403`, `404`, `409`, `429`, `5xx`) plus connection/timeout. |
| **Retries** | Automatic retry with backoff on `429` / `5xx` / network errors (configurable). |
| **Money** | Balances and quotas are in **cents**; `usage.cost` is in **credits (USD)**. |

The full endpoint reference lives in [`docs/API_SURFACE.md`](docs/API_SURFACE.md).

## Repository layout

```text
api-airforce-sdk/
├── docs/
│   └── API_SURFACE.md     # the shared, language-agnostic contract
├── typescript/            # @api-airforce/sdk
├── python/                # airforce-api  (sync + async)
├── go/                    # Go module
├── java/                  # Java / Maven artifact
├── csharp/                # Airforce (.NET)
├── rust/                  # airforce crate
├── dart/                  # airforce (Dart / Flutter)
└── php/                   # api-airforce/sdk (Composer)
```

## Development

Each SDK builds and tests independently:

```bash
# TypeScript
cd typescript && npm install && npm test && npm run build

# Python
cd python && pip install -e ".[dev]" && pytest

# Go
cd go && go test ./...

# Java
cd java && mvn test

# C#
cd csharp && dotnet test

# Rust
cd rust && cargo test

# Dart
cd dart && dart pub get && dart test

# PHP
cd php && php tests/run.php
```

## Contributing

All four SDKs implement the same surface from [`docs/API_SURFACE.md`](docs/API_SURFACE.md).
When the API changes, update the contract first, then mirror the change across every
language and keep each test suite green.

## License

Released under the [MIT License](LICENSE).
