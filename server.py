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

def escape(text):
    return text.replace(":", r'\:').replace("'", r"\'").replace(",", r'\,')

def wrap_caption(caption, width=30):
    lines = textwrap.wrap(caption, width)
    if len(lines) > 2:
        lines = [" ".join(lines[:-1]), lines[-1]]
    return "\\n".join(lines)

@app.route("/process/<brand>", methods=["POST"])
def process(brand):
    if brand not in BRANDS:
        return {"error": f"Unsupported brand '{brand}'"}, 400

    video_url = request.json.get("video_url")
    if not video_url:
        return {"error": "Missing video_url"}, 400

    in_path = f"/tmp/{uuid.uuid4()}.mp4"
    mid_path = f"/tmp/{uuid.uuid4()}_mid.mp4"
    out_path = f"/tmp/{uuid.uuid4()}_out.mp4"

    try:
        cfg = BRANDS[brand]
        assets = os.path.join(os.getcwd(), "assets")
        wm_file = os.path.join(assets, random.choice(cfg["watermarks"]))
        lut_file = os.path.join(assets, cfg["lut"]) if cfg["lut"] else None
        captions_path = os.path.join(assets, cfg["captions_file"])
        metadata = cfg["metadata"]

        subprocess.run(["wget", "-q", "--header=User-Agent: Mozilla/5.0", "-O", in_path, video_url], check=True)

        # Load & wrap caption
        with open(captions_path, encoding="utf-8") as f:
            caption_lines = [l.strip() for l in f if l.strip()]
        raw_caption = random.choice(caption_lines)
        wrapped = wrap_caption(raw_caption)
        escaped_caption = escape(wrapped)

        ob = round(random.uniform(0.6, 0.7), 2)
        os_ = round(random.uniform(0.85, 0.95), 2)
        ot = round(random.uniform(0.4, 0.6), 2)
        sb = round(random.uniform(0.85, 1.0), 2)
        ss = round(random.uniform(1.1, 1.25), 2)
        st = round(random.uniform(0.9, 1.1), 2)
        fr = round(random.uniform(29.87, 30.1), 3)
        lut_cmd = f"lut3d='{lut_file}'," if lut_file else ""

        fc = (
            f"[1:v]split=3[b1][b2][b3];"
            f"[b1]scale=iw*{sb}:ih*{sb},format=rgba,colorchannelmixer=aa={ob}[wm1];"
            f"[b2]scale=iw*{ss}:ih*{ss},format=rgba,colorchannelmixer=aa={os_}[wm2];"
            f"[b3]scale=iw*{st}:ih*{st},format=rgba,colorchannelmixer=aa={ot}[wm3];"
            f"[0:v]hflip,setpts=PTS+0.001/TB,scale=iw*0.98:ih*0.98,"
            f"crop=iw-8:ih-8:(iw-8)/2:(ih-8)/2,{lut_cmd}"
            f"pad=iw+16:ih+16:(ow-iw)/2:(oh-ih)/2,"
            f"eq=brightness=0.01:contrast=1.02:saturation=1.03[bg];"
            f"[bg][wm1]overlay=x='main_w-w-40':y='main_h-h-80'[tmp1];"
            f"[tmp1][wm2]overlay=x='(main_w-w)/2':y='main_h-h-20'[tmp2];"
            f"[tmp2][wm3]overlay=x='main_w-w-50':y=60[withwm];"
            f"[withwm]drawtext=fontfile=/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf:"
            f"text='{escaped_caption}':fontcolor=white:fontsize=28:box=1:"
            f"boxcolor=black@0.6:boxborderw=10:x=(w-text_w)/2:y=h*0.45:"
            f"enable='between(t,0,4)':alpha='if(lt(t,3),1,1-(t-3))'[captioned];"
            f"[captioned]scale=trunc(iw/2)*2:trunc(ih/2)*2[out]"
        )

        subprocess.run([
            "ffmpeg", "-y",
            "-i", in_path,
            "-i", wm_file,
            "-filter_complex", fc,
            "-map", "[out]",
            "-map", "0:a?",
            "-r", str(fr),
            "-g", "48", "-keyint_min", "24", "-sc_threshold", "0",
            "-b:v", "2500k", "-maxrate", "2500k", "-bufsize", "5000k",
            "-c:v", "libx264", "-preset", "fast", "-profile:v", "high",
            "-c:a", "copy",
            "-metadata", metadata,
            "-t", "40",
            mid_path
        ], check=True)

        subprocess.run([
            "ffmpeg", "-y",
            "-i", mid_path,
            "-map_metadata", "-1",
            "-map_chapters", "-1",
            "-c:v", "copy", "-c:a", "copy",
            "-metadata", metadata,
            out_path
        ], check=True)

        return send_file(out_path, as_attachment=True)

    except subprocess.CalledProcessError as e:
        return {"error": f"FFmpeg failed: {str(e)}"}, 500
    except Exception as e:
        return {"error": f"Unexpected error: {str(e)}"}, 500
    finally:
        for path in (in_path, mid_path):
            try: os.remove(path)
            except: pass

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
