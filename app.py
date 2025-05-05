from flask import Flask, render_template, request, jsonify
import subprocess
import os
import uuid
import random
import threading
import time
import requests

app = Flask(__name__)

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

# This dict holds the current progress (0–100)
progress_data = {"progress": 0}


# -----------------------------------------------------------------------------
# Background processing function
# -----------------------------------------------------------------------------
def process_video_in_background(video_url, selected_brand, progress_callback):
    """
    Downloads the video, simulates progress, applies FFmpeg filters,
    and writes out a finished file path.
    """
    # generate unique temp filenames
    input_file        = f"tmp_{uuid.uuid4()}.mp4"
    watermarked_file  = f"tmp_{uuid.uuid4()}_marked.mp4"
    final_output      = f"tmp_{uuid.uuid4()}_final.mp4"

    try:
        cfg           = BRANDS[selected_brand]
        metadata_tag  = cfg["metadata"]
        scroll_speed  = cfg["scroll_speed"]

        # pick a random watermark and optional LUT
        assets_path   = os.path.join(os.getcwd(), "assets")
        wm_choice     = random.choice(cfg["watermarks"])
        watermark     = os.path.join(assets_path, wm_choice)
        lut_path      = os.path.join(assets_path, cfg["lut"]) if cfg["lut"] else None
        lut_filter    = f"lut3d='{lut_path}'," if lut_path else ""

        # 1) Download the video
        with requests.get(video_url, stream=True) as r:
            r.raise_for_status()
            with open(input_file, "wb") as f:
                for chunk in r.iter_content(chunk_size=8192):
                    f.write(chunk)

        # 2) Simulate progress for the UI
        for i in range(101):
            time.sleep(0.05)
            progress_callback(i)

        # 3) Build your FFmpeg filter_complex
        opacity_bounce  = round(random.uniform(0.6, 0.7), 2)
        opacity_static  = round(random.uniform(0.85, 0.95), 2)
        opacity_topleft = round(random.uniform(0.4, 0.6), 2)

        scale_bounce    = random.uniform(0.85, 1.0)
        scale_static    = random.uniform(1.1, 1.25)
        scale_topleft   = random.uniform(0.9, 1.1)

        framerate       = round(random.uniform(29.87, 30.1), 3)

        filter_complex = (
            # split watermark into three streams
            f"[1:v]split=3[wm_bounce][wm_static][wm_top];"
            # bouncing watermark (now static bottom-right with a tiny sin() shift)
            f"[wm_bounce]scale=iw*{scale_bounce}:ih*{scale_bounce},"
            f"format=rgba,colorchannelmixer=aa={opacity_bounce}[bounce_out];"
            # static center-bottom watermark
            f"[wm_static]scale=iw*{scale_static}:ih*{scale_static},"
            f"format=rgba,colorchannelmixer=aa={opacity_static}[static_out];"
            # top-left scrolling watermark
            f"[wm_top]scale=iw*{scale_topleft}:ih*{scale_topleft},"
            f"format=rgba,colorchannelmixer=aa={opacity_topleft}[top_out];"
            # main video chain: flip, tiny timestamp tweak, shrink, crop, pad, LUT, color
            f"[0:v]hflip,setpts=PTS+0.001/TB,"
            f"scale=iw*0.98:ih*0.98,"
            f"crop=iw-8:ih-8:(iw-8)/2:(ih-8)/2,"
            f"{lut_filter}"
            f"pad=iw+16:ih+16:(ow-iw)/2:(oh-ih)/2,"
            f"eq=brightness=0.01:contrast=1.02:saturation=1.03[base];"
            # overlay bottom-right watermark
            f"[base][bounce_out]overlay="
            f"x='main_w-w-30+10*sin(t*2)':y='main_h-h-60+5*sin(t*2)'[step1];"
            # overlay center-bottom watermark
            f"[step1][static_out]overlay="
            f"x='(main_w-w)/2':y='main_h-h-10'[step2];"
            # overlay top-left watermark as a news-ticker
            f"[step2][top_out]overlay="
            f"x='mod(t*{scroll_speed}, main_w + w) - w':y=20,"
            # enforce even dimensions
            f"scale='trunc(iw/2)*2:trunc(ih/2)*2'[final]"
        )

        # 4) Run ffmpeg: apply filters + copy audio + strip metadata
        subprocess.run([
            "ffmpeg", "-i", input_file,
            "-i", watermark,
            "-filter_complex", filter_complex,
            "-map", "[final]", "-map", "0:a?",
            "-map_metadata", "-1", "-map_chapters", "-1",
            "-r", str(framerate),
            "-g", "48", "-keyint_min", "24", "-sc_threshold", "0",
            "-b:v", "5M", "-maxrate", "5M", "-bufsize", "10M",
            "-preset", "ultrafast",
            "-t", "40",
            "-c:v", "libx264", "-c:a", "copy",
            "-metadata", metadata_tag,
            watermarked_file
        ], check=True)

        # 5) Final pass to re-apply metadata strip and copy streams again
        subprocess.run([
            "ffmpeg", "-i", watermarked_file,
            "-map_metadata", "-1", "-map_chapters", "-1",
            "-c:v", "copy", "-c:a", "copy",
            "-metadata", metadata_tag,
            final_output
        ], check=True)

        return final_output

    except subprocess.CalledProcessError as e:
        print("FFmpeg error:", e)
        return None
    except Exception as e:
        print("Unexpected error:", e)
        return None
    finally:
        # cleanup temp files
        for f in (input_file, watermarked_file):
            if os.path.exists(f):
                os.remove(f)


# -----------------------------------------------------------------------------
# Routes
# -----------------------------------------------------------------------------
@app.route('/')
def index():
    return render_template('index.html', brands=BRANDS)


@app.route('/process', methods=['POST'])
def process_video_route():
    global progress_data

    video_url      = request.form.get('video_url', '').strip()
    selected_brand = request.form.get('brand', '')

    if not video_url or selected_brand not in BRANDS:
        return render_template('index.html', brands=BRANDS), 400

    # reset the shared progress
    progress_data["progress"] = 0

    def update_progress(p):
        progress_data["progress"] = p

    # kick off background processing
    t = threading.Thread(
        target=lambda: process_video_in_background(video_url, selected_brand, update_progress)
    )
    t.daemon = True
    t.start()

    return render_template('processing.html')


@app.route('/progress', methods=['GET'])
def get_progress():
    return jsonify(progress=progress_data["progress"])


# -----------------------------------------------------------------------------
# Run the app
# -----------------------------------------------------------------------------
if __name__ == '__main__':
    app.run(debug=True)
