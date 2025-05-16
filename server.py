from flask import Flask, request, send_file
import subprocess
import uuid
import os
import random

app = Flask(__name__)

BRANDS = {
    "thick_asian": {
        "metadata": "brand=thick_asian",
        "lut": "Cobi_3.CUBE",
        "scroll_speed": 80,
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
        "scroll_speed": 120,
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
        "scroll_speed": 80,
        "watermarks": [
            "polished_watermark.png",
            "polished_watermark_2.png",
            "polished_watermark_3.png"
        ],
        "captions_file": "polishedform_captions.txt"
    }
}

@app.route('/process/<brand>', methods=['POST'])
def process_video(brand):
    if brand not in BRANDS:
        return {"error": f"Unsupported brand '{brand}'."}, 400

    video_url = request.json.get('video_url')
    if not video_url:
        return {"error": "Missing video_url in request."}, 400

    in_f  = f"/tmp/{uuid.uuid4()}.mp4"
    mid_f = f"/tmp/{uuid.uuid4()}_marked.mp4"
    out_f = f"/tmp/{uuid.uuid4()}_final.mp4"

    try:
        cfg          = BRANDS[brand]
        metadata_tag = cfg["metadata"]
        speed        = cfg["scroll_speed"]
        assets       = os.path.join(os.getcwd(), "assets")
        wm           = os.path.join(assets, random.choice(cfg["watermarks"]))
        lut_path     = os.path.join(assets, cfg["lut"]) if cfg["lut"] else None
        caps_file    = os.path.join(assets, cfg["captions_file"])

        # 1) Download source
        subprocess.run([
            "wget","--header=User-Agent: Mozilla/5.0",
            "-O", in_f, video_url
        ], check=True)

        # 2) Pick a random caption
        with open(caps_file, "r", encoding="utf-8") as ff:
            lines = [l.strip() for l in ff if l.strip()]
        caption = random.choice(lines).replace("'", "\\'")

        # 3) Random watermark parameters
        ob = round(random.uniform(0.6,0.7),2)
        os_ = round(random.uniform(0.85,0.95),2)
        ot = round(random.uniform(0.4,0.6),2)
        sb = random.uniform(0.85,1.0)
        ss = random.uniform(1.1,1.25)
        st = random.uniform(0.9,1.1)
        fr = round(random.uniform(29.87,30.1),3)
        lut_f = f"lut3d='{lut_path}'," if lut_path else ""

        # 4) Build filter_complex
        fc = (
            # split watermark layers
            "[1:v]split=3[wm_bounce][wm_static][wm_top];"
            # bounce layer
            f"[wm_bounce]scale=iw*{sb}:ih*{sb},format=rgba,"
              f"colorchannelmixer=aa={ob}[bounce];"
            # static layer
            f"[wm_static]scale=iw*{ss}:ih*{ss},format=rgba,"
              f"colorchannelmixer=aa={os_}[static];"
            # top layer
            f"[wm_top]scale=iw*{st}:ih*{st},format=rgba,"
              f"colorchannelmixer=aa={ot}[top];"
            # base video transforms
            "[0:v]hflip,setpts=PTS+0.001/TB,"
              "scale=iw*0.98:ih*0.98,"
              "crop=iw-8:ih-8:(iw-8)/2:(ih-8)/2,"
              f"{lut_f}"
              "pad=iw+16:ih+16:(ow-iw)/2:(oh-ih)/2,"
              "eq=brightness=0.01:contrast=1.02:saturation=1.03[base];"
            # overlay bounce
            "[base][bounce]overlay="
              "x='main_w-w-30+10*sin(t*3)':"
              "y='main_h-h-60+5*sin(t*2)'[s1];"
            # overlay static
            "[s1][static]overlay="
              "x='(main_w-w)/2':y='main_h-h-10'[s2];"
            # overlay top + force even dims
            f"[s2][top]overlay="
              f"x='mod(t*{speed},main_w+w)-w':y=60,"
              "scale='trunc(iw/2)*2:trunc(ih/2)*2'[vout];"
            # draw final caption box + text on top
            f"[vout]drawtext=text='{caption}':"
              "fontfile=/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf:"
              "fontcolor=white:"
              # dynamic shrink if needed
              "fontsize=ceil(28*min(1\\,(w-40)/text_w)):"
              # always draw box behind text
              "box=1:boxcolor=black@0.6:boxborderw=10:"
              "x=(w-text_w)/2:y=(h-text_h)/2:"
              "enable='between(t,0,4)':"
              "alpha='if(lt(t,3),1,1-(t-3))'[final]"
        )

        # 5) First pass: heavy encode
        cmd1 = [
            "ffmpeg","-i",in_f,"-i",wm,
            "-filter_complex",fc,
            "-map","[final]","-map","0:a?",
            "-map_metadata","-1","-map_chapters","-1",
            "-r",str(fr),
            "-g","48","-keyint_min","24","-sc_threshold","0",
            "-b:v","8M","-maxrate","8M","-bufsize","16M",
            "-preset","slow","-profile:v","high",
            "-t","40","-c:v","libx264","-c:a","copy",
            "-metadata",metadata_tag,
            mid_f
        ]
        subprocess.run(cmd1, check=True)

        # 6) Strip & pass-through audio
        subprocess.run([
            "ffmpeg","-i",mid_f,
            "-map_metadata","-1","-map_chapters","-1",
            "-c:v","copy","-c:a","copy",
            "-metadata",metadata_tag,
            out_f
        ], check=True)

        return send_file(out_f, as_attachment=True)

    except subprocess.CalledProcessError as e:
        return {"error": f"FFmpeg error: {e}"}, 500
    except Exception as e:
        return {"error": f"Unexpected error: {e}"}, 500
    finally:
        for fpath in (in_f, mid_f):
            if os.path.exists(fpath):
                os.remove(fpath)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT",5000)))
