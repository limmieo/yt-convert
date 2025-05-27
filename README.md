> ⚠️ This project is proprietary and not open source. All rights reserved.  
> Do not reuse, republish, or fork without permission.  
> Built by Tony Destin LLC · tonydestinpromo@gmail.com

# 🚀 Faceless Video Branding Automation

A modular Flask-based backend for transforming short-form videos into **brand-consistent**, **repost-resistant**, and **platform-optimized** content — automatically and at scale.  
Ideal for creators, marketers, and automation engineers working on TikTok, Instagram Reels, or Facebook.

---

## ✅ What This System Does

- 🔽 Downloads videos via `wget`
- 🧠 Applies FFmpeg filters for repost obfuscation (crop, pad, saturation, etc.)
- 🎨 Adds up to **3 branded watermarks**
- 📝 Injects smart caption overlays from rotating `.txt` files
- 📽️ Appends brand-specific **outro clips** for visual signature
- 🔀 Randomizes watermark opacity, size, and animation patterns
- 🧩 Supports multiple brands from a single backend
- 🔗 Works with Make.com, Google Sheets, Dropbox, ChatGPT & Meta APIs

---

## ✨ Key Features

### 🔁 Modular Brand Profiles
Each brand can define its own:
- Watermarks (bouncing/static/scrolling)
- Caption text bank
- LUT (.CUBE) for color grading (optional)
- Outro video clip (optional)
- Metadata tagging

### 🎬 Video Editing Pipeline
- Crop, pad, and lightly scale each video
- Caption appears top-center with bounce + fade
- Randomized watermarks with animated effects
- Horizontal flip **disabled** to preserve visual/text integrity
- Outro stitched seamlessly at the end for select brands

---

## 🧠 Built for Automation

- Designed for **fully automated workflows**
- Compatible with:
  - Google Sheets as the video queue
  - Make.com or Zapier as trigger
  - ChatGPT for comment/caption gen
  - Dropbox / Google Drive for storage
  - Meta API for IG/FB posting

---

## 🛠 Brand Config Format

```python
"example_brand": {
    "metadata": "brand=example_brand",
    "lut": "example_lut.CUBE",
    "watermarks": [
        "wm1.png",
        "wm2.png",
        "wm3.png"
    ],
    "captions_file": "example_brand_captions.txt",
    "outro": "example_brand_outro.mp4"
}
```

---

## 📁 Project Structure

```
project/
├── server.py                  # Main working Flask server
├── assets/
│   ├── example_brand_outro.mp4
│   ├── example_lut.CUBE
│   ├── captions_brand.txt
│   ├── watermark1.png
│   └── ...
```

> `app.py` is being reworked to include a web-based settings editor — not currently in use.

---

## ⚙️ System Requirements

- Python 3.8+
- Flask
- FFmpeg (in PATH)
- `wget`

---

## 📦 Example API Request

```http
POST /process/<brand>
```

**JSON:**
```json
{
  "video_url": "https://example.com/video.mp4"
}
```

Response: processed `.mp4` with caption, branding, and outro.

---

## 🔁 Sample Automation Flow

1. ✅ Paste video link in Google Sheet  
2. 🔁 Make.com triggers the endpoint  
3. 🎞️ Flask server downloads & processes  
4. 💬 ChatGPT generates post copy  
5. 📤 Uploads to IG/FB  
6. ✅ Google Sheet row marked as "Posted"

---

## 💼 Why It Matters (for Employers)

This isn't a proof-of-concept — it powers **real monetized brands** today.

### Technical Strengths:
- FFmpeg animation and remuxing expertise
- Flask API development and deployment
- Modular backend design for multi-brand scaling
- Seamless integration with automation stacks

### Business Value:
- Reduces video editing time to **zero**
- Enables high-volume short-form content pipelines
- Bypasses repost detection algorithms
- Adds consistent brand identity across pages
- Powers multiple Instagram/Facebook brands 24/7

### Who This Helps:
- Social media growth teams
- Content automation startups
- Digital marketing agencies
- Creators managing faceless content
- Brand monetization tool builders

---

## 🧩 Roadmap (Coming Soon)

- [ ] Admin panel for real-time config via browser
- [ ] Support for vertical-to-square conversion
- [ ] Built-in logging & error dashboard
- [ ] Scheduled batch processing

---

**Built by creators, for creators.**  
**Stop editing. Start scaling.**
