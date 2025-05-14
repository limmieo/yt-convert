from flask import Flask, request, send_file
import subprocess, uuid, os, random

app = Flask(__name__)

BRANDS = {
    "thick_asian": {
        "metadata":      "brand=thick_asian",
        "watermarks": [
            "Thick_asian_watermark.png",      # top
            "Thick_asian_watermark_2.png",    # bottom
            "Thick_asian_watermark_3.png"     # moving
        ],
        "captions_file": "thick_asian_captions.txt",
        "scroll_speed":  80
    },
    "gym_baddie": {
        "metadata":      "brand=gym_baddie",
        "watermarks": [
            "gym_baddie_watermark.png",
            "gym_baddie_watermark_2.png",
            "gym_baddie_watermark_3.png"
        ],
        "captions_file": "gym_baddie_captions.txt",
        "scroll_speed":  120
    },
    "polishedform": {
        "metadata":      "brand=polishedform",
        "watermarks": [
            "polished_watermark.png",
            "polished_watermark_2.png",
            "polished_watermark_3.png"
        ],
        "captions_file": "polishedform_captions.txt",
        "scroll_speed":  80
    }
}

@app.route('/process/<brand>', methods=['POST'])
def process_video(brand):
    if brand not in BRANDS:
        return {"error": f"Unsupported brand '{brand}'"}, 400

    data = request.get_json() or {}
    url  = data.get("video_url")
    if not url:
        return {"error": "Missing video_url"}, 400

    # temp file names
    in_tmp  = f"/tmp/{uuid.uuid4()}.mp4"
    mid_tmp = f"/tmp/{uuid.uuid4()}_mid.mp4"
    out_tmp = f"/tmp/{uuid.uuid4()}_final.mp4"

    cfg         = BRANDS[brand]
    assets_dir  = os.path.join(os.getcwd(), "assets")
    caps_file   = os.path.join(assets_dir, cfg["captions_file"])
    wm_top      = os.path.join(assets_dir, cfg["watermarks"][0])
    wm_bottom   = os.path.join(assets_dir, cfg["watermarks"][1])
    wm_moving   = os.path.join(assets_dir, cfg["watermarks"][2])
    scroll_spd  = cfg["scroll_speed"]

    try:
        # 1) download via wget
        subprocess.run(
            ["wget", "-q", "-O", in_tmp, url],
            check=True
        )

        # 2) pick a random caption
        with open(caps_file, "r", encoding="utf-8") as f:
            lines = [l.strip() for l in f if l.strip()]
        caption = random.choice(lines).replace("'", r"\'")

        # 3) build ffmpeg filter graph
        fc = (
            "[0:v]format=yuv420p[in];"
            # top watermark
            f"movie={wm_top}[wt];[in][wt]overlay=x=(W-w)/2:y=10[in];"
            # caption box + text
            "drawbox=x=0:y=70:w=W:h=50:color=black@0.6:t=fill,"
            f"drawtext=text='{caption}':fontcolor=white:fontsize=24:x=(W-text_w)/2:y=80[in];"
            # bottom static watermark
            f"movie={wm_bottom}[wb];[in][wb]overlay=x=(W-w)/2:y=H-h-20[in];"
            # moving watermark
            f"movie={wm_moving}[wm];[in][wm]overlay="
            f"x='mod(t*{scroll_spd},W+w)-w':y=H-h-60,"
            # force even dimensions & label final
            "scale='trunc(iw/2)*2:trunc(ih/2)*2'[outv]"
        )

        # 4) render with high‐quality settings
        cmd = [
            "ffmpeg", "-y",
            "-i",  in_tmp,
            "-filter_complex", fc,
            "-map", "[outv]",
            "-map", "0:a?",            # preserve any audio
            #
            # ← much higher‐quality H.264 encode
            "-c:v",      "libx264",
            "-crf",      "18",
            "-preset",   "slow",
            "-profile:v", "high",
            "-movflags", "+faststart",
            #
            "-c:a",      "copy",      # copy audio untouched
            "-metadata", cfg["metadata"],
            mid_tmp
        ]
        subprocess.run(cmd, check=True)

        # 5) finalize (strip any extra metadata)
        subprocess.run([
            "ffmpeg", "-y",
            "-i", mid_tmp,
            "-map", "0:v", "-map", "0:a?",
            "-c", "copy",
            "-metadata", cfg["metadata"],
            out_tmp
        ], check=True)

        return send_file(out_tmp, as_attachment=True)

    except subprocess.CalledProcessError as e:
        return {"error": f"FFmpeg failed: {e}"}, 500

    finally:
        # cleanup intermediates
        for f in (in_tmp, mid_tmp):
            if os.path.exists(f):
                os.remove(f)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT",5000)))
