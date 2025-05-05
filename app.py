from flask import Flask, render_template, request, jsonify
import subprocess
import os
import uuid
import random
import threading
import time

app = Flask(__name__)

# Brands configuration
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

# Progress data for tracking the process
progress_data = {"progress": 0}

# Function to simulate video processing and update progress
def process_video_in_background(video_url, selected_brand, progress_callback):
    input_file = f"/tmp/{uuid.uuid4()}.mp4"
    watermarked_file = f"/tmp/{uuid.uuid4()}_marked.mp4"
    final_output = f"/tmp/{uuid.uuid4()}_final.mp4"

    try:
        config = BRANDS[selected_brand]
        metadata_tag = config["metadata"]
        scroll_speed = config["scroll_speed"]

        assets_path = os.path.join(os.getcwd(), "assets")
        watermark_choice = os.path.join(assets_path, random.choice(config["watermarks"]))
        lut_path = os.path.join(assets_path, config["lut"]) if config["lut"] else None

        # Download video
        subprocess.run([
            "wget", "--header=User-Agent: Mozilla/5.0", "-O", input_file, video_url
        ], check=True)

        # Simulate progress (for demonstration purposes)
        for i in range(101):
            time.sleep(0.1)  # Simulate processing delay
            progress_callback(i)

        # Apply video processing logic
        opacity_bounce = round(random.uniform(0.6, 0.7), 2)
        opacity_static = round(random.uniform(0.85, 0.95), 2)
        opacity_topleft = round(random.uniform(0.4, 0.6), 2)

        scale_bounce = random.uniform(0.85, 1.0)
        scale_static = random.uniform(1.1, 1.25)
        scale_topleft = random.uniform(0.9, 1.1)

        framerate = round(random.uniform(29.87, 30.1), 3)
        lut_filter = f"lut3d='{lut_path}'," if lut_path else ""

        filter_complex = (
            f"[1:v]split=3[wm_bounce][wm_static][wm_top];"
            f"[wm_bounce]scale=iw*{scale_bounce}:ih*{scale_bounce},format=rgba,colorchannelmixer=aa={opacity_bounce}[bounce_out];"
            f"[wm_static]scale=iw*{scale_static}:ih*{scale_static},format=rgba,colorchannelmixer=aa={opacity_static}[static_out];"
            f"[wm_top]scale=iw*{scale_topleft}:ih*{scale_topleft},format=rgba,colorchannelmixer=aa={opacity_topleft}[top_out];"
            f"[0:v]hflip,setpts=PTS+0.001/TB,"
            f"scale=iw*0.98:ih*0.98,"
            f"crop=iw-8:ih-8:(iw-8)/2:(ih-8)/2,"
            f"{lut_filter}"
            f"pad=iw+16:ih+16:(ow-iw)/2:(oh-ih)/2,"
            f"eq=brightness=0.01:contrast=1.02:saturation=1.03[base];"
            f"[base][bounce_out]overlay=x='main_w-w-30+10*sin(t*3)':y='main_h-h-60+5*sin(t*2)'[step1];"
            f"[step1][static_out]overlay=x='(main_w-w)/2':y='main_h-h-10'[step2];"
            f"[step2][top_out]overlay=x='mod((t*{scroll_speed}),(main_w+w))-w':y=60,"
            f"scale='trunc(iw/2)*2:trunc(ih/2)*2'[final]"
        )

        # Apply the filter to the video
        subprocess.run([
            "ffmpeg", "-i", input_file,
            "-i", watermark_choice,
            "-filter_complex", filter_complex,
            "-map", "[final]", "-map", "0:a?",
            "-map_metadata", "-1", "-map_chapters", "-1",
            "-r", str(framerate),
            "-g", "48", "-keyint_min", "24", "-sc_threshold", "0",
            "-b:v", "5M", "-maxrate", "5M", "-bufsize", "10M",
            "-preset", "ultrafast",  # << Updated here
            "-t", "40",
            "-c:v", "libx264", "-c:a", "copy",
            "-metadata", metadata_tag,
            watermarked_file
        ], check=True)

        # Final pass to copy audio and metadata to the final output
        subprocess.run([
            "ffmpeg", "-i", watermarked_file,
            "-map_metadata", "-1", "-map_chapters", "-1",
            "-c:v", "copy", "-c:a", "copy",
            "-metadata", metadata_tag,
            final_output
        ], check=True)

        return final_output

    except subprocess.CalledProcessError as e:
        return {"error": f"FFmpeg error: {str(e)}"}, 500
    except Exception as e:
        return {"error": f"Unexpected error: {str(e)}"}, 500
    finally:
        for f in [input_file, watermarked_file]:
            if os.path.exists(f): os.remove(f)


@app.route('/process', methods=['POST'])
def process_video_route():
    video_url = request.form['video_url']
    selected_brand = request.form['brand']

    if selected_brand not in BRANDS:
        return {"error": "Unsupported brand selected."}, 400

    progress_data = {"progress": 0}

    def update_progress(progress):
        progress_data["progress"] = progress

    # Start video processing in a separate thread
    processing_thread = threading.Thread(target=process_video_in_background, args=(video_url, selected_brand, update_progress))
    processing_thread.start()

    return render_template('processing.html', video_url=None, progress=progress_data["progress"])


@app.route('/progress', methods=['GET'])
def get_progress():
    return jsonify(progress=progress_data["progress"])


if __name__ == "__main__":
    app.run(debug=True)
