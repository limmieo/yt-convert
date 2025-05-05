# 🎞️ Faceless Video Branding Automation

This Flask app automates the transformation of reposted short-form videos into brand-aligned, original-feeling content — perfect for content aggregator pages like **Thick Asian Cosplay**, **Gym Baddie World**, and **PolishedForm**.

It applies subtle visual changes and overlays to:
- Help bypass repost detection
- Enhance engagement with dynamic captions
- Deliver a consistent brand identity across multiple verticals

---

## ✨ Features

✅ **Brand-Specific Configurations**  
Each brand has its own:
- Watermark pool (animated, blurred, or subtle)
- LUT filters (optional color grading)
- Caption tone and file
- Visual motion style (e.g., scroll speed)

✅ **Top Caption Bar with Effects**  
- Displays a caption from a rotating `.txt` file  
- Caption + black background **fade out together**
- Includes a smooth **bounce-in animation**
- Supports **multi-line captions** using `\n`

✅ **Watermark Enhancements**
- One animated watermark bounces around
- One static watermark is blurred to mimic reaction-style content
- One optional top watermark scrolls horizontally

✅ **Repost Resistance Built-in**
- Subtle transformations (flip, crop, pad, LUT, saturation)
- Unique per-video watermark positioning and opacity
- Mimics native app editing quirks (reaction/duet vibe)

✅ **Easy Expansion**  
Add a new brand in seconds by updating the `BRANDS` dict:
```python
"new_brand": {
    "metadata": "brand=new_brand",
    "lut": "Optional_LUT.CUBE",
    "scroll_speed": 100,
    "watermarks": ["watermark1.png", "watermark2.png"],
    "caption_file": "new_brand_captions.txt"
}
```

---

## 📁 Folder Structure

```
project/
├── app.py                   # Flask API logic
├── assets/
│   ├── thick_asian_captions.txt
│   ├── gym_baddie_captions.txt
│   ├── polishedform_captions.txt
│   ├── Thick_asian_watermark.png
│   ├── gym_baddie_watermark.png
│   ├── Cobi_3.CUBE
│   └── ...
```

---

## 🚀 Usage

**1. Run the server locally:**
```bash
python app.py
```

**2. POST a request to:**
```
http://localhost:5000/process/<brand>
```

**With JSON body:**
```json
{
  "video_url": "https://your-video-url.mp4"
}
```

**3. Output:**
Returns the fully processed `.mp4` with all overlays and edits applied.

---

## 🛠️ Requirements

- Python 3.8+
- FFmpeg (must be installed and available in PATH)
- `wget` (for video download)
- `flask`

---

## 💡 Example Brands
| Brand         | Caption Style         | Aesthetic               |
|---------------|------------------------|--------------------------|
| Thick Asian   | Flirty, playful, online baddie  | Cosplay, anime-inspired |
| Gym Baddie    | Confident, gym-glam energy      | Fitness & fashion       |
| PolishedForm  | Elevated, minimal, masculine    | Fashion-forward, clean  |
