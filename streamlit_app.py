# app_veo_gemini_advanced.py
# Streamlit • Veo 2 / Veo 3 via Gemini API (API key only)
# - Advanced-only UI, compact 2-column layout
# - Thin outlined groups (expanders styled like cards)
# - Batch prompts, LRO polling, MP4 download & preview
# - Rotating log + viewer
# pip install streamlit requests

import os
import time
import json
import logging
from logging.handlers import RotatingFileHandler
from datetime import datetime
from urllib.parse import urlparse, urlunparse, parse_qsl, urlencode

import requests
import streamlit as st

# =========================
# Page & Global Config
# =========================
st.set_page_config(page_title="RenderX Veo", layout="wide")
BASE_URL = "https://generativelanguage.googleapis.com/v1beta"

# Compact CSS + thin outline for groups
st.markdown("""
<style>
:root {
  --card-border-light: rgba(0,0,0,.12);
  --card-border-dark: rgba(255,255,255,.15);
}
html:not(.dark) details { border:1px solid var(--card-border-light); }
html.dark details { border:1px solid var(--card-border-dark); }
details {
  border-radius: 12px; padding: 10px 12px; margin-bottom: 10px;
}
details > summary {
  font-weight: 600; font-size: 0.95rem; margin-bottom: 6px; cursor: pointer;
}
.block-container { padding-top: 1.2rem; }
h1, h2, h3 { margin-bottom: .4rem; }
.small-note { opacity:.7; font-size:.9rem; }
.cardpad { padding: 4px 6px 2px 6px; }
</style>
""", unsafe_allow_html=True)

st.title("🎬 RenderX Veo")

# =========================
# Session Defaults
# =========================
if "prompts" not in st.session_state:
    st.session_state.prompts = []
if "results" not in st.session_state:
    st.session_state.results = []

# =========================
# Logging
# =========================
def setup_logger(log_path: str | None, level=logging.INFO):
    logger = logging.getLogger("veo_gemini_adv")
    logger.setLevel(level)
    logger.propagate = False
    if logger.handlers:  # avoid duplicate handlers on rerun
        return logger
    fmt = logging.Formatter("%(asctime)s | %(levelname)s | %(message)s")
    ch = logging.StreamHandler()
    ch.setFormatter(fmt); ch.setLevel(level)
    logger.addHandler(ch)
    if log_path:
        try:
            fh = RotatingFileHandler(log_path, maxBytes=2_000_000, backupCount=3, encoding="utf-8")
            fh.setFormatter(fmt); fh.setLevel(level)
            logger.addHandler(fh)
        except Exception as e:
            st.warning(f"⚠️ Log file gagal dibuat: {e}")
    return logger

def tail_file(path: str, max_bytes: int = 60_000) -> str:
    try:
        size = os.path.getsize(path)
        with open(path, "rb") as f:
            if size > max_bytes:
                f.seek(-max_bytes, os.SEEK_END)
            return f.read().decode("utf-8", errors="ignore")
    except Exception as e:
        return f"(Tidak dapat membaca log: {e})"

# =========================
# Top Row: API+Output | Model+Params
# =========================
colL, colR = st.columns(2, gap="small")

with colL:
    with st.expander("🔑 API & Output", expanded=True):
        api_key = st.text_input("Gemini API Key (format AIza…)", type="password")
        default_out = os.path.join(os.path.expanduser("~"), "Downloads", "VEO_OUTPUT")
        output_folder = st.text_input("Folder output", value=default_out)
        os.makedirs(output_folder, exist_ok=True)

        use_file_log = st.toggle("Aktifkan file log", value=True)
        log_level = st.selectbox("Level Log", ["INFO", "DEBUG", "WARNING", "ERROR"], index=0)
        log_file = os.path.join(output_folder, "veo_gemini_advanced.log") if use_file_log else None
        logger = setup_logger(log_file, getattr(logging, log_level))

        st.caption("API key bisa dibuat dari Google AI Studio atau `gcloud services api-keys create`.")

with colR:
    with st.expander("🎛️ Model & Parameters", expanded=True):
        model = st.selectbox(
            "Model",
            [
                "veo-3.0-fast-generate-preview",  # cepat, 8s, 16:9, audio on
                "veo-3.0-generate-preview",       # 8s, 16:9, audio on
                "veo-2.0-generate-001",           # 5–8s, 16:9/9:16, silent
            ],
            index=0
        )

        # Aspect ratio & duration rules
        if model.startswith("veo-3."):
            aspect_ratio = st.selectbox("Aspect Ratio", ["16:9"], index=0)
            st.markdown('<div class="small-note">Veo 3 preview: 16:9 & 8 detik (audio on).</div>', unsafe_allow_html=True)
            duration_seconds = 8
        else:
            aspect_ratio = st.selectbox("Aspect Ratio (Veo 2)", ["16:9", "9:16"], index=0)
            duration_seconds = st.selectbox("Durasi (detik, Veo 2)", [5, 6, 7, 8], index=3)

        c1, c2 = st.columns(2, gap="small")
        with c1:
            negative_prompt = st.text_input("Negative Prompt (opsional)", value="")
        with c2:
            person_generation = st.selectbox(
                "Person Generation (opsional)",
                ["(default)", "allow_all", "allow_adult", "dont_allow"],
                index=0,
                help="Tergantung region & model. Biarkan default jika ragu."
            )
            if person_generation == "(default)":
                person_generation = None

# =========================
# Prompts (Full width, compact)
# =========================
with st.expander("📝 Prompts", expanded=True):
    cA, cB = st.columns([2, 1], gap="small")
    with cA:
        multi = st.text_area("Tambahkan beberapa prompt (1 baris = 1 prompt)", height=160, placeholder="Contoh: An ultra wide cinematic shot of ...")
        if st.button("➕ Tambah dari teks di atas"):
            lines = [l.strip() for l in multi.splitlines() if l.strip()]
            st.session_state.prompts.extend(lines)
            st.success(f"Ditambahkan {len(lines)} prompt.")

    with cB:
        txt = st.file_uploader("Upload .txt (1/baris)", type=["txt"])
        if txt:
            lines = txt.read().decode("utf-8", errors="ignore").splitlines()
            lines = [l.strip() for l in lines if l.strip()]
            st.session_state.prompts.extend(lines)
            st.success(f"Ditambahkan {len(lines)} prompt dari file.")
        if st.button("🧹 Bersihkan semua prompt"):
            st.session_state.prompts = []
            st.success("Prompt dibersihkan.")

    if st.session_state.prompts:
        st.caption(f"Total prompt: {len(st.session_state.prompts)}")
        with st.container():
            for i, p in enumerate(st.session_state.prompts, start=1):
                st.text(f"{i}. {p}")

# =========================
# Gemini REST Helpers
# =========================
def start_generation(api_key: str, model: str, prompt: str,
                     aspect_ratio: str, negative_prompt: str | None,
                     person_generation: str | None,
                     duration_seconds: int | None) -> tuple[bool, str]:
    """
    Kick off Veo via Gemini API (predictLongRunning). Returns (ok, operation_name_or_error)
    """
    url = f"{BASE_URL}/models/{model}:predictLongRunning"
    headers = {"x-goog-api-key": api_key, "Content-Type": "application/json"}
    params = {"aspectRatio": aspect_ratio}
    if model.startswith("veo-2.") and duration_seconds:
        params["durationSeconds"] = int(duration_seconds)
    if negative_prompt:
        params["negativePrompt"] = negative_prompt
    if person_generation:
        params["personGeneration"] = person_generation

    body = {"instances": [{"prompt": prompt}], "parameters": params}

    logger.info(f"Kickoff -> model={model} aspect={aspect_ratio} dur={params.get('durationSeconds','8')} prompt='{prompt[:80]}'")
    resp = requests.post(url, headers=headers, data=json.dumps(body), timeout=90)
    if resp.status_code != 200:
        logger.error(f"Kickoff FAIL {resp.status_code}: {resp.text}")
        return False, f"{resp.status_code}: {resp.text}"
    data = resp.json()
    op_name = data.get("name")
    if not op_name:
        logger.error(f"Kickoff BAD RESPONSE: {data}")
        return False, f"Bad response: {data}"
    logger.info(f"Kickoff OK operation={op_name}")
    return True, op_name

def poll_operation(api_key: str, operation_name: str, timeout: int = 900, every: int = 5) -> tuple[bool, dict | str]:
    """
    Poll until done. Returns (ok, response_dict_or_error_str).
    """
    url = f"{BASE_URL}/{operation_name}"
    headers = {"x-goog-api-key": api_key}
    start = time.time()
    progress = st.progress(0, text="Menunggu hasil (polling)…")

    while True:
        try:
            r = requests.get(url, headers=headers, timeout=60)
        except Exception as e:
            logger.error(f"Poll EXCEPTION: {e}")
            progress.empty()
            return False, f"Exception: {e}"

        if r.status_code != 200:
            logger.error(f"Poll FAIL {r.status_code}: {r.text}")
            progress.empty()
            return False, f"{r.status_code}: {r.text}"
        j = r.json()
        if j.get("done"):
            logger.info("Poll DONE")
            progress.progress(100, text="Selesai.")
            time.sleep(0.25)
            progress.empty()
            return True, j

        elapsed = time.time() - start
        pct = min(int((elapsed / timeout) * 100), 99)
        progress.progress(pct, text=f"Polling… ({pct}%)")
        logger.debug(f"Poll running… elapsed={int(elapsed)}s")
        if elapsed > timeout:
            logger.error("Poll TIMEOUT")
            progress.empty()
            return False, "Timeout polling operation."
        time.sleep(every)

# ---------- URI helpers (fix for redirects/auth) ----------
def _append_key(u: str, key: str) -> str:
    """
    Put the API key in the query string so auth survives cross-host redirects.
    """
    parts = list(urlparse(u))
    q = dict(parse_qsl(parts[4]))
    q["key"] = key
    parts[4] = urlencode(q)
    return urlunparse(parts)

def extract_video_uri(op_json: dict) -> str | None:
    """
    Supports both current (generatedVideos) and older (generateVideoResponse.generatedSamples)
    response shapes, and returns a downloadable URI (without the key).
    """
    r = op_json.get("response", {}) or {}

    # Newer shape
    try:
        v = r["generatedVideos"][0]["video"]
        uri = v.get("uri") or v.get("fileUri")
        if uri:
            return uri
    except Exception:
        pass

    # Older/preview shape
    try:
        v = r["generateVideoResponse"]["generatedSamples"][0]["video"]
        uri = v.get("uri") or v.get("fileUri")
        if uri:
            return uri
    except Exception:
        pass

    return None

def download_video_by_uri(api_key: str, uri: str, out_path: str) -> tuple[bool, str]:
    """
    Download the video using the URI from the operation response.
    IMPORTANT: add ?key=... so auth survives cross-host redirects.
    """
    dl_url = _append_key(uri, api_key)

    logger.info(f"Download -> {dl_url} -> {out_path}")
    try:
        with requests.Session() as s:
            r = s.get(dl_url, stream=True, allow_redirects=True, timeout=300)
            if r.status_code != 200:
                ct = r.headers.get("content-type", "")
                msg = r.text if "application/json" in ct or "text" in ct else f"HTTP {r.status_code}"
                logger.error(f"Download FAIL {r.status_code}: {msg}")
                return False, msg

            ct = r.headers.get("content-type", "")
            if "video" not in ct and "octet-stream" not in ct:
                logger.warning(f"Unexpected content-type during download: {ct}")

            os.makedirs(os.path.dirname(out_path), exist_ok=True)
            with open(out_path, "wb") as f:
                for chunk in r.iter_content(chunk_size=1024 * 1024):
                    if chunk:
                        f.write(chunk)

        logger.info("Download OK")
        return True, out_path
    except Exception as e:
        logger.exception(f"Download EXCEPTION: {e}")
        return False, str(e)

# =========================
# Run Row & Results
# =========================
with st.expander("🚀 Jalankan & Hasil", expanded=True):
    runL, runR = st.columns([1, 3], gap="small")
    with runL:
        go = st.button("🎬 Generate Batch", use_container_width=True)
    with runR:
        st.caption("Video akan diunduh & dipreview otomatis. Lihat log jika ada error.")

    if go:
        if not api_key:
            st.error("Masukkan API key dulu.")
        elif not st.session_state.prompts:
            st.error("Tambah minimal 1 prompt.")
        else:
            st.session_state.results = []
            status = st.empty()
            for i, prompt in enumerate(st.session_state.prompts, start=1):
                status.text(f"Mulai job {i}/{len(st.session_state.prompts)} …")
                logger.info(f"=== JOB {i} START ===")
                ok, op_or_err = start_generation(
                    api_key=api_key,
                    model=model,
                    prompt=prompt,
                    aspect_ratio=aspect_ratio,
                    negative_prompt=negative_prompt,
                    person_generation=person_generation,
                    duration_seconds=duration_seconds if model.startswith("veo-2.") else None
                )
                if not ok:
                    st.error(f"Kickoff gagal: {op_or_err}")
                    st.session_state.results.append({"index": i, "status": "ERROR", "info": op_or_err, "prompt": prompt})
                    logger.info(f"=== JOB {i} END (kickoff error) ===")
                    continue

                op_name = op_or_err
                ok, resp = poll_operation(api_key, op_name, timeout=900, every=5)
                if not ok:
                    st.error(f"Gagal polling: {resp}")
                    st.session_state.results.append({"index": i, "status": "ERROR", "info": str(resp), "prompt": prompt})
                    logger.info(f"=== JOB {i} END (poll error) ===")
                    continue

                # Parse URI (robust to new/old response shapes)
                uri = extract_video_uri(resp)
                if not uri:
                    st.error("Respon selesai tapi tidak ada URI video yang bisa diunduh.")
                    st.session_state.results.append({"index": i, "status": "ERROR", "info": "No URI in response", "prompt": prompt})
                    logger.info(f"=== JOB {i} END (no uri) ===")
                    continue

                ts = datetime.now().strftime("%Y%m%d_%H%M%S")
                fname = f"veo_{i}_{ts}.mp4"
                out_path = os.path.join(output_folder, fname)

                ok, msg = download_video_by_uri(api_key, uri, out_path)
                if ok:
                    st.success(f"✅ Video {i} tersimpan: {out_path}")
                    st.video(out_path)

                    # Optional: client download button (useful if app berjalan di server)
                    try:
                        with open(out_path, "rb") as f:
                            st.download_button("⬇️ Download MP4", f, file_name=os.path.basename(out_path), mime="video/mp4", key=f"dl_{i}_{ts}")
                    except Exception as e:
                        logger.warning(f"Gagal membuat tombol download: {e}")

                    st.session_state.results.append({"index": i, "status": "OK", "info": out_path, "prompt": prompt})
                else:
                    st.error(f"Download gagal: {msg}")
                    st.session_state.results.append({"index": i, "status": "ERROR", "info": msg, "prompt": prompt})

                logger.info(f"=== JOB {i} END ===")

            status.empty()
            st.markdown("---")
            st.subheader("📊 Ringkasan")
            for r in st.session_state.results:
                emoji = "✅" if r["status"] == "OK" else "❌"
                st.write(f"{r['index']}. {emoji} {r['status']} — {r['info']}")

# =========================
# Logs (Collapsed by default)
# =========================
with st.expander("📜 Logs", expanded=False):
    if 'use_file_log' in locals() and use_file_log and log_file and os.path.exists(log_file):
        if st.button("Muat Log Terbaru"):
            st.text_area("Tail Log", tail_file(log_file), height=280)
        st.caption(log_file)
    else:
        st.caption("File log belum tersedia atau logging dimatikan.")

# =========================
# Footer
# =========================
st.markdown("---")
st.caption("Created by @effands with Ai | ziqva.com - @2025")
st.caption("kontak : 0856 4990 5055")
st.caption(f"Terakhir diupdate: {datetime.now().strftime('%d %B %Y %H:%M:%S')}")
