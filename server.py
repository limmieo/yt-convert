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

@app.route('/process/<brand>', methods=['POST'])
def process_video(brand):
    if brand not in BRANDS:
        return {"error": f"Unsupported brand '{brand}'."}, 400

    data = request.get_json()
    video_url = data.get('video_url') if data else None
    if not video_url:
        return {"error": "Missing video_url in request."}, 400

    # temp filenames
    input_file      = f"/tmp/{uuid.uuid4()}.mp4"
    watermarked_file= f"/tmp/{uuid.uuid4()}.mp4"
    final_output    = f"/tmp/{uuid.uuid4()}.mp4"

    try:
        cfg = BRANDS[brand]
        metadata_tag = cfg["metadata"]

        assets = os.path.join(os.getcwd(), "assets")
        watermark = os.path.join(assets, random.choice(cfg["watermarks"]))
        lut_path   = os.path.join(assets, cfg["lut"]) if cfg["lut"] else None
        captions_f = os.path.join(assets, cfg["captions_file"])

        # 1) Download source via yt-dlp
        subprocess.run([
            "yt-dlp", "-f", "bv*+ba/best",
            "-o", input_file,
            video_url
        ], check=True)

        # 2) Pick a random caption
        with open(captions_f, "r", encoding="utf-8") as f:
            captions = [l.strip() for l in f if l.strip()]
        caption = random.choice(captions).replace("'", r"\'")

        # watermarks: slightly bigger/more opaque
        opacity_wm = round(random.uniform(0.7, 0.85), 2)
        scale_wm   = random.uniform(0.9, 1.1)

        # brief on-screen caption for first 4s
        text_filt = (
            "drawbox=x=0:y=60:width=iw:height=50:color=black@0.6:t=fill:enable='between(t,0,4)',"
            f"drawtext=text='{caption}':fontcolor=white:fontsize=30:"
            "x=(w-text_w)/2:y=70:enable='between(t,0,4)':"
            "alpha='if(lt(t,3),1,1-(t-3))'"
        )

        # optional LUT
        lut_filt = f"lut3d='{lut_path}'," if lut_path else ""

        # build a single static‐overlay chain
        filter_complex = (
            # prepare watermark stream
            f"[1:v]scale=iw*{scale_wm}:ih*{scale_wm},format=rgba,"
            f"colorchannelmixer=aa={opacity_wm}[wm];"
            # base video pipeline
            f"[0:v]hflip,setpts=PTS+0.001/TB,"
            f"scale=iw*0.98:ih*0.98,"
            f"crop=iw-8:ih-8:(iw-8)/2:(ih-8)/2,"
            f"{lut_filt}"
            "pad=iw+16:ih+16:(ow-iw)/2:(oh-ih)/2,"
            "eq=brightness=0.01:contrast=1.02:saturation=1.03,"
            f"{text_filt}[base];"
            # overlay watermark bottom-right
            "[base][wm]overlay="
            "x=main_w-w-30:y=main_h-h-60,"
            # ensure even dims
            "scale='trunc(iw/2)*2:trunc(ih/2)*2'[final]"
        )

        # 3) Run ffmpeg
        cmd = [
            "ffmpeg", "-y",
            "-i", input_file,
            "-i", watermark,
            "-filter_complex", filter_complex,
            "-map", "[final]",
            "-map", "0:a?",
            "-map_metadata", "-1",
            "-map_chapters", "-1",
            "-c:v", "libx264",
            "-preset", "superfast",
            "-crf", "20",
            "-c:a", "copy",
            "-t", "40",
            "-metadata", metadata_tag,
            watermarked_file
        ]
        subprocess.run(cmd, check=True)

        # 4) Final remux (strip all metadata & just copy)
        subprocess.run([
            "ffmpeg", "-y",
            "-i", watermarked_file,
            "-map_metadata", "-1",
            "-map_chapters", "-1",
            "-c:v", "copy",
            "-c:a", "copy",
            "-metadata", metadata_tag,
            final_output
        ], check=True)

        # 5) Return
        return send_file(final_output, as_attachment=True)

    except subprocess.CalledProcessError as e:
        return {"error": f"Processing error: {e}"}, 500
    except Exception as e:
        return {"error": f"Unexpected error: {e}"}, 500
    finally:
        # cleanup
        for f in (input_file, watermarked_file, final_output):
            if os.path.exists(f):
                os.remove(f)

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
