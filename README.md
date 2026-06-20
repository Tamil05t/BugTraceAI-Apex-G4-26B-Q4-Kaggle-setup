# BugTraceAI Apex G4-26B-Q4 — Kaggle GPU Setup

> One-click setup script to run BugTraceAI Apex G4-26B-Q4 model on Kaggle with dual GPU acceleration (T4 x2).

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
| 🔥 **CUDA Acceleration** | Uses llama-cpp-python cu124 for maximum GPU performance |
| 🌐 **Public Tunnel** | Auto-creates ngrok/cloudflared tunnel for external access |
| 🔌 **Anthropic API** | Fully compatible with `/v1/messages` and `/v1/chat/completions` |
| ✅ **Health Checks** | Built-in monitoring and smoke testing |
| 🔄 **Fallback Modes** | Multiple load configs (2-GPU, 1-GPU, partial layers, CPU) |
| 💾 **VRAM Monitoring** | Shows real-time VRAM usage and delta |

---

## 🚀 Quick Start

### Step 1: Create Kaggle Notebook

1. Go to [Kaggle](https://kaggle.com) and create a new Notebook
2. Click **Settings** (gear icon) on the right sidebar
3. Under **Accelerator**, select **GPU T4 x2**
4. Click **Save**

### Step 2: Copy the Script

1. Copy the entire `kaggle_setup.py` script from this repository
2. Paste it into a code cell in your Kaggle notebook

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

1. ✅ Detect GPUs
2. ✅ Install dependencies
3. ✅ Download the model (~15–20GB)
4. ✅ Start the API server
5. ✅ Create a public tunnel
6. ✅ Display your public URL

### Step 5: Connect

Once complete, you'll see something like:

```
============================================================
  BugTraceAI API LIVE
============================================================
  URL: https://random-words-here.trycloudflare.com
```

Your model is now accessible from anywhere.

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
    "model": "bugtraceai-apex",
    "max_tokens": 200,
    "temperature": 0.7,
    "messages": [
      {"role": "system", "content": "You are a security expert"},
      {"role": "user", "content": "Explain SQL injection prevention"}
    ]
  }'
```

### Example: Claude Code CLI

```bash
export ANTHROPIC_API_KEY="dummy"
export ANTHROPIC_BASE_URL="https://your-tunnel-url"
claude
```

```powershell
# PowerShell
$env:ANTHROPIC_API_KEY="dummy"
$env:ANTHROPIC_BASE_URL="https://your-tunnel-url"
claude
```

### Endpoints

| Endpoint | Method | Description |
|---|---|---|
| `/` | GET | Server status, GPU mode, VRAM delta |
| `/health` | GET | Simple health check |
| `/v1/messages` | POST | Anthropic Messages API |
| `/v1/chat/completions` | POST | Alias of `/v1/messages` |

---

## 🧠 How It Works

1. **GPU check** — confirms a GPU is available and reads the CUDA driver version
2. **libcuda.so fix** — Kaggle's CUDA stub linking is occasionally broken; the script locates the real `libcuda.so`, symlinks it to standard paths, and rebuilds `ldconfig`
3. **CUDA wheel install** — installs a prebuilt `llama-cpp-python` wheel for CUDA 12.4 (skips slow from-source compilation)
4. **Model download** — pulls the GGUF file from Hugging Face via `huggingface_hub`
5. **Server generation** — writes a FastAPI server (`server.py`) that loads the model and exposes Anthropic-compatible endpoints, with automatic fallback across 2-GPU, 1-GPU, partial-offload, and CPU-only load configs
6. **Smoke test** — sends a test request and reports tokens/sec to confirm GPU vs CPU inference
7. **Tunnel** — opens a public URL via cloudflared (default) or ngrok (if configured)

---

## 📦 Requirements

- A free [Kaggle](https://kaggle.com) account with phone-verified access to GPU notebooks
- **GPU T4 x2** accelerator enabled in notebook settings
- Internet access enabled in the notebook (on by default)
- (Optional) A free [ngrok](https://ngrok.com) account if you prefer ngrok over cloudflared

---

## 🛠️ Troubleshooting

| Symptom | Likely cause / fix |
|---|---|
| `❌ No GPU detected` | Enable **GPU T4 x2** under notebook Settings → Accelerator |
| `pip install failed` at Step 3 | Kaggle's base image changed; check the `llama-cpp-python` cu124 wheel index is still reachable |
| Model load falls back to CPU | Check the VRAM delta printed at server start; T4 x2 (≈30GB combined) should be enough for a Q4 26B model — if not, try the `partial 20 layers` config manually |
| `⚠️ Could not get cloudflared URL` | Check `/tmp/cf.log` in the notebook for the actual error; occasionally Cloudflare's edge is slow to allocate a hostname — rerun the tunnel step |
| Server starts but requests time out | Kaggle notebooks idle out after ~20–60 min of inactivity unless the tab stays open and active — keep the notebook tab in the foreground |
| ngrok tunnel fails immediately | Token wasn't attached as a Kaggle Secret, or the token was revoked — generate a new one and re-attach |

---

## 📊 Model Information

- **Name:** BugTraceAI Apex G4-26B-Q4
- **Format:** GGUF (Q4 quantization)
- **Source:** [Hugging Face — BugTraceAI](https://huggingface.co/BugTraceAI)
- **Context length:** 4096 tokens (configurable via `n_ctx` in `server.py`)
- **Intended use:** Local/private inference for security research and CTF workflows, accessed through an Anthropic-compatible API surface

---

## 🔒 Security Notes


- **The tunnel is public.** Anyone with the generated URL can call your model while the notebook is running. There's no authentication on `/v1/messages` beyond a dummy header check — don't share the URL, and shut the notebook down when you're done.
- **Rotate immediately if a token leaks.** If a real ngrok token (or any credential) is ever exposed in a commit, notebook output, or screenshot, treat it as compromised the moment it's visible — revoke/regenerate it at the [ngrok dashboard](https://dashboard.ngrok.com/tunnels/authtokens) rather than just removing it from the file later.
- **This is a research/personal-use setup**, not a hardened production deployment — there's no rate limiting, request logging is minimal, and the API key check is a placeholder, not real auth.

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
