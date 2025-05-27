from flask import Flask, request, send_file
import subprocess
import uuid
import os
import random
import textwrap

app = Flask(__name__)

# ─── Brand Config ─────────────────────────────────────────────────────────
BRANDS = {
    "thick_asian": {
        "metadata": "brand=thick_asian",
        "lut": "Cobi_3.CUBE",
        "watermarks": [
            "Thick_asian_watermark.png",
            "Thick_asian_watermark_2.png",
            "Thick_asian_watermark_3.png"
        ],
        "captions_file": "thick_asian_captions.txt",
        "outro": "thick_asian_outro.MOV"
    },
    "gym_baddie": {
        "metadata": "brand=gym_baddie",
        "lut": "Cobi_3.CUBE",
        "watermarks": [
            "gym_baddie_watermark.png",
            "gym_baddie_watermark_2.png",
            "gym_baddie_watermark_3.png"
        ],
        "captions_file": "gym_baddie_captions.txt",
        "outro": "gym_baddie_ig.mov"
    },
    "polishedform": {
        "metadata": "brand=polishedform",
        "lut": None,
        "watermarks": [
            "polished_watermark.png",
            "polished_watermark_2.png",
            "polished_watermark_3.png"
        ],
        "captions_file": "polishedform_captions.txt",
        "outro": None
    },
    "asian_travel": {
        "metadata": "brand=asian_travel",
        "lut": None,
        "watermarks": [
            "asian_travel_watermark.png",
            "asian_travel_watermark_2.png",
            "asian_travel_watermark_3.png"
        ],
        "captions_file": "asian_travel_captions.txt",
        "outro": "asia_travel_vault_outro.MOV"
    }
}

def wrap_caption(caption, width=30):
    lines = textwrap.wrap(caption, width)
    if len(lines) > 2:
        lines = [" ".join(lines[:-1]), lines[-1]]
    return "\\n".join(lines)

def sanitize_caption(caption):
    caption = caption.replace('\\', '\\\\')
    caption = caption.replace("'", "\\'")
    caption = caption.replace(":", "\\:")
    caption = caption.replace('\n', '')
    return caption

@app.route('/process/<brand>', methods=['POST'])
def process_video(brand):
    if brand not in BRANDS:
        return {"error": f"Unsupported brand '{brand}'."}, 400

    video_url = request.json.get('video_url')
    if not video_url:
        return {"error": "Missing video_url in request."}, 400

    in_mp4 = f"/tmp/{uuid.uuid4()}.mp4"
    mid_mp4 = f"/tmp/{uuid.uuid4()}_mid.mp4"
    out_mp4 = f"/tmp/{uuid.uuid4()}_final.mp4"

    try:
        cfg = BRANDS[brand]
        metadata = cfg["metadata"]
        assets = os.path.join(os.getcwd(), "assets")
        wm_file = os.path.join(assets, random.choice(cfg["watermarks"]))
        lut_file = os.path.join(assets, cfg["lut"]) if cfg["lut"] else None
        caps_file = os.path.join(assets, cfg["captions_file"])
        outro_file = os.path.join(assets, cfg["outro"]) if cfg.get("outro") else None

        print("▶ Downloading source video...")
        subprocess.run([
            "wget", "-q", "--header=User-Agent: Mozilla/5.0",
            "-O", in_mp4, video_url
        ], check=True)

        with open(caps_file, encoding="utf-8") as f:
            lines = [l.strip() for l in f if l.strip()]
        raw_caption = random.choice(lines)
        wrapped_caption = sanitize_caption(wrap_caption(raw_caption))
        print(f"📝 Using caption: {wrapped_caption}")

        ob = round(random.uniform(0.6, 0.7), 2)
        os_ = round(random.uniform(0.85, 0.95), 2)
        ot = round(random.uniform(0.4, 0.6), 2)
        sb = random.uniform(0.85, 1.0)
        ss = random.uniform(1.1, 1.25)
        st = random.uniform(0.9, 1.1)
        fr = round(random.uniform(29.87, 30.1), 3)
        dx = round(random.uniform(20, 40), 2)
        dy = round(random.uniform(20, 40), 2)
        delay_x = round(random.uniform(0.2, 1.0), 2)
        delay_y = round(random.uniform(0.2, 1.0), 2)
        lut_chain = f"lut3d='{lut_file}'," if lut_file else ""

        fc = (
            "[1:v]split=3[wb][ws][wt];"
            f"[wb]scale=iw*{sb}:ih*{sb},format=rgba,colorchannelmixer=aa={ob}[bounce];"
            f"[ws]scale=iw*{ss}:ih*{ss},format=rgba,colorchannelmixer=aa={os_}[static];"
            f"[wt]scale=iw*{st}:ih*{st},format=rgba,colorchannelmixer=aa={ot}[top];"
            "[0:v]"
            "setpts=PTS+0.001/TB,"
            "scale=iw*0.98:ih*0.98,"
            "crop=iw-8:ih-8:(iw-8)/2:(ih-8)/2,"
            f"{lut_chain}"
            "pad=iw+150:ih+150:75:75:color=black[padded];"
            "[padded][bounce]overlay="
            f"x='abs(mod((t+{delay_x})*{dx},(main_w-w)*2)-(main_w-w))':"
            f"y='abs(mod((t+{delay_y})*{dy},(main_h-h)*2)-(main_h-h))'[b1];"
            "[b1][static]overlay=x=(main_w-w)/2:y=main_h-h-20[b2];"
            "[b2][top]overlay=x='mod(t*100,main_w+w)-w':y=20[step3];"
            "[step3]drawtext="
            "fontfile=/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf:"
            f"text='{wrapped_caption}':"
            "fontcolor=white:fontsize=28:box=1:boxcolor=black@0.6:boxborderw=10:"
            "x=(w-text_w)/2:y=h*0.45:"
            "enable='between(t,0,4)':"
            "alpha='if(lt(t,3),1,1-(t-3))'[captioned];"
            "[captioned]scale='trunc(iw/2)*2:trunc(ih/2)*2'[final]"
        )

        print("🎬 Running first-pass encode...")
        subprocess.run([
            "ffmpeg", "-y", "-i", in_mp4, "-i", wm_file,
            "-filter_complex", fc,
            "-map", "[final]", "-map", "0:a?",
            "-r", str(fr),
            "-g", "48", "-keyint_min", "24", "-sc_threshold", "0",
            "-b:v", "8M", "-maxrate", "8M", "-bufsize", "16M",
            "-preset", "ultrafast",
            "-threads", "0",
            "-t", "40",
            "-c:v", "libx264", "-c:a", "aac",
            "-metadata", metadata,
            mid_mp4
        ], check=True)

        if outro_file:
            concat_list = f"/tmp/{uuid.uuid4()}.txt"
            with open(concat_list, "w") as f:
                f.write(f"file '{mid_mp4}'\n")
                f.write(f"file '{outro_file}'\n")
            subprocess.run([
                "ffmpeg", "-y", "-f", "concat", "-safe", "0",
                "-i", concat_list,
                "-c:v", "libx264", "-c:a", "aac",
                "-metadata", metadata,
                out_mp4
            ], check=True)
        else:
            subprocess.run([
                "ffmpeg", "-y", "-i", mid_mp4,
                "-map_metadata", "-1", "-map_chapters", "-1",
                "-c:v", "copy", "-c:a", "copy",
                "-metadata", metadata,
                out_mp4
            ], check=True)

        if not os.path.exists(out_mp4):
            raise FileNotFoundError(f"Expected output file not found: {out_mp4}")

        print(f"✅ Returning file: {out_mp4}")
        return send_file(out_mp4, as_attachment=True)

    except subprocess.CalledProcessError as e:
        print(f"❌ FFmpeg failed: {e}")
        return {"error": f"FFmpeg failed: {e}"}, 500
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        return {"error": f"Unexpected error: {e}"}, 500
    finally:
        for path in (in_mp4, mid_mp4, out_mp4):
            try: os.remove(path)
            except: pass

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
