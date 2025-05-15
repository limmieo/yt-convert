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

