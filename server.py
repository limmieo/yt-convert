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
        "watermarks": [
            "Thick_asian_watermark.png",
            "Thick_asian_watermark_2.png",
            "Thick_asian_watermark_3.png"
        ]
    },
    "gym_baddie": {
        "metadata": "brand=gym_baddie",
        "lut": "Cobi_3.CUBE",
        "watermarks": [
            "gym_baddie_watermark.png",
            "gym_baddie_watermark_2.png",
            "gym_baddie_watermark_3.png"
        ]
    },
    "polishedform": {
        "metadata": "brand=polishedform",
        "lut": None,
        "watermarks": [
            "polished_watermark.png",
            "polished_watermark_2.png",
            "polished_watermark_3.png"
        ]
    }
}

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
        config = BRANDS[brand]
        metadata = config["metadata"]
        assets = os.path.join(os.getcwd(), "assets")
        wm_file = os.path.join(assets, random.choice(config["watermarks"]))
        lut_file = os.path.join(assets, config["lut"]) if config["lut"] else None

        subprocess.run([
            "wget", "--header=User-Agent: Mozilla/5.0", "-O", in_path, video_url
        ], check=True)

        op_b = round(random.uniform(0.6, 0.7), 2)
        op_s = round(random.uniform(0.85, 0.95), 2)
        op_t = round(random.uniform(0.4, 0.6), 2)
        sc_b = round(random.uniform(0.85, 1.0), 2)
        sc_s = round(random.uniform(1.1, 1.25), 2)
        sc_t = round(random.uniform(0.9, 1.1), 2)
        fps = round(random.uniform(29.87, 30.1), 3)

        lut_cmd = f"lut3d='{lut_file}'," if lut_file else ""

        filter_complex = (
            f"[1:v]split=3[bounce][static][top];"
            f"[bounce]scale=iw*{sc_b}:ih*{sc_b},format=rgba,colorchannelmixer=aa={op_b}[b1];"
            f"[static]scale=iw*{sc_s}:ih*{sc_s},format=rgba,colorchannelmixer=aa={op_s}[b2];"
            f"[top]scale=iw*{sc_t}:ih*{sc_t},format=rgba,colorchannelmixer=aa={op_t}[b3];"
            f"[0:v]hflip,setpts=PTS+0.001/TB,scale=iw*0.98:ih*0.98,"
            f"crop=iw-8:ih-8:(iw-8)/2:(ih-8)/2,{lut_cmd}"
            f"pad=iw+16:ih+16:(ow-iw)/2:(oh-ih)/2,"
            f"eq=brightness=0.01:contrast=1.02:saturation=1.03[base];"
            f"[base][b1]overlay=x='main_w-w-30+10*sin(t*3)':y='main_h-h-60+5*sin(t*2)'[s1];"
            f"[s1][b2]overlay=x='(main_w-w)/2':y='main_h-h-10'[s2];"
            f"[s2][b3]overlay=x='mod((t*80),(main_w+w))-w':y=60,"
            f"scale='trunc(iw/2)*2:trunc(ih/2)*2'[out]"
        )

        subprocess.run([
            "ffmpeg", "-y", "-i", in_path, "-i", wm_file,
            "-filter_complex", filter_complex,
            "-map", "[out]", "-map", "0:a?", "-r", str(fps),
            "-g", "48", "-keyint_min", "24", "-sc_threshold", "0",
            "-b:v", "2.5M", "-maxrate", "2.5M", "-bufsize", "5M",
            "-c:v", "libx264", "-profile:v", "high", "-preset", "fast", "-level", "4.0",
            "-c:a", "copy", "-t", "40", "-metadata", metadata,
            mid_path
        ], check=True)

        subprocess.run([
            "ffmpeg", "-y", "-i", mid_path,
            "-map_metadata", "-1", "-map_chapters", "-1",
            "-c:v", "copy", "-c:a", "copy", "-metadata", metadata,
            out_path
        ], check=True)

        return send_file(out_path, as_attachment=True)

    except subprocess.CalledProcessError as e:
        return {"error": f"FFmpeg failed: {str(e)}"}, 500
    except Exception as e:
        return {"error": f"Unexpected error: {str(e)}"}, 500
    finally:
        for f in (in_path, mid_path):
            try:
                os.remove(f)
            except:
                pass

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
