from flask import Flask, request, send_file
import subprocess
import uuid
import os
import random

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
        "lut": "Cinematic_2.CUBE",
        "scroll_speed": 120,
        "watermarks": [
            "gym_baddie_watermark.png",
            "gym_baddie_watermark_2.png"
        ],
        "captions_file": "gym_baddie_captions.txt"
    },
    "polishedform": {
        "metadata": "brand=polishedform",
        "lut": "Soft_Polish.CUBE",
        "scroll_speed": 60,
        "watermarks": [
            "polishedform_watermark.png"
        ],
        "captions_file": "polishedform_captions.txt"
    }
}

@app.route('/process/<brand>', methods=['POST'])
def process_video(brand):
    if brand not in BRANDS:
        return f"Unknown brand: {brand}", 400

    brand_config = BRANDS[brand]

    video = request.files['video']
    filename = f"/tmp/{uuid.uuid4()}.mp4"
    video.save(filename)

    watermark = random.choice(brand_config["watermarks"])
    watermark_path = os.path.join("assets", watermark)
    output_file = filename.replace(".mp4", "_mid.mp4")
    caption_text = get_random_caption(brand_config["captions_file"])
    font_path = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"

    ffmpeg_cmd = [
        "ffmpeg", "-y", "-i", filename,
        "-i", watermark_path,
        "-filter_complex",
        f"[0:v]hflip,scale=1080:1920,setdar=9/16,format=yuv420p[lut];"
        f"[lut]lut3d='{brand_config['lut']}'[base];"
        f"[1:v]scale=200:40[wm];"
        f"[base][wm]overlay=W-w-20:H-h-20[watermarked];"
        f"[watermarked]drawtext=fontfile={font_path}:text='{caption_text}':x=(w-text_w)/2:y=50:fontcolor=white:fontsize=36:box=1:boxcolor=black@0.5:boxborderw=10",
        "-c:v", "libx264", "-b:v", "10000k", "-preset", "faster", "-movflags", "+faststart",
        "-c:a", "copy",
        output_file
    ]

    subprocess.run(ffmpeg_cmd, check=True)
    return send_file(output_file, mimetype="video/mp4")

def get_random_caption(captions_file):
    path = os.path.join("assets", captions_file)
    with open(path, 'r', encoding='utf-8') as f:
        lines = [line.strip() for line in f if line.strip()]
    return random.choice(lines)

if __name__ == '__main__':
    app.run(debug=False, host="0.0.0.0", port=10000)
