# 🚀 FACILESS VIDEO BRANDING AUTOMATION

**A Flask-based backend to automatically turn short-form reposts into unique, brand-consistent, repost-resistant content.**  
Perfect for IG Reels, TikTok, and Facebook automation at scale.

---

# ✅ WHAT THIS SYSTEM DOES

- 🔽 **Downloads videos** using `wget`
- 🎞️ **Applies FFmpeg processing** with:
  - Crop, pad, flip, LUTs, saturation tweaks
  - Top caption overlay (bounce-in + fade-out)
  - Multi-line support via `\n`
  - Up to **3 watermark layers** (bouncing, blurred, scrolling)
- 🎯 **Randomized watermark behavior** (position, opacity, order)
- 💬 **Caption pulled from rotating .txt** file
- 🧠 **Repost detection obfuscation** (looks edited in-app)
- 🔄 **Brand modularity** via `BRANDS` dict
- 🧩 **Integrates with full automation stacks**:
  - Google Sheets
  - Make.com
  - Dropbox / Google Drive
  - ChatGPT (captions/comments)
  - Instagram/Facebook posting

---

# ✨ FEATURES

## 🔁 BRAND PROFILES
Each brand gets its own:
- `.txt` caption bank
- Watermark pool (static/animated/blurred)
- LUT (`.CUBE` optional color grading)
- Scroll speed config
- Metadata label for tracking

## 🎬 VIDEO EDITING BREAKDOWN
- Top caption from `.txt`
- Caption + bar fades after 4–6s
- Bounce-in animation at start
- 1 animated watermark (random position + bounce)
- 1 blurred static watermark
- 1 optional top-scroll watermark
- Flip / crop / LUT applied per video

## 🔗 AUTOMATION SYSTEM SUPPORT
- Paste video links in **Google Sheets**
- Trigger workflow using **Make.com**
- Generate captions with **ChatGPT**
- Save files to **Dropbox/Drive**
- Auto-post via **Meta’s API**
- Update row status from `Pending` to `Posted`

---

# 📁 PROJECT STRUCTURE

```
project/
├── app.py                      # Flask server
├── assets/
│   ├── captions_brand1.txt     # Rotating captions
│   ├── watermark1.png          # Static/animated overlays
│   ├── LUT_file.CUBE           # Optional LUT
│   └── ...
```

---

# 🔧 BRAND CONFIG EXAMPLE

```python
"example_brand": {
    "metadata": "brand=example_brand",
    "lut": "LUT_file.CUBE",
    "scroll_speed": 100,
    "watermarks": [
        "wm1.png",
        "wm2.png",
        "wm3.png"
    ],
    "captions_file": "example_brand_captions.txt"
}
```

---

# 🛠️ HOW TO USE

## 1️⃣ START SERVER
```bash
python app.py
```

## 2️⃣ POST A REQUEST
```
POST http://localhost:5000/process/<brand>
```

**JSON Body Example:**
```json
{
  "video_url": "https://example.com/video.mp4"
}
```

## 3️⃣ OUTPUT
You’ll get a `.mp4` file with overlays, captions, and filters — ready to upload.

---

# ⚙️ SYSTEM REQUIREMENTS

- Python 3.8+
- FFmpeg (installed + in PATH)
- `wget`
- `flask`

---

# 🔁 FULL AUTOMATION FLOW (EXAMPLE)

1. 🧾 **New video link added to Google Sheet**
2. 🔁 **Make.com triggers Flask endpoint**
3. 💾 **Processed video saved to Dropbox**
4. 💬 **ChatGPT creates caption/comment**
5. 📲 **Video uploaded to IG/FB via API**
6. ✅ **Status updated in Google Sheet**

---

# 💡 TIPS & NOTES

- Each brand has its own `captions.txt`
- Supports emoji, line breaks, custom tones
- Caption fade/bounce customizable in FFmpeg
- Optional LUTs help build aesthetic identity
- Deployable to Render, RunPod, or self-hosted

---

> **This system is built for content re-creators, automation hustlers, and social media machines.**  
> Never edit a video manually again.
