from flask import Flask, request, send_file, jsonify
import subprocess
import uuid
import os
import random
import shutil

app = Flask(__name__)

# ─── Brand Configuration ───────────────────────────────────────────────────────
BRANDS = {
    "thick_asian": {
        "lut": "Cobi_3.CUBE",
        "watermarks": [
            "Thick_asian_watermark.png",
            "Thick_asian_watermark_2.png",
            "Thick_asian_watermark_3.png"
        ],
        "captions_file": "thick_asian_captions.txt",
        "outro": "outro_thick_asian.mp4"
    },
    "gym_baddie": {
        "lut": "Cobi_3.CUBE",
        "watermarks": [
            "gym_baddie_watermark.png",
            "gym_baddie_watermark_2.png",
            "gym_baddie_watermark_3.png"
        ],
        "captions_file": "gym_baddie_captions.txt",
        "outro": "outro_gym_baddie.mp4"
    },
    "polishedform": {
        "lut": "minimal_lut.CUBE",
        "watermarks": [
            "polishedform_wm1.png",
            "polishedform_wm2.png"
        ],
        "captions_file": "polishedform_captions.txt",
        "outro": "outro_polishedform.mp4"
    }
}

# ─── Endpoint ───────────────────────────────────────────────────────────────────
@app.route('/process/<brand>', methods=['POST'])
def process_video(brand):
    if brand not in BRANDS:
        return jsonify({"error": "Invalid brand"}), 400

    if 'video' not in request.files:
        return jsonify({"error": "Missing video file"}), 400

    video = request.files['video']
    input_path = f"/tmp/{uuid.uuid4()}.mp4"
    video.save(input_path)

    config = BRANDS[brand]
    caption = random_caption(config['captions_file'])
    watermark_path = random.choice(config['watermarks'])
    lut_path = config['lut']
    outro_path = config['outro']

    mid_mp4 = f"/tmp/{uuid.uuid4()}_mid.mp4"
    outro_mp4 = f"/tmp/{uuid.uuid4()}_outro.mp4"
    concat_list = f"/tmp/{uuid.uuid4()}_list.txt"
    final_mp4 = f"/tmp/{uuid.uuid4()}_final.mp4"

    # Step 1: Process original video
    ffmpeg_cmd = [
        "ffmpeg",
        "-i", input_path,
        "-i", watermark_path,
        "-vf",
        f"format=yuv420p,lut3d='{lut_path}',"
        f"drawtext=fontfile=/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf:"
        f"text='{caption}':x=(w-text_w)/2:y=30:fontsize=32:fontcolor=white:"
        f"box=1:boxcolor=black@0.5:boxborderw=10,"
        f"overlay=W-w-random(1)*50:H-h-random(1)*50",
        "-preset", "ultrafast",
        "-crf", "18",
        "-movflags", "+faststart",
        mid_mp4
    ]
    subprocess.run(ffmpeg_cmd, check=True)

    # Step 2: Re-encode outro to match input
    ffmpeg_outro_cmd = [
        "ffmpeg", "-i", outro_path,
        "-c:v", "libx264", "-crf", "18", "-preset", "ultrafast",
        "-c:a", "aac", "-movflags", "+faststart",
        outro_mp4
    ]
    subprocess.run(ffmpeg_outro_cmd, check=True)

    # Step 3: Concat processed + outro
    with open(concat_list, "w") as f:
        f.write(f"file '{mid_mp4}'\n")
        f.write(f"file '{outro_mp4}'\n")

    ffmpeg_concat_cmd = [
        "ffmpeg", "-f", "concat", "-safe", "0", "-i", concat_list,
        "-c", "copy", final_mp4
    ]
    subprocess.run(ffmpeg_concat_cmd, check=True)

    return send_file(final_mp4, mimetype='video/mp4')

# ─── Caption Utility ───────────────────────────────────────────────────────────
def random_caption(file_path):
    with open(file_path, "r", encoding="utf-8") as f:
        captions = [line.strip() for line in f if line.strip()]
    return random.choice(captions)

# ─── Run ────────────────────────────────────────────────────────────────────────
if __name__ == '__main__':
    app.run(debug=False, host='0.0.0.0', port=5000)
