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

    in_tmp  = f"/tmp/{uuid.uuid4()}.mp4"
    mid_tmp = f"/tmp/{uuid.uuid4()}_mid.mp4"
    out_tmp = f"/tmp/{uuid.uuid4()}_final.mp4"

    cfg        = BRANDS[brand]
    assets_dir = os.path.join(os.getcwd(), "assets")
    caps_file  = os.path.join(assets_dir, cfg["captions_file"])
    wm_top     = os.path.join(assets_dir, cfg["watermarks"][0])
    wm_bot     = os.path.join(assets_dir, cfg["watermarks"][1])
    wm_mov     = os.path.join(assets_dir, cfg["watermarks"][2])
    speed      = cfg["scroll_speed"]

    try:
        subprocess.run(["wget","-q","-O",in_tmp,url], check=True)

        with open(caps_file, "r", encoding="utf-8") as f:
            lines = [l.strip() for l in f if l.strip()]
        caption = random.choice(lines).replace("'", r"\'")

        # corrected filter_complex: use main_w/main_h in overlays
        fc = (
            "[0:v]format=yuv420p[n0];"
            f"movie={wm_top}[wt];[n0][wt]overlay="
              "x='(main_w-w)/2':y=10[n1];"
            "[n1]drawbox=x=0:y=70:w=iw:h=50:color=black@0.6:t=fill[n2];"
            f"[n2]drawtext=text='{caption}':fontcolor=white:fontsize=24:"
              "x='(iw-text_w)/2':y=80:alpha='if(lt(t,3),1,1-(t-3))'[n3];"
            f"movie={wm_bot}[wb];[n3][wb]overlay="
              "x='(main_w-w)/2':y='main_h-h-20'[n4];"
            f"movie={wm_mov}[wm];[n4][wm]overlay="
              f"x='mod(t*{speed},main_w+w)-w':y='main_h-h-60'[n5];"
            "[n5]scale='trunc(iw/2)*2:trunc(ih/2)*2'[outv]"
        )

        cmd1 = [
            "ffmpeg","-y",
            "-i", in_tmp,
            "-filter_complex", fc,
            "-map", "[outv]",
            "-map", "0:a?",
            "-c:v", "libx264", "-crf", "18", "-preset", "slow",
            "-profile:v", "high", "-movflags", "+faststart",
            "-c:a", "copy",
            "-metadata", cfg["metadata"],
            mid_tmp
        ]
        subprocess.run(cmd1, check=True)

        cmd2 = [
            "ffmpeg","-y",
            "-i", mid_tmp,
            "-map","0:v","-map","0:a?",
            "-c","copy",
            "-metadata", cfg["metadata"],
            out_tmp
        ]
        subprocess.run(cmd2, check=True)

        return send_file(out_tmp, as_attachment=True)

    except subprocess.CalledProcessError as e:
        return {"error": f"FFmpeg failed: {e}"}, 500

    finally:
        for f in (in_tmp, mid_tmp):
            if os.path.exists(f):
                os.remove(f)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT",5000)))
