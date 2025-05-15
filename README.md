🎞️ Faceless Video Branding Automation
This is a Flask-based backend for fully automating the processing, reformatting, and redistribution of short-form videos for content aggregation pages. It transforms ordinary reposts into brand-aligned, algorithm-resistant, and visually distinct content.

Built for scale and speed, this system is designed to be used with tools like Make.com, Google Sheets, ChatGPT, and Dropbox for end-to-end video automation — from link intake to final upload.

✅ What It Does (Full Overview)
✅ Downloads videos from URLs (via wget)

✅ Processes videos using FFmpeg to apply:

Visual tweaks (crop, pad, flip, saturation, LUTs)

Top caption overlays with black bars + bounce-in animation

Multi-line caption support with fade-out timing

Up to 3 watermarks: animated, static blurred, and top-scrolling

✅ Randomizes watermark position, opacity, and order

✅ Reads captions from .txt file per brand

✅ Mimics native in-app editing quirks (reaction-style overlays)

✅ Prevents repost detection using subtle obfuscation techniques

✅ Returns fully edited .mp4 for reposting

✅ Modular brand system lets you manage multiple styles with one server

✅ Integrates into automation tools to:

Pull links from Google Sheets

Track status (Pending → Posted)

Store final video in Dropbox or Drive

Auto-post to Instagram/Facebook using Graph API

Generate captions or comments with ChatGPT

🧠 Key Features
🔄 Brand Profiles
Each brand is defined with its own:

Caption .txt file (rotates entries)

Watermark folder (animated, static, blurred)

Optional LUT (.CUBE format)

Scroll speed for moving elements

Metadata identifier

🎬 Video Processing
Adds top caption bar from rotating file

Caption + black bar fade out after intro

Bounce-in caption entrance

Supports multiline (\n) captions

1 watermark bounces around screen

1 static blurred watermark to mimic reactions

1 optional top-scrolling watermark

Subtle visual edits (flip, crop, LUT, saturation) per video

Randomized effects to avoid pattern detection

Ensures every video looks slightly different, even if reposted

⚙️ Full Automation Support
Can be triggered and connected to:

Google Sheets — paste video links + track status

Make.com / Zapier — orchestrate the full pipeline

ChatGPT — generate captions/comments dynamically

Dropbox or Google Drive — auto-save processed videos

Instagram Graph API — auto-upload + add first comment

📁 Folder Structure
bash
Copy
Edit
project/
├── app.py                      # Flask server
├── assets/
│   ├── captions_brand1.txt     # Caption bank (rotated)
│   ├── watermark1.png          # Watermark files
│   ├── watermark2.png
│   ├── LUT.CUBE                # Optional color filter
│   └── ...
🧪 Example Brand Config
python
Copy
Edit
"example_brand": {
    "metadata": "brand=example_brand",
    "lut": "LUT_file.CUBE",
    "scroll_speed": 100,
    "watermarks": ["wm1.png", "wm2.png", "wm3.png"],
    "captions_file": "example_brand_captions.txt"
}
🚀 How to Use (Manually or via API)
1. Run the Server
bash
Copy
Edit
python app.py
2. POST a Request
bash
Copy
Edit
http://localhost:5000/process/<brand>
JSON body:

json
Copy
Edit
{
  "video_url": "https://example.com/your-video.mp4"
}
3. Output:
Returns a processed .mp4 file with all transformations applied, ready for upload.

🛠️ Requirements
Python 3.8+

ffmpeg (must be installed + available in PATH)

wget

flask

Works on local or cloud (e.g. Render, RunPod)

🔗 Automation Flow (Make.com)
Trigger: Watch new row in Google Sheet

Download: Send video_url to Flask /process/<brand> endpoint

Store: Upload processed .mp4 to Dropbox/Drive

Generate: Use ChatGPT to create caption or comment

Upload: Post video to Instagram or Facebook

Update: Change status in Google Sheet to Posted

🧠 Pro Tips
Use a separate .txt file for each brand’s captions

Caption bar supports emojis and line breaks

Adjust watermark opacity and duration inside the FFmpeg config

Auto-scale by deploying Flask on a Render or RunPod instance

