# BugTraceAI Apex G4-26B-Q4 — Kaggle GPU Setup

> One-click setup script to run BugTraceAI Apex G4-26B-Q4 model on Kaggle with dual GPU acceleration (T4 x2), exposed as an Anthropic-compatible API — including a working recipe for connecting Claude Code CLI to it.

[![Kaggle](https://img.shields.io/badge/Kaggle-035a7d?style=for-the-badge&logo=kaggle&logoColor=white)](https://kaggle.com)
[![Python](https://img.shields.io/badge/Python-3.10+-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://python.org)
[![License](https://img.shields.io/badge/License-MIT-blue.svg?style=for-the-badge)](LICENSE)
[![Hugging Face](https://img.shields.io/badge/Hugging%20Face-BugTraceAI-FFD21E?style=for-the-badge&logo=huggingface&logoColor=black)](https://huggingface.co/BugTraceAI)

---

## 📋 Table of Contents

- [Features](#-features)
- [Quick Start](#-quick-start)
- [Configuration](#-configuration)
- [API Usage](#-api-usage)
- [Connecting Claude Code CLI](#-connecting-claude-code-cli)
- [How It Works](#-how-it-works)
- [Requirements](#-requirements)
- [Troubleshooting](#-troubleshooting)
- [Model Information](#-model-information)
- [Security Notes](#-security-notes)
- [Contributing](#-contributing)
- [License](#-license)
- [Credits](#-credits)

---

## ✨ Features

| Feature | Description |
|---------|-------------|
| 🚀 **GPU Detection** | Automatically detects and configures T4 x2 GPUs |
| 📦 **Self-Contained** | Installs all dependencies on Kaggle — no local setup needed |
| 🔥 **CUDA Acceleration** | Uses llama-cpp-python cu124 wheel for GPU inference (forward-compatible with Kaggle's CUDA 13 driver) |
| 🔧 **Dynamic libcuda.so fix** | Scores and symlinks the correct `libcuda.so` from wherever Kaggle actually put it that session |
| 🌐 **Public Tunnel** | Auto-creates ngrok/cloudflared tunnel for external access |
| 🔌 **Anthropic API** | Fully compatible with `/v1/messages` and `/v1/chat/completions` |
| 🧹 **Clean Output** | Strips leaked `<\|channel>thought` template artifacts from raw-prompt generation |
| 🏎️ **Warm-up Inference** | Eats the one-time CUDA JIT compile cost at startup so the first real request is fast |
| ✅ **Health Checks** | Built-in monitoring and smoke testing |
| 🔄 **Fallback Modes** | Multiple load configs (2-GPU, 1-GPU, partial layers, CPU) |
| 💾 **VRAM Monitoring** | Shows real-time VRAM usage and delta |
| 🤖 **Claude Code Ready** | Documented `--bare` flag recipe to connect Claude Code CLI without OAuth conflicts |

---

## 🚀 Quick Start

### Step 1: Create Kaggle Notebook

1. Go to [Kaggle](https://kaggle.com) and create a new Notebook
2. Click **Settings** (gear icon) on the right sidebar
3. Under **Accelerator**, select **GPU T4 x2**
4. Click **Save**

### Step 2: Copy the Script

1. Copy the entire `kaggle_setup.py` script from this repository
2. Paste it into a **single** code cell in your Kaggle notebook — everything (GPU fix, install, download, server, tunnel) runs in one cell so you never need to stop/restart mid-setup

### Step 3: Configure (Optional)

Edit these variables at the top of the script:

```python
NGROK_AUTH_TOKEN = os.environ.get("NGROK_AUTH_TOKEN", "")  # see Configuration below
MODEL_REPO       = "BugTraceAI/BugTraceAI-Apex-G4-26B-Q4"
MODEL_FILE       = "BugTraceAI-Apex-G4-26B-Q4.gguf"
```

> **Note:** If you don't set up an ngrok token, the script uses **cloudflared** instead — no account or token required.

### Step 4: Run

Click **Run** on the cell. The script will:

1. ✅ Kill any leftover server process from a previous run (safe to re-run)
2. ✅ Detect GPUs and driver CUDA version
3. ✅ Find and symlink the correct `libcuda.so` for this session
4. ✅ Install the CUDA-enabled `llama-cpp-python` wheel
5. ✅ Download the model (skipped if already cached, ~15–20GB first time)
6. ✅ Write and syntax-check the API server
7. ✅ Start the server, run a warm-up inference, run a smoke test
8. ✅ Create a public tunnel and print your URL

### Step 5: Connect

Once complete, you'll see something like:

```
============================================================
  BugTraceAI API LIVE (clean output, warmed up)
============================================================
  URL: https://random-words-here.trycloudflare.com
```

Your model is now accessible from anywhere — see [API Usage](#-api-usage) or [Connecting Claude Code CLI](#-connecting-claude-code-cli) below.

> **Each restart gets a new URL** on the free ngrok/cloudflared tier. Re-export `ANTHROPIC_BASE_URL` with the new URL every time you restart the Kaggle kernel.

---

## ⚙️ Configuration

### NGROK_AUTH_TOKEN

To use ngrok:

1. Get a free token from the [ngrok dashboard](https://dashboard.ngrok.com/get-started/your-authtoken)
2. In your Kaggle notebook: **Add-ons → Secrets → Add a new secret**
   - Name: `NGROK_AUTH_TOKEN`
   - Value: your token
3. Attach the secret to the notebook before running

If you'd rather skip ngrok entirely, leave the secret unset — the script automatically falls back to **cloudflared**, which needs no account at all.

> A reserved/static ngrok domain (free tier includes one) or a Cloudflare-account-backed tunnel hostname will save you from re-pasting a new URL every session — worth setting up if this becomes a regular workflow.

### MODEL_REPO / MODEL_FILE

Point these at any compatible GGUF model on Hugging Face if you want to swap models:

```python
MODEL_REPO = "BugTraceAI/BugTraceAI-Apex-G4-26B-Q4"
MODEL_FILE = "BugTraceAI-Apex-G4-26B-Q4.gguf"
```

---

## 🔌 API Usage

The server exposes an Anthropic-Messages-API-compatible endpoint at `/v1/messages` (and an alias at `/v1/chat/completions`).

### Example: curl

```bash
curl https://your-tunnel-url/v1/messages \
  -H "x-api-key: dummy" \
  -H "anthropic-version: 2023-06-01" \
  -H "content-type: application/json" \
  -d '{
    "model": "claude-opus-4-5",
    "max_tokens": 200,
    "temperature": 0.7,
    "messages": [
      {"role": "system", "content": "You are a security expert"},
      {"role": "user", "content": "Explain SQL injection prevention"}
    ]
  }'
```

> The `model` field can be any string — the server ignores it for routing and always uses the loaded GGUF model. Using a real Anthropic model name (like `claude-opus-4-5`) here matters mainly for clients like Claude Code that validate the name client-side.

### Endpoints

| Endpoint | Method | Description |
|---|---|---|
| `/` | GET | Server status, GPU mode, VRAM delta |
| `/health` | GET | Simple health check |
| `/v1/messages` | POST | Anthropic Messages API |
| `/v1/chat/completions` | POST | Alias of `/v1/messages` |

---

## 🤖 Connecting Claude Code CLI

Claude Code's newer versions require OAuth for the default login flow, which conflicts with a custom `ANTHROPIC_BASE_URL`. Two things fix this:

1. **Unset any saved OAuth token** so it doesn't override your API key
2. **Use the `--bare` flag**, which forces Claude Code to authenticate strictly via `ANTHROPIC_API_KEY` (or `apiKeyHelper`) and never touches OAuth or the system keychain

```bash
unset ANTHROPIC_AUTH_TOKEN
export ANTHROPIC_API_KEY="dummy"
export ANTHROPIC_BASE_URL="https://your-tunnel-url"
claude --bare --model claude-opus-4-5
```

```powershell
# PowerShell
$env:ANTHROPIC_API_KEY="dummy"
$env:ANTHROPIC_BASE_URL="https://your-tunnel-url"
claude --bare --model claude-opus-4-5
```

If you're already logged into a real Claude account, log out first so the saved auth token doesn't take precedence:

```bash
claude auth status   # check if logged in
claude auth logout   # if so, log out
```

### Why `--model claude-opus-4-5` specifically?

Claude Code validates the model name client-side against known Anthropic model strings before sending the request. An arbitrary name like `bugtraceai-apex` gets rejected with *"This model may not exist or you may not have access to it."* Using a real model alias satisfies that check; the server-side code ignores it and always runs the loaded GGUF model regardless of what name is sent.

### Quick reconnect helper

Since the tunnel URL changes each session, this shell function saves retyping the whole block:

```bash
# Add to ~/.bashrc or ~/.zshrc
bugtrace() {
    if [ -z "$1" ]; then
        echo "Usage: bugtrace <tunnel-url>"
        return 1
    fi
    unset ANTHROPIC_AUTH_TOKEN
    export ANTHROPIC_API_KEY="dummy"
    export ANTHROPIC_BASE_URL="$1"
    claude --bare --model claude-opus-4-5
}
```

Usage: `bugtrace https://your-new-tunnel-url`

---

## 🧠 How It Works

1. **Cleanup** — kills any server process left running from a previous execution of the cell, so it's always safe to re-run
2. **GPU check** — confirms a GPU is available and reads the CUDA driver version
3. **libcuda.so fix** — Kaggle's CUDA library location varies by session/image (seen at `/usr/local/nvidia/lib64/`, `/usr/local/cuda-*/compat/`, and stub-only paths). The script searches all of `/usr`, `/lib`, `/lib64`, scores each candidate (penalizing stub-only files, preferring versioned `.so.1` files under `nvidia`/`compat` paths), symlinks the best one to standard runtime locations, and rebuilds `ldconfig`
4. **CUDA wheel install** — installs a prebuilt `llama-cpp-python` wheel for CUDA 12.4 (skips slow, frequently-broken from-source compilation against Kaggle's CUDA 13 toolchain)
5. **Model download** — pulls the GGUF file from Hugging Face via `huggingface_hub` (cached on repeat runs)
6. **Server generation** — writes a FastAPI server (`server.py`) that:
   - Loads the model with automatic fallback across 2-GPU layer-split, 1-GPU, partial-offload, and CPU-only configs
   - Runs a warm-up inference to absorb one-time CUDA JIT compile latency before the first real request
   - Strips leaked `<|channel>thought\n<channel|>` template markers from raw-prompt generations before returning the response (these leak through because the server builds prompts manually rather than using the full Jinja chat template)
   - Exposes Anthropic-compatible `/v1/messages` and `/v1/chat/completions`
7. **Syntax check** — the generated `server.py` is compiled with `py_compile` before launch, so syntax errors are caught immediately instead of after a multi-minute model-load wait
8. **Smoke test** — sends a test request *after* warm-up and reports tokens/sec, so the GPU-vs-CPU reading reflects steady-state speed, not cold-start
9. **Tunnel** — opens a public URL via ngrok (if a token is configured) or cloudflared (default, no account needed)

---

## 📦 Requirements

- A free [Kaggle](https://kaggle.com) account with phone-verified access to GPU notebooks
- **GPU T4 x2** accelerator enabled in notebook settings
- Internet access enabled in the notebook (on by default)
- (Optional) A free [ngrok](https://ngrok.com) account if you prefer ngrok over cloudflared
- (Optional) [Claude Code CLI](https://github.com/anthropics/claude-code) v2.1+ if you want the `--bare` connection flow

---

## 🛠️ Troubleshooting

| Symptom | Likely cause / fix |
|---|---|
| `❌ No GPU detected` | Enable **GPU T4 x2** under notebook Settings → Accelerator |
| `pip install failed` at Step 3 | Kaggle's base image changed; check the `llama-cpp-python` cu124 wheel index is still reachable |
| `CUDA::cuda_driver target not found` during a source build | Kaggle's CUDA 13 toolchain breaks `llama-cpp-python` source builds — don't build from source; use the prebuilt cu124 wheel path (the script does this by default) |
| `GPU VRAM used: 0 MiB` despite a "successful" install | The wheel can't find `libcuda.so` at runtime. Check the `[2/8] Locating and fixing libcuda.so` output — if no paths were found, GPU binding isn't possible this session; if paths *were* found but it's still 0 MiB, the `LD_LIBRARY_PATH` may need to be passed into the server subprocess explicitly (the script already does this — confirm `env` is passed to `subprocess.run` if you've modified it) |
| Smoke test shows very low tok/s on first run only | This is cold-start CUDA JIT compilation, not a real CPU fallback — the script's warm-up step exists specifically to avoid this misleading reading. If it's still slow *after* warm-up, then it's genuinely on CPU — check the VRAM delta |
| Model load falls back to CPU | Check the VRAM delta printed at server start; T4 x2 (≈30GB combined) should be enough for a Q4 26B model — if not, try the `partial 20 layers` config manually |
| `⚠️ Could not get cloudflared URL` | Check `/tmp/cf.log` in the notebook for the actual error; occasionally Cloudflare's edge is slow to allocate a hostname — rerun the tunnel step |
| Server starts but requests time out | Kaggle notebooks idle out after ~20–60 min of inactivity unless the tab stays open and active — keep the notebook tab in the foreground |
| ngrok tunnel fails immediately, `ERR_NGROK_105` | Token wasn't set correctly (check for placeholder strings like `YOUR_NGROK_TOKEN_HERE` left in the config), or the token was revoked — generate a new one and re-attach |
| Claude Code says *"model may not exist or you may not have access to it"* | You're using a non-Anthropic model name. Launch with `--model claude-opus-4-5` (or another real Anthropic alias) — the server ignores the name for routing, it's just there to pass Claude Code's client-side validation |
| Claude Code shows `Both ANTHROPIC_AUTH_TOKEN and ANTHROPIC_API_KEY set` warning, or tries to OAuth-login | Run `unset ANTHROPIC_AUTH_TOKEN` and launch with `--bare`, which forces strict API-key auth and never reads OAuth/keychain |
| Claude Code response contains `<\|channel>thought` text | You're running an older version of `server.py` without the cleanup regex — re-run the full setup script; the current version strips this automatically |
| Generated `server.py` throws a `SyntaxError` on a decorator line | Fixed in the current script (avoid stacking `@app.get(...)` decorators on one line with `;`) — if you're editing the template yourself, keep each decorator on its own line |

---

## 📊 Model Information

- **Name:** BugTraceAI Apex G4-26B-Q4
- **Format:** GGUF (Q4_K_M quantization, ~15.6GB)
- **Architecture:** Gemma4, Mixture-of-Experts (128 experts, 8 active), 25.2B total params
- **Source:** [Hugging Face — BugTraceAI](https://huggingface.co/BugTraceAI)
- **Context length:** 4096 tokens served (model supports up to 262144 natively — increase `n_ctx` in `server.py` if you need more and have the VRAM headroom)
- **Intended use:** Local/private inference for security research and CTF workflows, accessed through an Anthropic-compatible API surface

---

## 🔒 Security Notes

- **The tunnel is public.** Anyone with the generated URL can call your model while the notebook is running. There's no authentication on `/v1/messages` beyond a dummy header check — don't share the URL, and shut the notebook down when you're done.
- **Rotate immediately if a token leaks.** If a real ngrok token (or any credential) is ever exposed in a commit, notebook output, or screenshot, treat it as compromised the moment it's visible — revoke/regenerate it at the [ngrok dashboard](https://dashboard.ngrok.com/tunnels/authtokens) rather than just removing it from the file later.
- **This is a research/personal-use setup**, not a hardened production deployment — there's no rate limiting, request logging is minimal, and the API key check is a placeholder, not real auth.
- **Model behavior is your responsibility.** This setup gives you a private inference endpoint; what you build on top of it (recon tooling, exploit drafting, report generation) should stay scoped to systems and engagements you're authorized to test.

---

## 🤝 Contributing

Issues and PRs are welcome. Please don't include real tokens, model weights, or large binaries in any contribution.

---

## 📄 License

MIT — see [LICENSE](LICENSE).

---

## 🙏 Credits

- [llama.cpp](https://github.com/ggerganov/llama.cpp) / [llama-cpp-python](https://github.com/abetlen/llama-cpp-python)
- [Kaggle](https://kaggle.com) for free GPU notebooks
- [cloudflared](https://github.com/cloudflare/cloudflared) and [ngrok](https://ngrok.com) for tunneling
- [Hugging Face](https://huggingface.co) for model hosting
- [Claude Code](https://github.com/anthropics/claude-code) for the `--bare` flag that made this whole pairing possible
