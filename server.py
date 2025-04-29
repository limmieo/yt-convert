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
    
    # Randomly pick a watermark
    watermark_choice = random.choice(["watermark.png", "watermark_2.png", "watermark_3.png"])

    # Download the video
    subprocess.run(["wget", "-O", input_file, video_url])

    # Random settings
    opacity_main = round(random.uniform(0.83, 0.91), 2)
    opacity_secondary = round(random.uniform(0.75, 0.83), 2)
    scale_main = random.uniform(0.85, 1.0)
    scale_secondary = random.uniform(0.8, 0.95)
    offset_x_main = random.randint(20, 50)
    offset_y_main = random.randint(350, 700)  # ⬅ Avoid Instagram top bar
    offset_x_secondary = random.randint(20, 40)
    offset_y_secondary = random.randint(20, 50)

    framerate = round(random.uniform(29.97, 30.03), 2)

    # FFmpeg Command
    command = [
        "ffmpeg", "-i", input_file,
        "-i", watermark_choice,
        "-filter_complex",
        f"[1:v]split=2[wm1][wm2];"
        f"[wm1]scale=iw*{scale_main}:ih*{scale_main},format=rgba,colorchannelmixer=aa={opacity_main}[wm1out];"
        f"[wm2]scale=iw*{scale_secondary}:ih*{scale_secondary},format=rgba,colorchannelmixer=aa={opacity_secondary}[wm2out];"
        f"[0:v]scale=iw*0.9:ih*0.9[scaled];"
        f"[scaled][wm1out]overlay={offset_x_main}:{offset_y_main}[step1];"
        f"[step1][wm2out]overlay={offset_x_secondary}:H-h-{offset_y_secondary}[marked];"
        f"[marked]pad=iw/0.9:ih/0.9:(ow-iw)/2:(oh-ih)/2",
        "-r", str(framerate),
        "-ss", "1", "-t", "59",
        "-preset", "fast",
        output_file
    ]

    subprocess.run(command)

    return send_file(output_file, as_attachment=True)

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
