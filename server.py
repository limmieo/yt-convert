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
        scroll_speed = cfg["scroll_speed"]

        assets = os.path.join(os.getcwd(), "assets")
        watermark = os.path.join(assets, random.choice(cfg["watermarks"]))
        lut = os.path.join(assets, cfg["lut"]) if cfg["lut"] else None
        caps = os.path.join(assets, cfg["captions_file"])

        subprocess.run(["wget", "--header=User-Agent: Mozilla/5.0", "-O", input_file, video_url], check=True)

        with open(caps, "r", encoding="utf-8") as f:
            lines = [l.strip() for l in f if l.strip()]
        caption = random.choice(lines).replace("'", "\\'")

        # dynamic parameters
        ob, os_, ot = [round(random.uniform(a, b), 2) for a,b in [(0.6,0.7),(0.85,0.95),(0.4,0.6)]]
        sb, ss, st = [random.uniform(a, b) for a,b in [(0.85,1.0),(1.1,1.25),(0.9,1.1)]]
        fr = round(random.uniform(29.87, 30.1), 3)
        lut_f = f"lut3d='{lut}'," if lut else ""

        # caption/text overlay
        text_f = (
            "drawbox=x=0:y=60:width=iw:height=40:color=black@0.6:t=fill:enable='between(t,0,4)',"
            f"drawtext=text='{caption}':fontcolor=white:fontsize=28:x=(w-text_w)/2:y=70:"
            "enable='between(t,0,4)':alpha='if(lt(t,3),1,1-(t-3))'"
        )

        fc = (
            "[1:v]split=3[wm_b][wm_s][wm_t];"
            f"[wm_b]scale=iw*{sb}:ih*{sb},format=rgba,colorchannelmixer=aa={ob}[b_out];"
            f"[wm_s]scale=iw*{ss}:ih*{ss},format=rgba,colorchannelmixer=aa={os_}[s_out];"
            f"[wm_t]scale=iw*{st}:ih*{st},format=rgba,colorchannelmixer=aa={ot}[t_out];"
            "[0:v]hflip,setpts=PTS+0.001/TB,"
            "scale=iw*0.98:ih*0.98,"
            "crop=iw-8:ih-8:(iw-8)/2:(ih-8)/2,"
            f"{lut_f}"
            "pad=iw+16:ih+16:(ow-iw)/2:(oh-ih)/2,"
            "eq=brightness=0.01:contrast=1.02:saturation=1.03,"
            f"{text_f}[base];"
            "[base][b_out]overlay=x='main_w-w-30+10*sin(t*3)':y='main_h-h-60+5*sin(t*2)'[s1];"
            "[s1][s_out]overlay=x='(main_w-w)/2':y='main_h-h-10'[s2];"
            f"[s2][t_out]overlay=x='mod((t*{scroll_speed}),(main_w+w))-w':y=60,scale='trunc(iw/2)*2:trunc(ih/2)*2'[final]"
        )

        cmd1 = [
            "ffmpeg", "-i", input_file,
            "-i", watermark,
            "-filter_complex", fc,
            "-map", "[final]", "-map", "0:a?",
            "-map_metadata", "-1", "-map_chapters", "-1",
            "-r", str(fr),
            "-g", "48", "-keyint_min", "24", "-sc_threshold", "0",
            "-crf", "0", "-preset", "placebo", "-profile:v", "high444",
            "-t", "40",
            "-c:v", "libx264", "-c:a", "copy",
            "-metadata", metadata_tag,
            watermarked_file
        ]
        subprocess.run(cmd1, check=True)

        cmd2 = [
            "ffmpeg", "-i", watermarked_file,
            "-map_metadata", "-1", "-map_chapters", "-1",
            "-c:v", "copy", "-c:a", "copy",
            "-metadata", metadata_tag,
            final_output
        ]
        subprocess.run(cmd2, check=True)

        return send_file(final_output, as_attachment=True)

    except subprocess.CalledProcessError as e:
        return {"error": f"FFmpeg error: {e}"}, 500
    except Exception as e:
        return {"error": f"Unexpected error: {e}"}, 500
    finally:
        for path in (input_file, watermarked_file):
            if os.path.exists(path):
                os.remove(path)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", "5000")))
