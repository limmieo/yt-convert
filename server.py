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
    metadata_tag = "brand=thick_asian"

    try:
        watermark_choice = random.choice(["watermark.png", "watermark_2.png", "watermark_3.png"])

        subprocess.run([
            "wget", "--header=User-Agent: Mozilla/5.0", "-O", input_file, video_url
        ], check=True)

        # Watermark styles
        opacity_bounce = round(random.uniform(0.5, 0.6), 2)
        opacity_static = round(random.uniform(0.85, 0.95), 2)
        opacity_topleft = round(random.uniform(0.4, 0.6), 2)

        scale_bounce = random.uniform(0.7, 0.85)
        scale_static = random.uniform(1.05, 1.2)
        scale_topleft = random.uniform(0.6, 0.75)

        dx = round(random.uniform(20, 40), 2)
        dy = round(random.uniform(20, 40), 2)
        delay_x = round(random.uniform(0.2, 1.0), 2)
        delay_y = round(random.uniform(0.2, 1.0), 2)

        framerate = round(random.uniform(29.87, 30.1), 3)

        command = [
            "ffmpeg", "-i", input_file,
            "-i", watermark_choice,
            "-filter_complex",
            f"[1:v]split=3[wm_bounce][wm_static][wm_top];"
            f"[wm_bounce]scale=iw*{scale_bounce}:ih*{scale_bounce},format=rgba,colorchannelmixer=aa={opacity_bounce}[bounce_out];"
            f"[wm_static]scale=iw*{scale_static}:ih*{scale_static},format=rgba,colorchannelmixer=aa={opacity_static}[static_out];"
            f"[wm_top]scale=iw*{scale_topleft}:ih*{scale_topleft},format=rgba,colorchannelmixer=aa={opacity_topleft}[top_out];"
            f"[0:v]hflip,"
            f"crop=iw-4:ih-4:(iw-4)*{random.random()}:(ih-4)*{random.random()},"
            f"pad=iw+4:ih+4:(ow-iw)/2:(oh-ih)/2,"
            f"eq=brightness=0.01:contrast=1.02:saturation=1.03,"
            f"scale=iw*0.9:ih*0.9[scaled];"
            f"[scaled][bounce_out]overlay="
            f"x='abs(mod((t+{delay_x})*{dx},(main_w-w)*2)-(main_w-w))':"
            f"y='abs(mod((t+{delay_y})*{dy},(main_h-h)*2)-(main_h-h))'[step1];"
            f"[step1][static_out]overlay="
            f"x='(main_w-w)/2':y='main_h-h-30'[step2];"
            f"[step2][top_out]overlay="
            f"x=20:y=20[final];"
            f"[final]pad=iw/0.9:ih/0.9:(ow-iw)/2:(oh-ih)/2",
            "-r", str(framerate),
            "-ss", "0", "-t", "40",
            "-preset", "ultrafast",
            "-metadata", metadata_tag,
            watermarked_file
        ]

        subprocess.run(command, check=True)

        subprocess.run([
            "ffmpeg", "-i", watermarked_file,
            "-map_metadata", "0",
            "-c:v", "copy", "-c:a", "aac", "-b:a", "128k",
            "-metadata", metadata_tag,
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
