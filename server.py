# GitHub: add-progress-bar-on-top-border
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
        cfg      = BRANDS[brand]
        metadata = cfg["metadata"]
        assets   = os.path.join(os.getcwd(), "assets")
        wm_file  = os.path.join(assets, random.choice(cfg["watermarks"]))
        lut_file = os.path.join(assets, cfg["lut"]) if cfg["lut"] else None
        captions = os.path.join(assets, cfg["captions_file"])

        # 1) Download source
        subprocess.run([
            "wget", "-q", "--header=User-Agent: Mozilla/5.0",
            "-O", in_mp4, video_url
        ], check=True)

        # 2) Pick & wrap a caption
        with open(captions, encoding="utf-8") as f:
            lines = [l.strip() for l in f if l.strip()]
        wrapped = wrap_caption(random.choice(lines))

        # 3) Random watermark params
        ob  = round(random.uniform(0.6, 0.7), 2)
        os_ = round(random.uniform(0.85, 0.95), 2)
        ot  = round(random.uniform(0.4, 0.6), 2)
        sb  = random.uniform(0.85, 1.0)     # bounce scale
        ss  = random.uniform(1.05, 1.25)    # static scale
        st  = random.uniform(0.6, 0.75)     # top scale
        fr  = round(random.uniform(29.87, 30.1), 3)

        lut_filter = f"lut3d='{lut_file}'," if lut_file else ""

        # 4) Build filter_complex
        #    – black pad: 30px left/right, 45px top/bottom
        #    – scrolling top ticker (news-scroll)
        #    – static + moving watermark
        #    – caption fade-out + box
        #    – draw dynamic progress bar (40s duration)
        fc = (
            "[1:v]split=3[wb][ws][wt];"
            # bouncing watermark
            f"[wb]scale=iw*{sb}:ih*{sb},format=rgba,"
            f"colorchannelmixer=aa={ob}[bounce];"
            # static watermark
            f"[ws]scale=iw*{ss}:ih*{ss},format=rgba,"
            f"colorchannelmixer=aa={os_}[static];"
            # top scrolling watermark
            f"[wt]scale=iw*{st}:ih*{st},format=rgba,"
            f"colorchannelmixer=aa={ot}[top];"
            # main video → flip + tiny timing shift
            "[0:v]hflip,setpts=PTS+0.001/TB,"
            "scale=iw*0.98:ih*0.98,"
            # centered crop for black framing
            "crop=iw-8:ih-8:(iw-8)/2:(ih-8)/2,"
            # apply LUT if any
            f"{lut_filter}"
            # pad around: 30px L/R, 45px T/B, black
            "pad=iw+60:ih+90:30:45:color=black[base];"
            # overlay bouncing watermark (bottom-right)
            "[base][bounce]overlay=x=main_w-w-40:y=main_h-h-80[b1];"
            # overlay static watermark (centered bottom)
            "[b1][static]overlay=x=(main_w-w)/2:y=main_h-h-20[b2];"
            # overlay top ticker (scrolling left-to-right)
            #   ticker moves at speed so it loops every 5s
            "[b2][top]overlay=x='mod(t*100,main_w+w)-w':y=0[b3];"
            # draw progress bar: 5px tall, white@80%, top border at y=20px
            "[b3]drawbox=x=0:y=20:w='t*iw/40':h=5:color=white@0.8:t=fill[bar];"
            # captions (fade out after 3s)
            "[bar]drawtext="
              "fontfile=/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf:"
              f"text='{wrapped}':"
              "fontcolor=white:fontsize=28:"
              "box=1:boxcolor=black@0.6:boxborderw=10:"
              "x=(w-text_w)/2:y=h*0.45:"
              "enable='between(t,0,4)':"
              "alpha='if(lt(t,3),1,1-(t-3))'"
            "[captioned];"
            # force even dimensions
            "[captioned]scale='trunc(iw/2)*2:trunc(ih/2)*2'[final]"
        )

        # 5) First pass → insert everything, ultrafast, copy audio
        cmd = [
            "ffmpeg", "-y",
            "-i", in_mp4,
            "-i", wm_file,
            "-filter_complex", fc,
            "-map", "[final]",
            "-map", "0:a?",   # copy audio if present
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
        return {"error": f"FFmpeg failed:\n{e.stderr.decode()}"}, 500
    except Exception as e:
        return {"error": f"Unexpected error: {e}"}, 500
    finally:
        for p in (in_mp4, mid_mp4, out_mp4):
            try: os.remove(p)
            except: pass

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
