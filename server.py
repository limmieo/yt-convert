#!/usr/bin/env python3
# PUSH: enforce even dims → 2025-05-25

from flask import Flask, request, send_file
import subprocess, uuid, os, random, textwrap

app = Flask(__name__)

BRANDS = {
    "thick_asian": {
        "metadata": "brand=thick_asian",
        "lut": "Cobi_3.CUBE",
        "watermarks": [
            "Thick_asian_watermark.png",
            "Thick_asian_watermark_2.png",
            "Thick_asian_watermark_3.png"
        ],
        "captions_file": "thick_asian_captions.txt"
    },
    "gym_baddie": {
        "metadata": "brand=gym_baddie",
        "lut": "Cobi_3.CUBE",
        "watermarks": [
            "gym_baddie_watermark.png",
            "gym_baddie_watermark_2.png",
            "gym_baddie_watermark_3.png"
        ],
        "captions_file": "gym_baddie_captions.txt"
    },
    "polishedform": {
        "metadata": "brand=polishedform",
        "lut": None,
        "watermarks": [
            "polished_watermark.png",
            "polished_watermark_2.png",
            "polished_watermark_3.png"
        ],
        "captions_file": "polishedform_captions.txt"
    }
}

HEART_IMGS = ["heart_1.png", "heart_2.png", "heart_3.png"]

def wrap_caption(caption, width=30):
    lines = textwrap.wrap(caption, width)
    if len(lines) > 2:
        lines = [" ".join(lines[:-1]), lines[-1]]
    return "\\n".join(lines)

@app.route('/process/<brand>', methods=['POST'])
def process_video(brand):
    if brand not in BRANDS:
        return {"error": f"Unsupported brand '{brand}'."}, 400

    data = request.get_json() or {}
    video_url = data.get('video_url')
    if not video_url:
        return {"error": "Missing video_url in request."}, 400

    # temp files
    in_mp4  = f"/tmp/{uuid.uuid4()}.mp4"
    mid_mp4 = f"/tmp/{uuid.uuid4()}_mid.mp4"
    out_mp4 = f"/tmp/{uuid.uuid4()}_final.mp4"

    try:
        cfg      = BRANDS[brand]
        metadata = cfg["metadata"]
        assets   = os.path.join(os.getcwd(), "assets")

        # choose your news-style watermark PNG
        wm_file = os.path.join(assets, random.choice(cfg["watermarks"]))
        # pick 4 heart icons (with replacement)
        hearts = random.choices(HEART_IMGS, k=4)
        heart_paths = [os.path.join(assets, h) for h in hearts]

        # LUT?
        lut_file = os.path.join(assets, cfg["lut"]) if cfg["lut"] else None
        lut_filter = f"lut3d='{lut_file}'," if lut_file else ""

        # captions
        with open(os.path.join(assets, cfg["captions_file"]), encoding="utf-8") as f:
            lines = [l.strip() for l in f if l.strip()]
        wrapped = wrap_caption(random.choice(lines))

        # random watermark alpha & scale
        ob  = round(random.uniform(0.6, 0.7), 2)
        os_ = round(random.uniform(0.85, 0.95), 2)
        sb  = round(random.uniform(0.9, 1.1), 2)
        fr  = round(random.uniform(29.87, 30.1), 3)

        # build filter_complex
        # inputs:
        #   0: video
        #   1: news-watermark
        #   2..5: heart_*.png
        fc = (
            # split & prep your news-watermark (across full width)
            "[1:v]scale=iw:-1,format=rgba,"
              f"colorchannelmixer=aa={os_}[wm];"

            # prep hearts (scale them small & set alpha)
            f"[2:v]scale=64:64,format=rgba,colorchannelmixer=aa=1[h1];"
            f"[3:v]scale=64:64,format=rgba,colorchannelmixer=aa=1[h2];"
            f"[4:v]scale=64:64,format=rgba,colorchannelmixer=aa=1[h3];"
            f"[5:v]scale=64:64,format=rgba,colorchannelmixer=aa=1[h4];"

            # main video: flip, tiny desync, LUT, bars, contrast
            "[0:v]hflip,setpts=PTS+0.001/TB,"
            f"{lut_filter}"
            "pad=iw:ih+90:0:45:black,"
            "eq=brightness=0.01:contrast=1.02:saturation=1.03[base];"

            # news-watermark across middle
            "[base][wm]overlay=x=0:y=(main_h-overlay_h)/2[b0];"

            # corner hearts
            "[b0][h1]overlay=x=10:y=10[b1];"
            "[b1][h2]overlay=x=main_w-overlay_w-10:y=10[b2];"
            "[b2][h3]overlay=x=10:y=main_h-overlay_h-10[b3];"
            "[b3][h4]overlay=x=main_w-overlay_w-10:y=main_h-overlay_h-10[step];"

            # caption fade
            "[step]drawtext="
              "fontfile=/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf:"
              f"text='{wrapped}':fontcolor=white:fontsize=28:"
              "box=1:boxcolor=black@0.6:boxborderw=10:"
              "x=(w-text_w)/2:y=(h-text_h)/2:"
              "enable='between(t,0,4)':"
              "alpha='if(lt(t,3),1,1-(t-3))'[captioned];"

            # final even-dims safeguard
            "[captioned]scale='trunc(iw/2)*2:trunc(ih/2)*2'[final]"
        )

        # 1) download source
        subprocess.run([
            "wget", "-q", "--header=User-Agent: Mozilla/5.0",
            "-O", in_mp4, video_url
        ], check=True)

        # 2) first ffmpeg pass
        cmd1 = [
            "ffmpeg", "-y",
            "-i", in_mp4,
            "-i", wm_file,
            *sum([["-i", p] for p in heart_paths], []),  # hearts 2→5
            "-filter_complex", fc,
            "-map", "[final]",
            "-map", "0:a?",
            "-r", str(fr),
            "-g", "48", "-keyint_min", "24", "-sc_threshold", "0",
            "-b:v", "8M", "-maxrate", "8M", "-bufsize", "16M",
            "-preset", "ultrafast",
            "-c:v", "libx264",
            "-c:a", "copy",
            "-metadata", metadata,
            mid_mp4
        ]
        subprocess.run(cmd1, check=True)

        # 3) strip metadata/chapters
        subprocess.run([
            "ffmpeg", "-y",
            "-i", mid_mp4,
            "-map_metadata", "-1",
            "-map_chapters", "-1",
            "-c:v", "copy",
            "-c:a", "copy",
            "-metadata", metadata,
            out_mp4
        ], check=True)

        return send_file(out_mp4, as_attachment=True)

    except subprocess.CalledProcessError as e:
        stderr = e.stderr.decode() if getattr(e, "stderr", None) else str(e)
        return {"error": f"FFmpeg failed:\n{stderr}"}, 500

    except Exception as e:
        return {"error": f"Unexpected error: {e}"}, 500

    finally:
        for p in (in_mp4, mid_mp4, out_mp4):
            try: os.remove(p)
            except: pass

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
