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
    watermarked_file = f"/tmp/{uuid.uuid4()}_watermarked.mp4"
    final_output = f"/tmp/{uuid.uuid4()}_final.mp4"

    # Pick a watermark file at random
    watermark_choice = random.choice(["watermark.png", "watermark_2.png", "watermark_3.png"])

    # Download video with spoofed user-agent
    subprocess.run([
        "wget", "--header=User-Agent: Mozilla/5.0",
        "-O", input_file, video_url
    ], check=True)

    # Watermark + styling variables
    opacity_main = round(random.uniform(0.83, 0.91), 2)
    opacity_secondary = round(random.uniform(0.75, 0.83), 2)
    scale_main = random.uniform(0.85, 1.05)
    scale_secondary = random.uniform(0.8, 0.95)
    offset_x_main = random.randint(20, 50)
    offset_y_main = random.randint(350, 700)
    offset_x_secondary = random.randint(30, 100)
    offset_y_secondary = random.randint(30, 120)

    # FFmpeg processing
  dx = random.randint(2, 4)
dy = random.randint(2, 4)
W = random.randint(0, 100)
H = random.randint(0, 100)
X = random.randint(1, 3)

command = [
    "ffmpeg", "-i", input_file,
    "-i", watermark_choice,
    "-filter_complex",
    f"[1:v]split=2[wm1][wm2];"
    f"[wm1]scale=iw*{scale_main}:ih*{scale_main},format=rgba,colorchannelmixer=aa={opacity_main}[wm1out];"
    f"[wm2]scale=iw*{scale_secondary}:ih*{scale_secondary},format=rgba,colorchannelmixer=aa={opacity_secondary}[wm2out];"
    f"[0:v]hflip,"
    f"crop=iw-6:ih-6:(iw-6)*{random.random()}:(ih-6)*{random.random()},"
    f"pad=iw+6:ih+6:(ow-iw)/2:(oh-ih)/2,"
    f"eq=brightness=0.015:contrast=1.04:saturation=1.05,"
    f"noise=alls=4:allf=t+u,"
    f"gblur=sigma=0.8,"
    f"scale=iw*0.9:ih*0.9[scaled];"
    f"[scaled][wm1out]overlay="
    f"x='if(eq(mod(n\\,{X})\\,0)\\,{W}\\,if(gte(x+{dx}\\,main_w-w)\\,-{dx}\\,x+{dx}))':"
    f"y='if(eq(mod(n\\,{X})\\,0)\\,{H}\\,if(gte(y+{dy}\\,main_h-h)\\,-{dy}\\,y+{dy}))'[step1];"
    f"[step1][wm2out]overlay={offset_x_secondary}:{offset_y_secondary}[marked];"
    f"[marked]pad=iw/0.9:ih/0.9:(ow-iw)/2:(oh-ih)/2",
    "-ss", "1", "-t", "59",
    "-r", "29.87",
    "-preset", "ultrafast",
    watermarked_file
]


    subprocess.run(command, check=True)

    # Scrub metadata
    subprocess.run([
        "ffmpeg", "-i", watermarked_file,
        "-map_metadata", "-1",
        "-c:v", "copy", "-c:a", "aac", "-b:a", "128k",
        final_output
    ], check=True)

    return send_file(final_output, as_attachment=True)

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
