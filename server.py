from flask import Flask, request, send_file
import subprocess
import uuid
import os

app = Flask(__name__)

@app.route('/process', methods=['POST'])
def process_video():
    video_url = request.json['video_url']
    input_file = f"/tmp/{uuid.uuid4()}.mp4"
    output_file = f"/tmp/{uuid.uuid4()}_out.mp4"
    watermark = "watermark.png"  # Put your watermark file here

    subprocess.run(["wget", "-O", input_file, video_url])

    subprocess.run([
        "ffmpeg", "-i", input_file,
        "-i", watermark,
        "-filter_complex",
        "scale=iw*0.9:ih*0.9,pad=iw/0.9:ih/0.9:(ow-iw)/2:(oh-ih)/2 [base]; [base][1] overlay=W-w-20:H-h-20",
        "-ss", "1", "-t", "59",
        "-preset", "fast",
        output_file
    ])

    return send_file(output_file, as_attachment=True)

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
