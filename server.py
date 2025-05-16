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

    input_file = f"/tmp/{uuid.uuid4()}.mp4"
    watermarked_file = f"/tmp/{uuid.uuid4()}_marked.mp4"
    final_output = f"/tmp/{uuid.uuid4()}_final.mp4"

    try:
        cfg = BRANDS[brand]
        metadata_tag = cfg["metadata"]
        speed = cfg["scroll_speed"]
        assets_dir = os.path.join(os.getcwd(), "assets")
        wm = os.path.join(assets_dir, random.choice(cfg["watermarks"]))
        lut_path = os.path.join(assets_dir, cfg["lut"]) if cfg["lut"] else None
        captions_file = os.path.join(assets_dir, cfg["captions_file"])

        subprocess.run([
            "wget", "--header=User-Agent: Mozilla/5.0",
            "-O", input_file, video_url
        ], check=True)

        with open(captions_file, "r", encoding="utf-8") as f:
            lines = [l.strip() for l in f if l.strip()]
        caption = random.choice(lines).replace("'", "\\'")

        ob = round(random.uniform(0.6, 0.7), 2)
        os_ = round(random.uniform(0.85, 0.95), 2)
        ot = round(random.uniform(0.4, 0.6), 2)
        sb = random.uniform(0.85, 1.0)
        ss = random.uniform(1.1, 1.25)
        st = random.uniform(0.9, 1.1)
        fr = round(random.uniform(29.87, 30.1), 3)
        lut_f = f"lut3d='{lut_path}'," if lut_path else ""

        # Caption + background drawn together
        CAP_H = 40
        caption_draw = (
            f"drawbox=x=0:y=(h-{CAP_H})/2:width=iw:height={CAP_H}:"
            "color=black@0.6:t=fill:enable='between(t,0,4)'[boxed];"
            f"[boxed]drawtext=text='{caption}':"
            "fontfile=/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf:"
            "fontcolor=white:fontsize=28:"
            "x=(w-text_w)/2:y=(h-text_h)/2:"
            "enable='between(t,0,4)':alpha='if(lt(t,3),1,1-(t-3))'[base];"
        )

        fc = (
            f"[1:v]split=3[wm_bounce][wm_static][wm_top];"
            f"[wm_bounce]scale=iw*{sb}:ih*{sb},format=rgba,colorchannelmixer=aa={ob}[bounce];"
            f"[wm_static]scale=iw*{ss}:ih*{ss},format=rgba,colorchannelmixer=aa={os_}[static];"
            f"[wm_top]scale=iw*{st}:ih*{st},format=rgba,colorchannelmixer=aa={ot}[top];"
            f"[0:v]hflip,setpts=PTS+0.001/TB,"
              "scale=iw*0.98:ih*0.98,"
              "crop=iw-8:ih-8:(iw-8)/2:(ih-8)/2,"
              f"{lut_f}"
              "pad=iw+16:ih+16:(ow-iw)/2:(oh-ih)/2,"
              "eq=brightness=0.01:contrast=1.02:saturation=1.03[pre];"
            f"[pre]{caption_draw}"
            f"[base][bounce]overlay=x='main_w-w-30+10*sin(t*3)':y='main_h-h-60+5*sin(t*2)'[s1];"
            f"[s1][static]overlay=x='(main_w-w)/2':y='main_h-h-10'[s2];"
            f"[s2][top]overlay=x='mod(t*{speed},main_w+w)-w':y=60,"
              "scale='trunc(iw/2)*2:trunc(ih/2)*2'[final]"
        )

        cmd1 = [
            "ffmpeg", "-i", input_file,
            "-i", wm,
            "-filter_complex", fc,
            "-map", "[final]", "-map", "0:a?",
            "-map_metadata", "-1", "-map_chapters", "-1",
            "-r", str(fr),
            "-g", "48", "-keyint_min", "24", "-sc_threshold", "0",
            "-b:v", "8M", "-maxrate", "8M", "-bufsize", "16M",
            "-preset", "slow",
            "-profile:v", "high",
            "-t", "40",
            "-c:v", "libx264",
            "-c:a", "copy",
            "-metadata", metadata_tag,
            watermarked_file
        ]
        subprocess.run(cmd1, check=True)

        subprocess.run([
            "ffmpeg", "-i", watermarked_file,
            "-map_metadata", "-1", "-map_chapters", "-1",
            "-c:v", "copy", "-c:a", "copy",
            "-metadata", metadata_tag,
            final_output
        ], check=True)

        return send_file(final_output, as_attachment=True)

    except subprocess.CalledProcessError as e:
        return {"error": f"FFmpeg error: {e}"}, 500
    except Exception as e:
        return {"error": f"Unexpected error: {e}"}, 500
    finally:
        for p in (input_file, watermarked_file):
            if os.path.exists(p):
                os.remove(p)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
