from flask import Flask, request, send_file, jsonify
import os
import subprocess
import uuid
import random
import yaml

app = Flask(__name__)
UPLOAD_FOLDER = "/tmp"
OUTPUT_FOLDER = "/tmp"

BRANDS = {
    "thick_asian": {
        "lut": "Cobi_3.CUBE",
        "watermarks": [
            "Thick_asian_watermark.png",
            "Thick_asian_watermark_2.png",
            "Thick_asian_watermark_3.png"
        ],
        "captions_file": "thick_asian_captions.txt"
    },
    "gym_baddie": {
        "lut": "GymBaddie_LUT.cube",
        "watermarks": [
            "gym_baddie_watermark.png",
            "gym_baddie_watermark_2.png"
        ],
        "captions_file": "gym_baddie_captions.txt"
    },
    "polishedform": {
        "lut": "PF_LUT.cube",
        "watermarks": [
            "pf_watermark_1.png",
            "pf_watermark_2.png"
        ],
        "captions_file": "pf_captions.txt"
    }
}

@app.route("/process/<brand>", methods=["POST"])
def process_video(brand):
    if brand not in BRANDS:
        return jsonify({"error": "Invalid brand"}), 400

    input_path = os.path.join(UPLOAD_FOLDER, f"{uuid.uuid4()}.mp4")
    output_path = os.path.join(OUTPUT_FOLDER, f"{uuid.uuid4()}_mid.mp4")
    file = request.files["video"]
    file.save(input_path)

    brand_cfg = BRANDS[brand]
    watermark = os.path.join("/opt/render/project/src/assets", random.choice(brand_cfg["watermarks"]))
    captions_path = os.path.join("/opt/render/project/src/assets", brand_cfg["captions_file"])
    lut_path = os.path.join("/opt/render/project/src/assets", brand_cfg["lut"])

    # Read random caption
    caption = "Default caption"
    if os.path.exists(captions_path):
        with open(captions_path, "r") as f:
            lines = [line.strip() for line in f if line.strip()]
            if lines:
                caption = random.choice(lines)

    # Construct FFmpeg command
    ffmpeg_cmd = [
        "ffmpeg", "-y", "-i", input_path,
        "-i", watermark,
        "-filter_complex",
        f"""
        [0:v]hflip,scale=1080:1920,setsar=1,format=yuv420p[lut_input];
        [lut_input]lut3d=file='{lut_path}'[base];
        [1:v]format=rgba,scale=200:-1[wm];
        [base][wm]overlay=W-w-30:H-h-30[watermarked];
        color=c=black@0.7:s=1080x160:d=1[bar];
        [watermarked][bar]overlay=0:0[with_bar];
        [with_bar]drawtext=text='{caption}':fontcolor=white:fontsize=40:x=(w-text_w)/2:y=20:box=1:boxcolor=black@0:boxborderw=5
        """,
        "-map", "[with_bar]",
        "-map", "0:a?", "-c:a", "copy",
        "-c:v", "libx264", "-b:v", "10000k", "-preset", "veryfast",
        "-movflags", "+faststart", output_path
    ]

    try:
        subprocess.run(" ".join(ffmpeg_cmd), shell=True, check=True)
    except subprocess.CalledProcessError as e:
        print("FFmpeg failed:", e)
        return jsonify({"error": "FFmpeg processing failed"}), 500

    if not os.path.exists(output_path):
        print("ERROR: Output file not created")
        return jsonify({"error": "Output video missing"}), 500

    return send_file(output_path, as_attachment=True)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
