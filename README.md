Veo 2 & Veo 3 Generator (Gemini API Key)
Advanced Streamlit app to batch-generate Veo 2 / Veo 3 videos using the Gemini API with API key only (no Service Account JSON).
Supports long-running operations (predict → poll) and auto-downloads MP4 results.

Author: effands — ziqva.com
Contact: 085649905055

✨ Features
API key only (header x-goog-api-key) — no OAuth/Service Account.

Models: veo-3.0-fast-generate-preview, veo-3.0-generate-preview, veo-2.0-generate-001.

Batch prompts (multi-line or .txt upload).

Progress & polling for each job.

Auto-download & preview MP4 in app.

Rotating log file (+ in-app log viewer).

Compact advanced-only UI with outlined groups (not too long vertically).

🧰 Requirements
Python 3.9+

pip to install dependencies

A Google Cloud project or AI Studio account with Gemini API enabled.

A Gemini API Key (format AIza...).

Model notes

Veo 3 (preview & fast preview): fixed 8 seconds, 16:9 only, audio ON.

Veo 2: 5–8 seconds, 16:9 or 9:16, silent (no audio).

🚀 Quick Start
Clone & install

bash
Copy
Edit
pip install streamlit requests
Run

bash
Copy
Edit
streamlit run app_veo_gemini_advanced.py
Use the app

Paste your Gemini API Key (AIza...).

Choose Model & Parameters.

Add prompts (one per line) or upload .txt.

Click Generate Batch → videos saved to your output folder (default: ~/Downloads/VEO_OUTPUT).

🔑 How to get a Gemini API Key
Option A — Google Cloud Shell (Qwiklabs-like)
bash
Copy
Edit
gcloud services enable generativelanguage.googleapis.com
gcloud services api-keys create --display-name="Gemini API Key"
# Copy the keyString from the command output (starts with AIza...)
Option B — Google AI Studio
Open Google AI Studio → Get API key → create/copy your key (AIza...).

If a model is restricted by organization policy, you may see an error like “model not allowed”. Ask your admin to allowlist the Veo models you need or use a project without that restriction.

🖥️ UI Overview
API & Output: enter API key, choose output folder, enable logging & level.

Model & Parameters: pick model, aspect ratio/duration (auto-constrained per model), set optional negativePrompt / personGeneration.

Prompts: add multi-line prompts or upload .txt (1 prompt per line).

Run & Results: run batch, see progress, preview videos, and a concise summary.

Logs: view the tail of the rotating log file.

📁 Files & Logging
Downloads: ~/Downloads/VEO_OUTPUT/veo_<index>_<timestamp>.mp4

Log file (rotating): ~/Downloads/VEO_OUTPUT/veo_gemini_advanced.log
(2 MB per file, 3 backups)

⚙️ Advanced Notes
The app calls Gemini REST v1beta/models/<model>:predictLongRunning, then polls the returned operation until done, then downloads response.generateVideoResponse.generatedSamples[0].video.uri.

For Veo 2, durationSeconds (5–8) is supported; Veo 3 preview duration is fixed at 8s.

If you hit permission/policy errors, it’s usually an org policy or region restriction. Use an allowed model or switch to an unrestricted project.

❓ Troubleshooting
401/403: Check your API key is valid and hasn’t been restricted (HTTP referrers/IPs).

Model not allowed: Your project/org may block that model. Ask admin to allow it or use a different project.

No URI in response: The operation finished but no video returned (rare). Re-try or adjust prompt.

Download fails: Check network/redirects. The app follows redirects with the API key header.

📝 License
Proprietary — © effands (ziqva.com). Contact for licensing/redistribution.

🙌 Credits
Built by effands — ziqva.com (085649905055)

Thanks to Google Gemini & Veo teams for the API.
