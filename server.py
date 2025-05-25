from flask import Flask, request, send_file
import subprocess
import uuid
import os
import random
import textwrap

app = Flask(__name__)

BRANDS = {
    "thick_asian": {
        "metadata":      "brand=thick_asian",
        "lut":           "Cobi_3.CUBE",
        "watermarks": [
            "Thick_asian_watermark.png",
            "Thick_asian_watermark_2.png",
            "Thick_asian_watermark_3.png"
        ],
        "captions_file": "thick_asian_captions.txt"
    },
    "gym_baddie": {
        "metadata":      "brand=gym_baddie",
        "lut":           "Cobi_3.CUBE",
        "watermarks": [
            "gym_baddie_watermark.png",
            "gym_baddie_watermark_2.png",
            "gym_baddie_watermark_3.png"
        ],
        "captions_file": "gym_baddie_captions.txt"
    },
    "polishedform": {
        "metadata":      "brand=polishedform",
        "lut":           None,
        "watermarks": [
            "polished_watermark.png",
            "polished_watermark_2.png",
            "polished_watermark_3.png"
        ],
        "captions_file": "polishedform_captions.txt"
    }
}

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

    in_mp4  = f"/tmp/{uuid.uuid4()}.mp4"
    mid_mp4 = f"/tmp/{uuid.uuid4()}_mid.mp4"
    out_mp4 = f"/tmp/{uuid.uuid4()}_final.mp4"

    try:
        cfg       = BRANDS[brand]
        metadata  = cfg["metadata"]
        assets    = os.path.join(os.getcwd(), "assets")
        wm_file   = os.path.join(assets, random.choice(cfg["watermarks"]))
        lut_file  = os.path.join(assets, cfg["lut"]) if cfg["lut"] else None
        caps_file = os.path.join(assets, cfg["captions_file"])

        # 1) Download source
        subprocess.run([
            "wget", "-q", "--header=User-Agent: Mozilla/5.0",
            "-O", in_mp4, video_url
        ], check=True)

        # 2) Pick & wrap a random caption
        with open(caps_file, encoding="utf-8") as f:
            lines = [l.strip() for l in f if l.strip()]
        wrapped = wrap_caption(random.choice(lines))

        # 3) Random params for watermarks & timing
        ob       = round(random.uniform(0.6, 0.7), 2)   # bounce opacity
        os_      = round(random.uniform(0.85, 0.95), 2) # static opacity
        ot       = round(random.uniform(0.4, 0.6), 2)   # scroll opacity
        sb       = random.uniform(0.85, 1.0)            # bounce scale
        ss       = random.uniform(1.1, 1.25)            # static scale
        st       = random.uniform(0.9, 1.1)             # scroll scale
        fr       = round(random.uniform(29.87, 30.1), 3)
        dx       = round(random.uniform(20, 40), 2)
        dy       = round(random.uniform(20, 40), 2)
        delay_x  = round(random.uniform(0.2, 1.0), 2)
        delay_y  = round(random.uniform(0.2, 1.0), 2)
        # stable center-top watermark
        sc       = 1.2    # 120% size
        oc       = 1.0    # full opacity
        lut_filt = f"lut3d='{lut_file}'," if lut_file else ""

        # 4) filter_complex
        fc = (
            "[1:v]split=4[wb][ws][wt][wc];"
            # bounce watermark
            f"[wb]scale=iw*{sb}:ih*{sb},format=rgba,"
            f"colorchannelmixer=aa={ob}[bounce];"
            # static bottom watermark
            f"[ws]scale=iw*{ss}:ih*{ss},format=rgba,"
            f"colorchannelmixer=aa={os_}[static];"
            # scrolling top watermark
            f"[wt]scale=iw*{st}:ih*{st},format=rgba,"
            f"colorchannelmixer=aa={ot}[scroll];"
            # stable center-top watermark
            f"[wc]scale=iw*{sc}:ih*{sc},format=rgba,"
            f"colorchannelmixer=aa={oc}[topcenter];"
            # base video → slight timing shift, scale, LUT, 75px black border
            "[0:v]setpts=PTS+0.001/TB,"
            "scale=iw*0.98:ih*0.98,"
            f"{lut_filt}"
            "pad=iw+150:ih+150:75:75:color=black[padded];"
            # 0) overlay center-top watermark
            "[padded][topcenter]overlay="
              "x=(main_w-w)/2:y=75[b0];"
            # 1) overlay bounce inside inner frame
            "[b0][bounce]overlay="
              "x=75+abs(mod((t+{delay_x})*{dx},(main_w-150-w)*2)-(main_w-150-w)):"
              "y=75+abs(mod((t+{delay_y})*{dy},(main_h-150-h)*2)-(main_h-150-h))[b1];"
            # 2) overlay static bottom-center
            "[b1][static]overlay="
              "x=(main_w-w)/2:y=main_h-h-30[b2];"
            # 3) overlay scrolling top
            "[b2][scroll]overlay="
              "x='mod(t*100,main_w+w)-w':y=20[step3];"
            # 4) draw fading caption
            "[step3]drawtext="
              "fontfile=/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf:"
              f"text='{wrapped}':"
              "fontcolor=white:fontsize=28:"
              "box=1:boxcolor=black@0.6:boxborderw=10:"
              "x=(w-text_w)/2:y=h*0.45:"
              "enable='between(t,0,4)':"
              "alpha='if(lt(t,3),1,1-(t-3))'[captioned];"
            # 5) force even dimensions
            "[captioned]scale='trunc(iw/2)*2:trunc(ih/2)*2'[final]"
        )

        # 5) encode
        cmd = [
            "ffmpeg", "-y",
            "-i", in_mp4,
            "-i", wm_file,
            "-filter_complex", fc,
            "-map", "[final]",
            "-map", "0:a?",            # passthrough original audio
            "-r", str(fr),
            "-g", "48", "-keyint_min", "24", "-sc_threshold", "0",
            "-b:v", "8M", "-maxrate", "8M", "-bufsize", "16M",
            "-preset", "medium",
            "-threads", "0",
            "-t", "40",
            "-c:v", "libx264",
            "-c:a", "copy",
            "-metadata", metadata,
            mid_mp4
        ]
        subprocess.run(cmd, check=True)

        # 6) strip metadata & chapters
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
        return {"error": f"FFmpeg failed: {e}"}, 500
    except Exception as e:
        return {"error": f"Unexpected error: {e}"}, 500
    finally:
        for fpath in (in_mp4, mid_mp4, out_mp4):
            try: os.remove(fpath)
            except: pass

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
