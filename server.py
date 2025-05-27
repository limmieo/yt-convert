from flask import Flask, request, send_file, jsonify
import subprocess
import uuid
import os
import random

app = Flask(__name__)

# ─── Brand Configurations ──────────────────────────────────────────────────────
BRANDS = {
    "thick_asian": {
        "metadata": "brand=thick_asian",
        "lut": "Cobi_3.CUBE",
        "watermarks": ["Thick_asian_watermark.png"],
        "captions_file": "thick_asian_captions.txt",
        "outro": "thick_asian_outro.MOV"
    },
    "asian_travel": {
        "metadata": "brand=asian_travel",
        "lut": "Cobi_3.CUBE",
        "watermarks": ["asian_travel_watermark.png"],
        "captions_file": "asian_travel_captions.txt",
        "outro": "asian_travel_outro.MOV"
    }
}

@app.route("/process/<brand>", methods=["POST"])
def process(brand):
    if brand not in BRANDS:
        return "Invalid brand", 400

    brand_conf = BRANDS[brand]

    input_file = request.files["video"]
    input_path = f"/tmp/{uuid.uuid4()}.mp4"
    input_file.save(input_path)

    wm_file = random.choice(brand_conf["watermarks"])
    wm_path = f"/opt/render/project/src/assets/{wm_file}"
    caption = "Yes. Just yes."

    caption_cmd = f"drawtext=fontfile=/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf:text='{caption}':fontcolor=white:fontsize=28:box=1:boxcolor=black@0.6:boxborderw=10:x=(w-text_w)/2:y=h*0.45:enable='between(t,0,4)':alpha='if(lt(t,3),1,1-(t-3))'"

    mid_output = f"/tmp/{uuid.uuid4()}_mid.mp4"
    final_output = f"/tmp/{uuid.uuid4()}_final.mp4"

    ffmpeg_cmd = [
        "ffmpeg", "-y",
        "-i", input_path,
        "-i", wm_path,
        "-filter_complex",
        f"[1:v]scale=iw*0.9:ih*0.9[wm];[0:v]scale=iw:ih[vid];[vid][wm]overlay=W-w-10:H-h-10, {caption_cmd}",
        "-map", "[out]",
        "-map", "0:a?",
        "-c:v", "libx264",
        "-preset", "ultrafast",
        "-crf", "23",
        "-c:a", "aac",
        "-b:v", "8M",
        "-maxrate", "8M",
        "-bufsize", "16M",
        "-metadata", brand_conf["metadata"],
        mid_output
    ]

    ffmpeg_cmd[16] = f"[vid][wm]overlay=W-w-10:H-h-10[out];{caption_cmd}"  # Fix filter chain naming
    subprocess.run(ffmpeg_cmd, check=True)

    # Try to add outro
    outro_path = f"/opt/render/project/src/assets/{brand_conf.get('outro', '')}"
    concat_txt_path = f"/tmp/{uuid.uuid4()}.txt"

    if os.path.exists(outro_path):
        fixed_mid = f"/tmp/{uuid.uuid4()}_reencoded.mp4"

        # Re-encode for concat
        subprocess.run([
            "ffmpeg", "-y", "-i", mid_output,
            "-c", "copy", "-movflags", "+faststart", fixed_mid
        ], check=True)

        # Write concat file
        with open(concat_txt_path, "w") as f:
            f.write(f"file '{fixed_mid}'\nfile '{outro_path}'\n")

        subprocess.run([
            "ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", concat_txt_path,
            "-c", "copy", final_output
        ], check=True)

        os.remove(fixed_mid)
        os.remove(concat_txt_path)
        return send_file(final_output, mimetype="video/mp4")

    # If outro missing, return mid video
    return send_file(mid_output, mimetype="video/mp4")

if __name__ == "__main__":
    app.run(debug=True)
