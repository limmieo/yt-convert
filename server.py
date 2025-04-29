from flask import Flask, request, send_file
import subprocess
import uuid
import os
import random

app = Flask(__name__)

@app.route('/process', methods=['POST'])
def process_video():
    video_url = request.json['video_url']
    input_file = f"/tmp/{uuid.uuid4()}.mp4"
    output_file = f"/tmp/{uuid.uuid4()}_out.mp4"
    watermark = "watermark.png"  # Full opacity, transparent PNG

    # Download video
    subprocess.run(["wget", "-O", input_file, video_url])

    # === Watermark Smarts ===
    opacity = round(random.uniform(0.83, 0.91), 2)
    watermark_scale = random.uniform(0.85, 1.0)
    offset_x = random.randint(20, 50)
    offset_y = random.randint(200, 350)

    # FFmpeg Command
    command = [
        "ffmpeg", "-i", input_file,
        "-i", watermark,
        "-filter_complex",
        f"[1:v]scale=iw*{watermark_scale}:ih*{watermark_scale},format=rgba,colorchannelmixer=aa={opacity}[wm];"
        f"[0:v]scale=iw*0.9:ih*0.9[scaled];"
        f"[scaled][wm]overlay={offset_x}:{offset_y}[marked];"
        f"[marked]pad=iw/0.9:ih/0.9:(ow-iw)/2:(oh-ih)/2",
        "-ss", "1", "-t", "59",
        "-preset", "fast",
        output_file
    ]

    subprocess.run(command)

    return send_file(output_file, as_attachment=True)

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
