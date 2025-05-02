from flask import Flask, request, send_file
import subprocess
import uuid
import os
import random

app = Flask(__name__)

@app.route('/process', methods=['POST'])
def process_video():
    video_url = request.json.get('video_url')
    if not video_url:
        return {"error": "Missing video_url in request."}, 400

    input_file = f"/tmp/{uuid.uuid4()}.mp4"
    watermarked_file = f"/tmp/{uuid.uuid4()}_marked.mp4"
    final_output = f"/tmp/{uuid.uuid4()}_final.mp4"

    try:
        # Watermark selection
        watermark_choice = random.choice(["watermark.png", "watermark_2.png", "watermark_3.png"])

        # Download video
        subprocess.run([
            "wget", "--header=User-Agent: Mozilla/5.0", "-O", input_file, video_url
        ], check=True)

        # Watermark settings
        opacity_main = round(random.uniform(0.83, 0.91), 2)
        opacity_secondary = round(random.uniform(0.75, 0.83), 2)
        scale_main = random.uniform(0.95, 1.1)
        scale_secondary = random.uniform(0.8, 0.95)

        offset_x_secondary = random.randint(20, 40)
        offset_y_secondary = random.randint(20, 50)

        # Time-based bounce speed
        dx = round(random.uniform(30, 80), 2)
        dy = round(random.uniform(30, 80), 2)

        framerate = round(random.uniform(29.87, 30.1), 3)

        # FFmpeg command with animated bouncing watermark
        command = [
            "ffmpeg", "-i", input_file,
            "-i", watermark_choice,
            "-filter_complex",
            f"[1:v]split=2[wm1][wm2];"
            f"[wm1]scale=iw*{scale_main}:ih*{scale_main},format=rgba,colorchannelmixer=aa={opacity_main}[wm1out];"
            f"[wm2]scale=iw*{scale_secondary}:ih*{scale_secondary},format=rgba,colorchannelmixer=aa={opacity_secondary}[wm2out];"
            f"[0:v]hflip,"
            f"crop=iw-4:ih-4:(iw-4)*{random.random()}:(ih-4)*{random.random()},"
            f"pad=iw+4:ih+4:(ow-iw)/2:(oh-ih)/2,"
            f"eq=brightness=0.01:contrast=1.02:saturation=1.03,"
            f"scale=iw*0.9:ih*0.9[scaled];"
            f"[scaled][wm1out]overlay="
            f"x='abs(mod(t*{dx},(main_w-w)*2)-(main_w-w))':"
            f"y='abs(mod(t*{dy},(main_h-h)*2)-(main_h-h))'[step1];"
            f"[step1][wm2out]overlay={offset_x_secondary}:H-h-{offset_y_secondary}[marked];"
            f"[marked]pad=iw/0.9:ih/0.9:(ow-iw)/2:(oh-ih)/2",
            "-r", str(framerate),
            "-ss", "0", "-t", "40",
            "-preset", "ultrafast",
            watermarked_file
        ]

        subprocess.run(command, check=True)

        # Strip metadata
        subprocess.run([
            "ffmpeg", "-i", watermarked_file,
            "-map_metadata", "-1",
            "-c:v", "copy", "-c:a", "aac", "-b:a", "128k",
            final_output
        ], check=True)

        return send_file(final_output, as_attachment=True)

    except subprocess.CalledProcessError as e:
        return {"error": f"FFmpeg error: {str(e)}"}, 500
    except Exception as e:
        return {"error": f"Unexpected error: {str(e)}"}, 500

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
