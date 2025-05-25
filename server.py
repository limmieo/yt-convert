from flask import Flask, request, send_file
import subprocess
import uuid
import os
import random
import requests

app = Flask(__name__)

BRANDS = {
    "thick_asian": {
        "metadata": "brand=thick_asian",
        "lut": "Cobi_3.CUBE",
        "scroll_speed": 80,
        "watermarks": [
            "Thick_asian_watermark.png",
            "Thick_asian_watermark_2.png",
            "Thick_asian_watermark_3.png"
        ],
        "captions_file": "thick_asian_captions.txt"
    },
    "gym_baddie": {
        "metadata": "brand=gym_baddie",
        "lut": "Cobi_3.CUBE",
        "scroll_speed": 100,
        "watermarks": [
            "gym_baddie_watermark.png",
            "gym_baddie_watermark_2.png"
        ],
        "captions_file": "gym_baddie_captions.txt"
    },
    "polishedform": {
        "metadata": "brand=polishedform",
        "lut": "CineGreen.CUBE",
        "scroll_speed": 60,
        "watermarks": [
            "polishedform_mark.png",
            "polishedform_mark_alt.png"
        ],
        "captions_file": "polishedform_captions.txt"
    }
}

@app.route("/process/<brand>", methods=["POST"])
def process_video(brand):
    if brand not in BRANDS:
        return "Unknown brand", 400

    config = BRANDS[brand]
    data = request.get_json()
    video_url = data.get("video_url")

    if not video_url:
        return "No video_url provided", 400

    # Download video to temporary file
    input_path = f"/tmp/{uuid.uuid4()}.mp4"
    output_path = f"/tmp/{uuid.uuid4()}.mp4"

    try:
        with requests.get(video_url, stream=True, timeout=15) as r:
            r.raise_for_status()
            with open(input_path, "wb") as f:
                for chunk in r.iter_content(chunk_size=8192):
                    f.write(chunk)
    except Exception as e:
        return f"Failed to download video: {str(e)}", 500

    # Get random caption
    try:
        with open(config["captions_file"], "r", encoding="utf-8") as f:
            captions = [line.strip() for line in f if line.strip()]
            caption_text = random.choice(captions)
    except Exception as e:
        return f"Failed to read caption file: {str(e)}", 500

    font_path = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
    drawtext = (
        f"drawtext=fontfile='{font_path}':"
        f"text='{caption_text}':"
        "fontcolor=white:fontsize=32:x=(w-text_w)/2:y=(h-text_h)/2:"
        "enable='between(t,0,4)':"
        "alpha='if(lt(t,3),1,1-(t-3))'"
    )

    filter_complex = (
        f"[0:v]scale=1080:-2:force_original_aspect_ratio=decrease,"
        f"pad=1080:1920:(ow-iw)/2:(oh-ih)/2:black,"
        f"{drawtext},format=yuv420p[outv]"
    )

    cmd = [
        "ffmpeg",
        "-y",
        "-loglevel", "error",
        "-i", input_path,
        "-filter_complex", filter_complex,
        "-map", "[outv]",
        "-map", "0:a?",
        "-c:v", "libx264",
        "-crf", "18",
        "-preset", "fast",
        "-c:a", "aac",
        "-b:a", "128k",
        "-shortest",
        output_path
    ]

    try:
        subprocess.run(cmd, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

        if not os.path.exists(output_path) or os.path.getsize(output_path) < 1024:
            return "FFmpeg finished but output file is empty or corrupted.", 500

        return send_file(output_path, as_attachment=True)

    except subprocess.CalledProcessError as e:
        return f"FFmpeg error:\n{e.stderr.decode('utf-8')}", 500

    finally:
        if os.path.exists(input_path):
            os.remove(input_path)
        if os.path.exists(output_path):
            os.remove(output_path)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
