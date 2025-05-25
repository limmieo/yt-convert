from flask import Flask, request, send_file
import subprocess
import uuid
import os
import random

app = Flask(__name__)

@app.route('/process/thick_asian', methods=['POST'])
def process_video():
    video_url = request.json.get('video_url')
    if not video_url:
        return {"error": "Missing video_url in request."}, 400

    # --- temp filenames ---
    input_file   = f"/tmp/{uuid.uuid4()}.mp4"
    mid_file     = f"/tmp/{uuid.uuid4()}_mid.mp4"
    final_file   = f"/tmp/{uuid.uuid4()}_final.mp4"

    # --- download source clip ---
    subprocess.run([
        "wget", "--header=User-Agent: Mozilla/5.0",
        "-O", input_file, video_url
    ], check=True)

    # --- randomize your bounce/static/top watermark params ---
    opacity_bounce  = round(random.uniform(0.6, 0.7), 2)
    opacity_static  = round(random.uniform(0.85, 0.95), 2)
    opacity_topleft = round(random.uniform(0.4, 0.6),  2)

    scale_bounce  = random.uniform(0.83, 1.0)
    scale_static  = random.uniform(1.05, 1.2)
    scale_topleft = random.uniform(0.6,  0.75)

    framerate = round(random.uniform(29.87, 30.1), 3)

    # --- pick your assets from /assets ---
    assets = os.path.join(os.getcwd(), "assets")
    watermark_choice = os.path.join(
        assets,
        random.choice(["watermark.png", "watermark_2.png", "watermark_3.png"])
    )
    lut_path = os.path.join(assets, "Cobi_3.CUBE")

    # --- build the monolithic filtergraph ---
    #    (no more escaping hell in the CLI)
    fc = (
        # split your PNG watermark into three streams
        "[1:v]split=3[wm_bounce][wm_static][wm_top];"
        # bounce watermark
        f"[wm_bounce]scale=iw*{scale_bounce}:ih*{scale_bounce},"
        f"format=rgba,colorchannelmixer=aa={opacity_bounce}[bounce_out];"
        # static watermark
        f"[wm_static]scale=iw*{scale_static}:ih*{scale_static},"
        f"format=rgba,colorchannelmixer=aa={opacity_static}[static_out];"
        # top-left watermark
        f"[wm_top]scale=iw*{scale_topleft}:ih*{scale_topleft},"
        f"format=rgba,colorchannelmixer=aa={opacity_topleft}[top_out];"
        # flip & lightly crop+scale the base video
        "[0:v]hflip,setpts=PTS+0.001/TB,scale=iw*0.98:ih*0.98[cropped];"
        # overlay bounce at bottom-right
        "[cropped][bounce_out]"
        "overlay=x='main_w-w-30':y='main_h-h-60'[step1];"
        # overlay static centered lower
        "[step1][static_out]"
        "overlay=x='(main_w-w)/2':y='main_h-h-10'[step2];"
        # overlay top_out in the corner, apply your LUT & force even dimensions
        "[step2][top_out]overlay=x=20:y=20,"
        f"lut3d='{lut_path}',"
        "scale='trunc(iw/2)*2:trunc(ih/2)*2'[final]"
    )

    # --- write that filtergraph to disk ---
    fc_path = f"/tmp/{uuid.uuid4()}_fc.txt"
    with open(fc_path, "w") as f:
        f.write(fc)

    # --- first ffmpeg pass: apply all filters + copy audio ---
    cmd1 = [
        "ffmpeg", "-y",
        "-i", input_file,
        "-i", watermark_choice,
        "-filter_complex_script", fc_path,
        "-map", "[final]",
        "-map", "0:a?",                      # passthrough audio
        "-r", str(framerate),
        "-g", "48", "-keyint_min", "24", "-sc_threshold", "0",
        "-b:v", "8M", "-maxrate", "8M", "-bufsize", "16M",
        "-preset", "superfast",
        "-c:v", "libx264",
        "-c:a", "copy",                      # copy audio intact
        "-metadata", "brand=thick_asian",
        mid_file
    ]
    subprocess.run(cmd1, check=True)

    # --- second ffmpeg pass: re-mux if you need to reattach metadata or fix containers ---
    subprocess.run([
        "ffmpeg", "-y",
        "-i", mid_file,
        "-map", "0:v",
        "-map", "0:a?",
        "-c", "copy",
        "-metadata", "brand=thick_asian",
        final_file
    ], check=True)

    # send it back
    return send_file(final_file, as_attachment=True)

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
