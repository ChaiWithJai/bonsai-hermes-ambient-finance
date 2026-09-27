# Choose settings for the task you need to complete

The reference configuration makes a 27B model available to a local agent with a limited set of business tools. The application supplies the source records, checks the calculation or write, and saves a result that a person can inspect. Sampling controls how the model generates its next token; it does not enforce agreement terms, portfolio constraints or correct persistence.

## Start with the publisher's settings

The [Bonsai model card](https://huggingface.co/prism-ml/Ternary-Bonsai-2-27B-gguf#best-practices) recommends a thinking-mode sampling profile and medium reasoning for shorter responses. The reference uses that profile and PQ2_0, the packing measured on Apple Silicon in the card. Use the matching Prism runtime because the model requires its ternary kernels.

| Parameter | Reference value | What it controls and why it is here |
| --- | --- | --- |
| Temperature | `1.0` | Changes the relative likelihood of candidate tokens. Lower values concentrate choices; this value preserves the publisher's thinking-mode baseline. It is not a legal or finance accuracy setting. |
| Top-p | `0.95` | Restricts token selection by cumulative probability. |
| Top-k | `20` | Restricts selection to the highest-ranked candidate tokens. |
| Min-p | `0.05` | Filters tokens relative to the most likely token. |
| Presence / repetition penalty | `0.0` / `1.0` | Leaves these repetition penalties neutral, following the publisher profile. |
| Reasoning effort | `medium` | Requests the model's shorter reasoning mode through its template. |
| Reasoning budget | `512` tokens | Caps reasoning at the runtime level; too small a budget can interrupt useful analysis. |
| Context | `65,536` tokens | Provides space for instructions, tool definitions, source text and conversation. Larger context uses additional memory and permits more prompt work. |
| Parallel slots | `1` | Runs one serving slot for this demonstration; additional throughput needs a measured concurrency test. |
| GPU offload / template | `-ngl 99`, `--jinja` | Requests GPU offload and uses the model's chat template for structured conversation and tool calls. |

The [llama.cpp server reference](https://github.com/ggml-org/llama.cpp/tree/master/tools/server#readme) documents runtime and sampler behavior. Several filters act together, so changing temperature alone does not describe the complete sampling policy. Confirm the effective HTTP request as well as startup flags, since a client can override server defaults.

## What was observed

The managed scheduled run saved a 197-word review that identified stale research and requested an owner and update date. The proxy caps responses at 1,536 tokens. Its one-attempt recovery path for a reasoning-only response has separate test evidence; the successful managed run does not exercise that branch. See [the scheduled run](../evidence/managed-launchd-20260927/README.md) and [source reading](source-reading.md).

The [configuration capture](recorded-configuration.md) provides the installed profile fields and available request settings. It is a reference view generated from those records. The current evidence supports reproducing the configuration; it does not establish a domain-specific fine-tune or a best setting across competing configurations.

## Tune against a completed task

For a scheduled review, acceptance means current prices, reproducible calculations, correct report citations, visible stale research and a saved final answer. Include missing report files and interrupted work. A clean process exit with no durable final answer fails.

Freeze the source snapshot, model hash, runtime revision and tool definitions before comparing configurations. Change one setting at a time, repeat the same requests, and inspect both successful and failed outputs. Record end-to-end time, all model calls and tokens, peak memory, retries and human corrections alongside task acceptance. Prefer the configuration that completes acceptable work at the required latency and cost, rather than the one that merely emits tokens fastest.

Start with unnecessary tool turns and excessive source text, then test reasoning budget and context size. If you test a different sampling profile, retain the same acceptance cases. Reducing a limit can lower work per request while increasing retries, so measure the entire task.
