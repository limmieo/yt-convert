import os
import uuid
import random
import subprocess
from flask import Flask, request, send_file, jsonify

app = Flask(__name__)

# === Brand Configs ===
BRANDS = {
    "thick_asian": {
        "captions_file": "assets/thick_asian_captions.txt",
        "lut": "assets/Cobi_3.CUBE",
        "scroll_speed": 80,
        "watermarks": [
            "assets/Thick_asian_watermark.png",
            "assets/Thick_asian_watermark_2.png",
            "assets/Thick_asian_watermark_3.png"
        ]
    },
    "gym_baddie": {
        "captions_file": "assets/gym_baddie_captions.txt",
        "lut": "assets/Cobi_3.CUBE",
        "scroll_speed": 120,
        "watermarks": [
            "assets/gym_baddie_watermark.png",
            "assets/gym_baddie_watermark_2.png",
            "assets/gym_baddie_watermark_3.png"
        ]
    },
    "polishedform": {
        "captions_file": "assets/polishedform_captions.txt",
        "lut": "assets/Cobi_3.CUBE",
        "scroll_speed": 100,
        "watermarks": [
            "assets/polished_watermark.png",
            "assets/polished_watermark_2.png",
            "assets/polished_watermark_3.png"
        ]
    }
}

# === Utility Functions ===
def get_random_line(filepath):
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            lines = [line.strip() for line in f if line.strip()]
        return random.choice(lines) if lines else ""
    except:
        return ""

def get_random_watermark(watermark_list):
    return random.choice(watermark_list)

# === Video Processing Route ===
@app.route("/process/<brand>", methods=["POST"])
def process_video(brand):
    data = request.get_json()
    if not data or "video_url" not in data:
        return jsonify({"error": "Missing 'video_url' in JSON body"}), 400

    if brand not in BRANDS:
        return jsonify({"error": f"Unsupported brand '{brand}'"}), 400

    config = BRANDS[brand]
    input_url = data["video_url"]
    file_id = str(uuid.uuid4())
    input_path = f"/tmp/{file_id}.mp4"
    output_path = f"/tmp/{file_id}_out.mp4"

    # Download the video
    subprocess.run(["curl", "-L", input_url, "-o", input_path], check=True)

    # Prepare overlays
    caption = get_random_line(config["captions_file"])
    watermark = get_random_watermark(config["watermarks"])
    font_path = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
    lut_path = config.get("lut", "")

    filter_chain = "[0:v]"
    filter_steps = []

    # Add LUT if valid
    if lut_path and os.path.isfile(lut_path):
        filter_steps.append(f"lut3d=file='{lut_path}'")

    # Add caption bar and text
    if caption:
        filter_steps.append("drawbox=y=0:color=black@0.8:width=iw:height=80:t=max")
        filter_steps.append(
            f"drawtext=fontfile='{font_path}':text='{caption}':"
            f"fontcolor=white:fontsize=48:x=(w-text_w)/2:y=20:box=0"
        )

    if filter_steps:
        filter_chain += "," + ",".join(filter_steps)
        filter_chain += "[base];"
        filter_chain += f"movie='{watermark}'[wm];[base][wm]overlay=20:20"
    else:
        filter_chain += f"[base];movie='{watermark}'[wm];[0:v][wm]overlay=20:20"

    # === FFmpeg Command ===
    cmd = [
        "ffmpeg", "-y",
        "-i", input_path,
        "-filter_complex", filter_chain,
        "-map", "0:v:0", "-map", "0:a?",
        "-c:v", "libx264", "-preset", "fast", "-crf", "18",
        "-c:a", "copy",
        "-movflags", "+faststart",
        output_path
    ]

    print("Running FFmpeg command:\n", " ".join(cmd))

    try:
        subprocess.run(cmd, check=True)
    except subprocess.CalledProcessError as e:
        return jsonify({"error": "FFmpeg failed", "details": str(e)}), 500

    return send_file(output_path, mimetype="video/mp4")

# === App Runner ===
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
