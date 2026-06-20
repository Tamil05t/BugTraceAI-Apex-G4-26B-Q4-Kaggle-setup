###############################################################################
# BugTraceAI Apex G4-26B-Q4 — Kaggle Setup FINAL (v6 + clean-output patch)
# Single cell — run once, does everything: GPU fix, install, download,
# server with thinking-channel stripped, warm-up, tunnel.
###############################################################################

import subprocess, time, requests, os, sys, re, threading

# =====================================================================
# ⚙️  CONFIGURE BEFORE RUNNING
# =====================================================================
# Option A (recommended for Kaggle): leave this as "" and the script will
#   automatically fall back to cloudflared, which needs no account/token.
# Option B: use ngrok instead — get a free token at https://dashboard.ngrok.com/get-started/your-authtoken
#   then set it as a Kaggle Secret named NGROK_AUTH_TOKEN and read it below,
#   rather than pasting it directly into this file.
NGROK_AUTH_TOKEN = os.environ.get("NGROK_AUTH_TOKEN", "")  # <-- put your token in a Kaggle Secret, do NOT hardcode it here
MODEL_REPO       = "BugTraceAI/BugTraceAI-Apex-G4-26B-Q4"
MODEL_FILE       = "BugTraceAI-Apex-G4-26B-Q4.gguf"
# =====================================================================

def sh(cmd, capture=False):
    return subprocess.run(cmd, shell=True, capture_output=capture, text=True)

def banner(msg):
    print(f"\n{'='*60}\n  {msg}\n{'='*60}")

banner("BugTraceAI Apex G4-26B-Q4 — Kaggle GPU Setup FINAL")

# Kill any previously running server from an earlier cell run
sh("pkill -f 'server.py' 2>/dev/null")
time.sleep(1)

# ─────────────────────────────────────────────────────────────
# STEP 1 — GPU Check
# ─────────────────────────────────────────────────────────────
print("\n[1/8] Checking GPU availability...")
gpu_out = sh("nvidia-smi --query-gpu=name,memory.total --format=csv,noheader", capture=True).stdout.strip()
cuda_ver = sh("nvidia-smi | grep -oP 'CUDA Version: \\K[0-9.]+'", capture=True).stdout.strip()

if not gpu_out:
    print("❌  No GPU detected. Enable GPU T4 x2 in Kaggle Settings.")
    sys.exit(1)

gpus = [g.strip() for g in gpu_out.splitlines() if g.strip()]
print(f"✅  {len(gpus)} GPU(s) | Driver CUDA: {cuda_ver}")
for i, g in enumerate(gpus):
    print(f"    GPU{i}: {g}")

# ─────────────────────────────────────────────────────────────
# STEP 2 — Fix libcuda.so (dynamic search)
# ─────────────────────────────────────────────────────────────
print("\n[2/8] Locating and fixing libcuda.so...")

find_out = sh("find /usr /lib /lib64 -name 'libcuda.so*' 2>/dev/null", capture=True).stdout.strip()
found_paths = [p.strip() for p in find_out.splitlines() if p.strip()]
print(f"    Found: {found_paths}")

def score(p):
    s = 0
    if "stub" in p:    s -= 10
    if p.endswith(".so.1"): s += 5
    if "nvidia" in p:  s += 3
    if "compat" in p:  s += 2
    return s

libcuda_src = None
if found_paths:
    libcuda_src = sorted(found_paths, key=score, reverse=True)[0]
    print(f"    Best candidate: {libcuda_src}")
    targets = [
        "/usr/lib/x86_64-linux-gnu/libcuda.so.1",
        "/usr/lib/libcuda.so.1",
        "/usr/local/lib/libcuda.so.1",
    ]
    for t in targets:
        sh(f"ln -sf {libcuda_src} {t} 2>/dev/null || true")
    print(f"    Symlinked to standard paths ✅")
else:
    print("    ⚠️  libcuda.so not found")

cuda_lib_dirs = [
    "/usr/local/nvidia/lib64",
    "/usr/local/cuda/lib64",
    "/usr/local/cuda/lib64/stubs",
    "/usr/local/lib",
    "/usr/lib/x86_64-linux-gnu",
]
for d in sh("find /usr/local -maxdepth 3 -name 'compat' -type d 2>/dev/null", capture=True).stdout.splitlines():
    d = d.strip()
    if d:
        cuda_lib_dirs.append(d)

if libcuda_src:
    cuda_lib_dirs.insert(0, os.path.dirname(libcuda_src))

seen = set()
existing_dirs = []
for d in cuda_lib_dirs:
    if d not in seen and os.path.isdir(d):
        seen.add(d)
        existing_dirs.append(d)

ld_path = ":".join(existing_dirs + [os.environ.get("LD_LIBRARY_PATH", "")])
os.environ["LD_LIBRARY_PATH"] = ld_path
os.environ["CUDA_VISIBLE_DEVICES"] = "0,1"

print(f"    LD_LIBRARY_PATH dirs: {existing_dirs}")

with open("/etc/ld.so.conf.d/kaggle-cuda.conf", "w") as f:
    f.write("\n".join(existing_dirs))
sh("ldconfig 2>/dev/null")
print("    ldconfig updated ✅")

# ─────────────────────────────────────────────────────────────
# STEP 3 — Install pre-built cu124 wheel
# ─────────────────────────────────────────────────────────────
print("\n[3/8] Installing llama-cpp-python cu124 wheel...")
sh("pip uninstall llama-cpp-python -y -q 2>/dev/null")

ret = sh(
    "pip install llama-cpp-python "
    "--extra-index-url https://abetlen.github.io/llama-cpp-python/whl/cu124 "
    "--no-cache-dir --force-reinstall -q 2>/dev/null"
)
if ret.returncode != 0:
    print("❌  pip install failed"); sys.exit(1)

verify = sh(
    f'LD_LIBRARY_PATH="{ld_path}" CUDA_VISIBLE_DEVICES="0,1" python -c '
    '"import llama_cpp; i=llama_cpp.llama_print_system_info(); print(i)"',
    capture=True
)
sysinfo = verify.stdout.strip()
has_cuda = "GGML_CUDA" in sysinfo or ("CUDA" in sysinfo and "NO_CUDA" not in sysinfo)
print(f"    System info: {sysinfo[:150]}")
if has_cuda:
    print("✅  CUDA confirmed in llama-cpp-python!")
else:
    print("⚠️  CUDA not in system_info — will verify via VRAM delta after load")

sh("pip install huggingface-hub fastapi uvicorn -q 2>/dev/null")

if NGROK_AUTH_TOKEN:
    sh("pip install pyngrok -q 2>/dev/null")
else:
    cf = "/usr/local/bin/cloudflared"
    if not os.path.exists(cf):
        sh("wget -q https://github.com/cloudflare/cloudflared/releases/latest/download/"
           "cloudflared-linux-amd64 -O /usr/local/bin/cloudflared && chmod +x /usr/local/bin/cloudflared")
print("✅  All packages ready")

# ─────────────────────────────────────────────────────────────
# STEP 4 — Download / verify model
# ─────────────────────────────────────────────────────────────
print(f"\n[4/8] Downloading / verifying model...")
from huggingface_hub import hf_hub_download
model_path = hf_hub_download(repo_id=MODEL_REPO, filename=MODEL_FILE)
print(f"✅  Model: {model_path}")

# ─────────────────────────────────────────────────────────────
# STEP 5 — Write server.py WITH clean-output patch baked in
# ─────────────────────────────────────────────────────────────
print("\n[5/8] Writing API server (with thinking-channel cleanup + warm-up)...")

SERVER_SCRIPT = f'''#!/usr/bin/env python3
"""BugTraceAI Apex FINAL — Anthropic-Compatible API (clean output)"""
import os
import re
import sys
import time
import subprocess

os.environ["CUDA_VISIBLE_DEVICES"] = "0,1"
os.environ["LD_LIBRARY_PATH"] = {repr(ld_path)}

try:
    from llama_cpp import Llama
except ModuleNotFoundError:
    print("ERROR: llama_cpp not found — run setup cell first")
    sys.exit(1)

import uvicorn
from fastapi import FastAPI
from fastapi import Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

MODEL_PATH = {repr(model_path)}
DEFAULT_SYSTEM = "You are BugTraceAI Apex, an expert offensive security assistant."

# Strips leaked <|channel>thought ... <channel|> markers from raw-prompt generation
THINKING_PATTERN = re.compile(
    r"^\\s*<\\|channel>thought\\s*\\n?<channel\\|>\\s*", re.DOTALL
)


def clean_response(text: str) -> str:
    return THINKING_PATTERN.sub("", text).strip()


def get_vram():
    r = subprocess.run(
        "nvidia-smi --query-gpu=memory.used --format=csv,noheader",
        shell=True, capture_output=True, text=True
    )
    return [v.strip() for v in r.stdout.strip().splitlines() if v.strip()]


print("\\nLoading model onto GPU...")
vram_before = get_vram()
print(f"   VRAM before load: {{vram_before}}")

llm = None
load_configs = [
    ("2-GPU layer-split", dict(n_gpu_layers=-1, split_mode=1, tensor_split=[1.0, 1.0], flash_attn=True)),
    ("1-GPU no split",    dict(n_gpu_layers=-1, split_mode=0, flash_attn=True)),
    ("partial 20 layers", dict(n_gpu_layers=20, flash_attn=True)),
    ("CPU fallback",      dict(n_gpu_layers=0)),
]

for desc, kwargs in load_configs:
    try:
        print(f"   Trying: {{desc}}...")
        llm = Llama(model_path=MODEL_PATH, n_ctx=4096, verbose=False, **kwargs)
        print(f"   Loaded: {{desc}}")
        break
    except Exception as e:
        print(f"   Failed: {{e}}")
        llm = None

if llm is None:
    print("FATAL: all load configs failed")
    sys.exit(1)

vram_after = get_vram()
try:
    delta = [
        int(a.replace("MiB", "").strip()) - int(b.replace("MiB", "").strip())
        for a, b in zip(vram_after, vram_before)
    ]
    total_gpu_mb = sum(delta)
except Exception:
    delta = []
    total_gpu_mb = 0

gpu_status = "GPU" if total_gpu_mb > 2000 else "CPU"
print(f"   Mode: {{gpu_status}} | VRAM delta: {{delta}} MiB ({{total_gpu_mb}} MiB total)")

# Warm-up call eats the one-time CUDA JIT compile cost so the first
# real request (from Claude Code) is fast, not falsely flagged as CPU.
print("   Running warm-up inference...")
try:
    _ = llm("<|turn>user\\nHi<turn|>\\n<|turn>model\\n", max_tokens=5)
    print("   Warm-up complete.")
except Exception as e:
    print(f"   Warm-up skipped: {{e}}")

app = FastAPI(title="BugTraceAI API FINAL")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
def root():
    return {{
        "status": "ok",
        "model": "BugTraceAI-Apex-G4-26B-Q4",
        "gpu_status": gpu_status,
        "vram_delta_mib": delta,
        "total_gpu_mib": total_gpu_mb,
    }}


@app.get("/health")
def health():
    return {{"status": "ok"}}


def extract_messages(req: dict):
    system = req.get("system", DEFAULT_SYSTEM)
    user = ""
    for msg in req.get("messages", []):
        role = msg.get("role", "")
        content = msg.get("content", "")
        if role == "system":
            if isinstance(content, str):
                system = content
        elif role == "user":
            if isinstance(content, str):
                user = content
            elif isinstance(content, list):
                user = " ".join(
                    b.get("text", "")
                    for b in content
                    if isinstance(b, dict) and b.get("type") == "text"
                )
    return system, user


@app.post("/v1/messages")
async def handle_messages(request: Request):
    try:
        req = await request.json()
    except Exception:
        return JSONResponse(status_code=400, content={{"error": "Invalid JSON"}})

    system, user = extract_messages(req)
    prompt = (
        f"<|turn>system\\n{{system}}<turn|>\\n"
        f"<|turn>user\\n{{user}}<turn|>\\n"
        f"<|turn>model\\n"
    )

    try:
        resp = llm(
            prompt,
            max_tokens=min(req.get("max_tokens", 2048), 4000),
            temperature=req.get("temperature", 0.7),
            top_p=req.get("top_p", 0.9),
            repeat_penalty=1.1,
            stop=["<turn|>", "<|turn>", "<eos>", "</s>"],
            echo=False,
        )
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={{"error": {{"type": "server_error", "message": str(e)}}}},
        )

    raw_text = resp["choices"][0]["text"].strip()
    text = clean_response(raw_text)
    usage = resp.get("usage", {{}})

    return {{
        "id": f"msg_{{int(time.time() * 1000)}}",
        "type": "message",
        "role": "assistant",
        "model": req.get("model", "claude-opus-4-5"),
        "content": [{{"type": "text", "text": text}}],
        "stop_reason": "end_turn",
        "stop_sequence": None,
        "usage": {{
            "input_tokens": usage.get("prompt_tokens", 0),
            "output_tokens": usage.get("completion_tokens", 0),
        }},
    }}


@app.post("/v1/chat/completions")
async def handle_chat(request: Request):
    return await handle_messages(request)


@app.exception_handler(Exception)
async def global_error(request: Request, exc: Exception):
    return JSONResponse(
        status_code=500,
        content={{"error": {{"type": "api_error", "message": str(exc)}}}},
    )


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000, log_level="warning")
'''

with open("/kaggle/working/server.py", "w") as f:
    f.write(SERVER_SCRIPT)
print("✅  Server script written")

syntax = sh(f"{sys.executable} -m py_compile /kaggle/working/server.py", capture=True)
if syntax.returncode == 0:
    print("✅  Syntax check passed")
else:
    print(f"❌  Syntax error in server.py:\n{syntax.stderr}")
    sys.exit(1)

# ─────────────────────────────────────────────────────────────
# STEP 6 — Launch server (warm-up adds ~30s extra wait)
# ─────────────────────────────────────────────────────────────
print("\n[6/8] Launching server (model load + warm-up, ~2.5-3 min)...")

env = os.environ.copy()
env["CUDA_VISIBLE_DEVICES"] = "0,1"
env["LD_LIBRARY_PATH"] = ld_path

def _run_server():
    subprocess.run([sys.executable, "/kaggle/working/server.py"], env=env)

threading.Thread(target=_run_server, daemon=True).start()

print("    Waiting for model to load", end="", flush=True)
ready = False
for _ in range(150):
    time.sleep(2)
    print(".", end="", flush=True)
    try:
        if requests.get("http://localhost:8000/health", timeout=3).status_code == 200:
            ready = True
            break
    except Exception:
        pass
print()

if not ready:
    print("❌  Server failed to start. Scroll up for error messages.")
    sys.exit(1)

try:
    info = requests.get("http://localhost:8000/", timeout=5).json()
    gpu_mb = info.get("total_gpu_mib", 0)
    delta  = info.get("vram_delta_mib", [])
    mode   = "GPU ✅" if gpu_mb > 2000 else "CPU ⚠️"
    print(f"✅  Server UP! Mode: {mode} | VRAM delta: {delta} MiB")
except Exception:
    print("✅  Server UP!")

# ─────────────────────────────────────────────────────────────
# STEP 7 — Smoke test (now post-warm-up, speed reading is accurate)
# ─────────────────────────────────────────────────────────────
print("\n[7/8] Smoke test...")
try:
    t0 = time.time()
    r = requests.post(
        "http://localhost:8000/v1/messages",
        json={
            "model": "claude-opus-4-5",
            "max_tokens": 30,
            "messages": [{"role": "user", "content": "Say: OK clean response"}],
        },
        headers={"x-api-key": "dummy", "anthropic-version": "2023-06-01"},
        timeout=90,
    )
    elapsed = time.time() - t0
    if r.status_code == 200:
        data  = r.json()
        text  = data["content"][0]["text"]
        toks  = data["usage"]["output_tokens"]
        speed = toks / elapsed if elapsed > 0 else 0
        label = "GPU ✅" if speed > 15 else "CPU ⚠️ (slow but works)"
        print(f"✅  '{text[:80]}' | {speed:.1f} tok/s → {label}")
    else:
        print(f"❌  HTTP {r.status_code}: {r.text[:200]}")
except Exception as e:
    print(f"⚠️  {e}")

# ─────────────────────────────────────────────────────────────
# STEP 8 — Tunnel (ngrok or cloudflared)
# ─────────────────────────────────────────────────────────────
print("\n[8/8] Creating tunnel...")
public_url = None

if NGROK_AUTH_TOKEN and "YOUR_NGROK" not in NGROK_AUTH_TOKEN:
    try:
        from pyngrok import ngrok, conf
        conf.get_default().auth_token = NGROK_AUTH_TOKEN
        ngrok.kill()
        time.sleep(1)
        public_url = ngrok.connect(8000, "http").public_url
        print(f"✅  ngrok: {public_url}")
    except Exception as e:
        print(f"⚠️  ngrok failed ({e}) — trying cloudflared")

if not public_url:
    cf = "/usr/local/bin/cloudflared"
    if not os.path.exists(cf):
        sh(
            "wget -q https://github.com/cloudflare/cloudflared/releases/latest/download/"
            "cloudflared-linux-amd64 -O /usr/local/bin/cloudflared "
            "&& chmod +x /usr/local/bin/cloudflared"
        )
    cf_log = "/tmp/cf.log"
    subprocess.Popen(
        [cf, "tunnel", "--url", "http://localhost:8000", "--no-autoupdate", "--logfile", cf_log],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    print("    Waiting for cloudflared URL", end="", flush=True)
    for _ in range(30):
        time.sleep(2)
        print(".", end="", flush=True)
        try:
            log = open(cf_log).read()
            m = re.search(r'https://[a-z0-9\-]+\.trycloudflare\.com', log)
            if m:
                public_url = m.group(0)
                break
        except Exception:
            pass
    print()
    if public_url:
        print(f"✅  cloudflared: {public_url}")
    else:
        print("⚠️  Could not get cloudflared URL. Check /tmp/cf.log")

# ─────────────────────────────────────────────────────────────
# Final output
# ─────────────────────────────────────────────────────────────
url = public_url or "http://localhost:8000 (local only)"
print(f"""
{'='*60}
  BugTraceAI API LIVE (clean output, warmed up)
{'='*60}
  URL: {url}

  Linux/macOS — Claude Code CLI:
    unset ANTHROPIC_AUTH_TOKEN
    export ANTHROPIC_API_KEY="dummy"
    export ANTHROPIC_BASE_URL="{url}"
    claude --bare --model claude-opus-4-5

  Windows PowerShell:
    $env:ANTHROPIC_API_KEY="dummy"
    $env:ANTHROPIC_BASE_URL="{url}"
    claude --bare --model claude-opus-4-5

  curl test:
    curl {url}/v1/messages \\
      -H "x-api-key: dummy" \\
      -H "anthropic-version: 2023-06-01" \\
      -H "content-type: application/json" \\
      -d '{{"model":"claude-opus-4-5","max_tokens":50,"messages":[{{"role":"user","content":"Hello"}}]}}'
{'='*60}
  Keep-alive running — do NOT close this tab.
""")

try:
    while True:
        time.sleep(60)
        try:
            requests.get("http://localhost:8000/health", timeout=5)
        except Exception:
            pass
except KeyboardInterrupt:
    print("\n Done.")
