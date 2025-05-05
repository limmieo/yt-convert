from flask import Flask, render_template, request, jsonify, send_from_directory
import subprocess
import os
import uuid
import random
import threading
import time
import requests

app = Flask(__name__, static_folder="outputs")

# -----------------------------------------------------------------------------
# Configuration
# -----------------------------------------------------------------------------
BRANDS = {
    "thick_asian": {
        "metadata": "brand=thick_asian",
        "lut": "Cobi_3.CUBE",
        "scroll_speed": 80,
        "watermarks": [
            "Thick_asian_watermark.png",
            "Thick_asian_watermark_2.png",
            "Thick_asian_watermark_3.png"
        ]
    },
    "gym_baddie": {
        "metadata": "brand=gym_baddie",
        "lut": "Cobi_3.CUBE",
        "scroll_speed": 120,
        "watermarks": [
            "gym_baddie_watermark.png",
            "gym_baddie_watermark_2.png",
            "gym_baddie_watermark_3.png"
        ]
    },
    "polishedform": {
        "metadata": "brand=polishedform",
        "lut": None,
        "scroll_speed": 80,
        "watermarks": [
            "polished_watermark.png",
            "polished_watermark_2.png",
            "polished_watermark_3.png"
        ]
    }
}

# Shared state (progress + final filename)
progress_data = {
    "progress": 0,
    "output_filename": None
}


# -----------------------------------------------------------------------------
# Background processing
# -----------------------------------------------------------------------------
def process_video_async(video_url, brand_key):
    """
    Downloads, watermarks, encodes the video, and updates progress_data.
    When done, sets progress_data['output_filename'] to the final file.
    """
    cfg = BRANDS[brand_key]
    assets = os.path.join(os.getcwd(), "assets")

    # Temp files
    in_file  = f"/tmp/{uuid.uuid4()}.mp4"
    mid_file = f"/tmp/{uuid.uuid4()}_marked.mp4"
    out_file = f"outputs/{uuid.uuid4()}_final.mp4"  # will live under ./outputs

    try:
        # 1) Download
        with requests.get(video_url, stream=True) as r:
            r.raise_for_status()
            with open(in_file, "wb") as f:
                for chunk in r.iter_content(8192):
                    f.write(chunk)

        # 2) Simulate progress
        for i in range(0, 90):
            time.sleep(0.03)
            progress_data["progress"] = i

        # 3) Build FFmpeg filter_complex
        wm_choice = random.choice(cfg["watermarks"])
        watermark = os.path.join(assets, wm_choice)
        lut_filter = (
            f"lut3d='{os.path.join(assets, cfg['lut'])}',"
            if cfg["lut"] else ""
        )

        # random styling
        op_b = round(random.uniform(0.6, 0.7), 2)
        op_s = round(random.uniform(0.85, 0.95), 2)
        op_t = round(random.uniform(0.4, 0.6), 2)
        sc_b = random.uniform(0.85, 1.0)
        sc_s = random.uniform(1.1, 1.25)
        sc_t = random.uniform(0.9, 1.1)
        fr = round(random.uniform(29.87, 30.1), 3)

        fc = (
            f"[1:v]split=3[wm_b][wm_s][wm_t];"
            f"[wm_b]scale=iw*{sc_b}:ih*{sc_b},format=rgba,"
            f"colorchannelmixer=aa={op_b}[b_out];"
            f"[wm_s]scale=iw*{sc_s}:ih*{sc_s},format=rgba,"
            f"colorchannelmixer=aa={op_s}[s_out];"
            f"[wm_t]scale=iw*{sc_t}:ih*{sc_t},format=rgba,"
            f"colorchannelmixer=aa={op_t}[t_out];"
            f"[0:v]hflip,setpts=PTS+0.001/TB,"
            f"scale=iw*0.98:ih*0.98,"
            f"crop=iw-8:ih-8:(iw-8)/2:(ih-8)/2,"
            f"{lut_filter}"
            f"pad=iw+16:ih+16:(ow-iw)/2:(oh-ih)/2,"
            f"eq=brightness=0.01:contrast=1.02:saturation=1.03[base];"
            f"[base][b_out]overlay=x='main_w-w-30':y='main_h-h-60'[st1];"
            f"[st1][s_out]overlay=x='(main_w-w)/2':y='main_h-h-10'[st2];"
            f"[st2][t_out]overlay="
            f"x='mod(t*{cfg['scroll_speed']},main_w+w)-w':y=20,"
            f"scale='trunc(iw/2)*2:trunc(ih/2)*2'[final]"
        )

        # 4) Run ffmpeg
        subprocess.run([
            "ffmpeg", "-y", "-i", in_file, "-i", watermark,
            "-filter_complex", fc,
            "-map", "[final]", "-map", "0:a?",
            "-map_metadata", "-1", "-map_chapters", "-1",
            "-r", str(fr),
            "-g", "48", "-keyint_min", "24", "-sc_threshold", "0",
            "-b:v", "5M", "-maxrate", "5M", "-bufsize", "10M",
            "-preset", "ultrafast",
            "-t", "40",
            "-c:v", "libx264", "-c:a", "copy",
            "-metadata", cfg["metadata"],
            mid_file
        ], check=True)

        # 5) Final copy
        subprocess.run([
            "ffmpeg", "-y", "-i", mid_file,
            "-map_metadata", "-1", "-map_chapters", "-1",
            "-c:v", "copy", "-c:a", "copy",
            "-metadata", cfg["metadata"],
            out_file
        ], check=True)

        # done!
        progress_data["progress"] = 100
        progress_data["output_filename"] = os.path.basename(out_file)

    except Exception as e:
        print("Processing error:", e)
        progress_data["output_filename"] = None

    finally:
        for f in (in_file, mid_file):
            try: os.remove(f)
            except: pass


# -----------------------------------------------------------------------------
# Routes
# -----------------------------------------------------------------------------
@app.route('/')
def index():
    return render_template('index.html', brands=BRANDS)


@app.route('/process', methods=['POST'])
def start_processing():
    url   = request.form.get('video_url','').strip()
    brand = request.form.get('brand','')
    if not url or brand not in BRANDS:
        return render_template('index.html', brands=BRANDS), 400

    # reset shared state
    progress_data["progress"] = 0
    progress_data["output_filename"] = None

    # start background job
    t = threading.Thread(target=process_video_async, args=(url, brand))
    t.daemon = True
    t.start()

    return render_template('processing.html')


@app.route('/progress', methods=['GET'])
def progress():
    return jsonify(progress=progress_data["progress"],
                   filename=progress_data["output_filename"])


@app.route('/download/<path:fn>')
def download(fn):
    # serves from ./outputs
    return send_from_directory("outputs", fn, as_attachment=True)


if __name__ == '__main__':
    os.makedirs("outputs", exist_ok=True)
    app.run(debug=True)
