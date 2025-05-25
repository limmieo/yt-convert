#!/usr/bin/env python3
# PUSH: add corner hearts + 45px bars | 2025-05-25

from flask import Flask, request, send_file
import subprocess
import uuid
import os
import random
import textwrap

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

HEARTS = ["🥰", "😍", "😻", "💌", "💘", "💝", "💗"]

def wrap_caption(caption, width=30):
    lines = textwrap.wrap(caption, width)
    if len(lines) > 2:
        lines = [" ".join(lines[:-1]), lines[-1]]
    return "\\n".join(lines)

@app.route('/process/<brand>', methods=['POST'])
def process_video(brand):
    if brand not in BRANDS:
        return {"error": f"Unsupported brand '{brand}'."}, 400

    video_url = request.json.get('video_url')
    if not video_url:
        return {"error": "Missing video_url in request."}, 400

    # prepare temp files
    in_mp4  = f"/tmp/{uuid.uuid4()}.mp4"
    mid_mp4 = f"/tmp/{uuid.uuid4()}_mid.mp4"
    out_mp4 = f"/tmp/{uuid.uuid4()}_final.mp4"

    try:
        cfg      = BRANDS[brand]
        metadata = cfg["metadata"]
        assets   = os.path.join(os.getcwd(), "assets")
        wm_file  = os.path.join(assets, random.choice(cfg["watermarks"]))
        lut_file = os.path.join(assets, cfg["lut"]) if cfg["lut"] else None
        captions = os.path.join(assets, cfg["captions_file"])

        # download input
        subprocess.run([
            "wget", "-q", "--header=User-Agent: Mozilla/5.0",
            "-O", in_mp4, video_url
        ], check=True)

        # pick & wrap caption
        with open(captions, encoding="utf-8") as f:
            lines = [l.strip() for l in f if l.strip()]
        wrapped = wrap_caption(random.choice(lines))

        # pick 4 random hearts
        corners = random.sample(HEARTS, 4)

        # random watermark params
        ob  = round(random.uniform(0.6, 0.7), 2)
        os_ = round(random.uniform(0.85, 0.95), 2)
        ot  = round(random.uniform(0.4, 0.6), 2)
        sb  = random.uniform(0.85, 1.0)
        ss  = random.uniform(1.1, 1.25)
        st  = random.uniform(0.9, 1.1)
        fr  = round(random.uniform(29.87, 30.1), 3)

        lut_filter = f"lut3d='{lut_file}'," if lut_file else ""

        # build filter_complex
        fc = (
            # split watermark into 3 streams
            "[1:v]split=3[wb][ws][wt];"
            # bounce-watermark
            f"[wb]scale=iw*{sb}:ih*{sb},format=rgba,"
              f"colorchannelmixer=aa={ob}[bounce];"
            # static-watermark
            f"[ws]scale=iw*{ss}:ih*{ss},format=rgba,"
              f"colorchannelmixer=aa={os_}[static];"
            # top-watermark
            f"[wt]scale=iw*{st}:ih*{st},format=rgba,"
              f"colorchannelmixer=aa={ot}[top];"

            # base video chain
            "[0:v]hflip,setpts=PTS+0.001/TB,"
              "scale=iw*0.98:ih*0.98,"
              "crop=iw-8:ih-8:(iw-8)/2:(ih-8)/2,"
            f"{lut_filter}"
              "pad=iw:ih+90:0:45:black,"    # 45px top & bottom
              "eq=brightness=0.01:contrast=1.02:saturation=1.03[base];"

            # overlay watermarks
            "[base][bounce]overlay=x=main_w-w-40:y=ih-h+5[b1];"
            "[b1][static]overlay=x=(main_w-w)/2:y=ih-h+5[b2];"
            "[b2][top]overlay=x=main_w-w-50:y=45[b3];"

            # caption
            "[b3]drawtext="
              "fontfile=/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf:"
              f"text='{wrapped}':"
              "fontcolor=white:fontsize=28:"
              "box=1:boxcolor=black@0.6:boxborderw=10:"
              "x=(w-text_w)/2:y=(h-text_h)/2:"
              "enable='between(t,0,4)':"
              "alpha='if(lt(t,3),1,1-(t-3))'[cap];"

            # four corner hearts (static, one per corner)
            f"[cap]drawtext=fontfile=/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf:"
              f"text='{corners[0]}':fontcolor=white:fontsize=32:"
              "x=30:y=30[h1];"
            "[h1]drawtext=fontfile=/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf:"
              f"text='{corners[1]}':fontcolor=white:fontsize=32:"
              "x=w-text_w-30:y=30[h2];"
            "[h2]drawtext=fontfile=/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf:"
              f"text='{corners[2]}':fontcolor=white:fontsize=32:"
              "x=30:y=h-text_h-30[h3];"
            "[h3]drawtext=fontfile=/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf:"
              f"text='{corners[3]}':fontcolor=white:fontsize=32:"
              "x=w-text_w-30:y=h-text_h-30[final]"
        )

        # first pass — fast encode, keep audio
        cmd = [
            "ffmpeg", "-y",
            "-i", in_mp4,
            "-i", wm_file,
            "-filter_complex", fc,
            "-map", "[final]",
            "-map", "0:a?",
            "-r", str(fr),
            "-g", "48", "-keyint_min", "24", "-sc_threshold", "0",
            "-b:v", "8M", "-maxrate", "8M", "-bufsize", "16M",
            "-preset", "ultrafast",
            "-threads", "0",
            "-t", "40",
            "-c:v", "libx264",
            "-c:a", "copy",
            "-metadata", metadata,
            mid_mp4
        ]
        subprocess.run(cmd, check=True)

        # strip metadata & chapters
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
        err = getattr(e, 'stderr', None)
        msg = err.decode() if err else str(e)
        return {"error": f"FFmpeg failed:\n{msg}"}, 500

    except Exception as e:
        return {"error": f"Unexpected error: {e}"}, 500

    finally:
        for p in (in_mp4, mid_mp4, out_mp4):
            try: os.remove(p)
            except: pass

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
