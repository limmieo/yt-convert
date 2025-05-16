from flask import Flask, request, send_file, jsonify
import subprocess
import uuid
import os
import random
import textwrap

app = Flask(__name__)

# where your assets live
ASSETS_DIR = os.path.join(os.getcwd(), "assets")
os.makedirs("processed", exist_ok=True)

BRANDS = {
    "thick_asian": {
        "metadata": "brand=thick_asian",
        "lut": "Cobi_3.CUBE",
        "watermarks": [
            "Thick_asian_watermark.png",
            "Thick_asian_watermark_2.png",
            "Thick_asian_watermark_3.png"
        ],
        "captions": "thick_asian_captions.txt"
    },
    "gym_baddie": {
        "metadata": "brand=gym_baddie",
        "lut": "Cobi_3.CUBE",
        "watermarks": [
            "gym_baddie_watermark.png",
            "gym_baddie_watermark_2.png",
            "gym_baddie_watermark_3.png"
        ],
        "captions": "gym_baddie_captions.txt"
    },
    "polishedform": {
        "metadata": "brand=polishedform",
        "lut": None,
        "watermarks": [
            "polished_watermark.png",
            "polished_watermark_2.png",
            "polished_watermark_3.png"
        ],
        "captions": "polishedform_captions.txt"
    }
}


def wrap_caption(caption, width=30):
    lines = textwrap.wrap(caption, width=width)
    if len(lines) > 2:
        # fold to two lines
        lines = [" ".join(lines[:-1]), lines[-1]]
    return "\\n".join(lines)


@app.route("/process/<brand>", methods=["POST"])
def process_brand(brand):
    if brand not in BRANDS:
        return jsonify(error=f"Unsupported brand '{brand}'"), 400

    data = request.get_json() or {}
    video_url = data.get("video_url")
    if not video_url:
        return jsonify(error="Missing video_url"), 400

    # temp filenames
    in_mp4  = f"/tmp/{uuid.uuid4()}.mp4"
    mid_mp4 = f"/tmp/{uuid.uuid4()}_mid.mp4"
    out_mp4 = f"/tmp/{uuid.uuid4()}_final.mp4"

    cfg = BRANDS[brand]
    metadata = cfg["metadata"]
    wm_path  = os.path.join(ASSETS_DIR, random.choice(cfg["watermarks"]))
    lut_path = os.path.join(ASSETS_DIR, cfg["lut"]) if cfg["lut"] else None
    caps_path = os.path.join(ASSETS_DIR, cfg["captions"])

    try:
        # 1) download
        subprocess.run([
            "wget", "-q", "--header=User-Agent: Mozilla/5.0",
            "-O", in_mp4, video_url
        ], check=True)

        # 2) pick & wrap a caption
        with open(caps_path, encoding="utf-8") as f:
            lines = [l.strip() for l in f if l.strip()]
        wrapped = wrap_caption(random.choice(lines))

        # 3) randomize watermark parameters
        ob = round(random.uniform(0.6, 0.7), 2)   # bounce opacity
        os_ = round(random.uniform(0.85, 0.95), 2) # static opacity
        ot = round(random.uniform(0.4, 0.6), 2)   # top opacity
        sb = random.uniform(0.85, 1.0)  # bounce scale
        ss = random.uniform(1.1, 1.25)  # static scale
        st = random.uniform(0.9, 1.1)   # top scale
        fr = round(random.uniform(29.87, 30.1), 3)

        lut_filter = f"lut3d={lut_path}," if lut_path else ""

        # 4) build a single, correct filter_complex
        filter_complex = (
            # split watermark into three streams
            "[1:v]split=3[wb][ws][wt];"

            # bounce watermark (bottom-right)
            f"[wb]scale=iw*{sb}:ih*{sb},format=rgba,"
              f"colorchannelmixer=aa={ob}[bounce];"

            # static watermark (center-bottom)
            f"[ws]scale=iw*{ss}:ih*{ss},format=rgba,"
              f"colorchannelmixer=aa={os_}[static];"

            # top watermark (upper-right)
            f"[wt]scale=iw*{st}:ih*{st},format=rgba,"
              f"colorchannelmixer=aa={ot}[top];"

            # base video pipeline: flip, desync, distort, optional LUT
            "[0:v]hflip,setpts=PTS+0.001/TB,"
            "scale=iw*0.98:ih*0.98,"
            "crop=iw-8:ih-8:(iw-8)/2:(ih-8)/2,"
            f"{lut_filter}"
            "pad=iw+16:ih+16:(ow-iw)/2:(oh-ih)/2,"
            "eq=brightness=0.01:contrast=1.02:saturation=1.03[base];"

            # overlay in order
            "[base][bounce]overlay=x=main_w-w-40:y=main_h-h-80[b1];"
            "[b1][static]overlay=x=(main_w-w)/2:y=main_h-h-20[b2];"
            "[b2][top]overlay=x=main_w-w-50:y=60[b3];"

            # draw caption, then force even dims
            "[b3]drawtext="
              "fontfile=/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf:"
              f"text='{wrapped}':"
              "fontcolor=white:fontsize=28:"
              "box=1:boxcolor=black@0.6:boxborderw=10:"
              "x=(w-text_w)/2:y=h*0.45:"
              "enable='between(t,0,4)':"
              "alpha='if(lt(t,3),1,1-(t-3))'[captioned];"
            "[captioned]scale=trunc(iw/2)*2:trunc(ih/2)*2[final]"
        )

        # run ffmpeg, copy audio through
        cmd1 = [
            "ffmpeg", "-y",
            "-i", in_mp4,
            "-i", wm_path,
            "-filter_complex", filter_complex,
            "-map", "[final]",
            "-map", "0:a?",
            "-r", str(fr),
            "-g", "48", "-keyint_min", "24", "-sc_threshold", "0",
            "-b:v", "8M", "-maxrate", "8M", "-bufsize", "16M",
            "-preset", "slow", "-profile:v", "high",
            "-t", "40",
            "-c:v", "libx264",
            "-c:a", "copy",
            "-metadata", metadata,
            mid_mp4
        ]
        subprocess.run(cmd1, check=True)

        # strip all metadata/chapters from final
        cmd2 = [
            "ffmpeg", "-y",
            "-i", mid_mp4,
            "-map_metadata", "-1",
            "-map_chapters", "-1",
            "-c:v", "copy",
            "-c:a", "copy",
            "-metadata", metadata,
            out_mp4
        ]
        subprocess.run(cmd2, check=True)

        return send_file(out_mp4, as_attachment=True)

    except subprocess.CalledProcessError as e:
        return jsonify(error=f"FFmpeg failed: {e.stderr or e}"), 500

    finally:
        for fn in (in_mp4, mid_mp4):
            try:
                os.remove(fn)
            except OSError:
                pass


if __name__ == "__main__":
    # specify debug=False in Prod
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)), debug=True)
