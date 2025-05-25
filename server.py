from flask import Flask, request, send_file
import subprocess
import uuid
import os
import random
import textwrap

app = Flask(__name__)

def wrap_caption(caption, width=30):
    lines = textwrap.wrap(caption, width)
    if len(lines) > 2:
        lines = [" ".join(lines[:-1]), lines[-1]]
    return "\\n".join(lines)

@app.route('/process/thick_asian', methods=['POST'])
def process_video():
    video_url = request.json.get('video_url')
    if not video_url:
        return {"error": "Missing video_url in request."}, 400

    # temp file paths
    in_mp4    = f"/tmp/{uuid.uuid4()}.mp4"
    mid_mp4   = f"/tmp/{uuid.uuid4()}_mid.mp4"
    final_mp4 = f"/tmp/{uuid.uuid4()}_final.mp4"

    try:
        assets      = os.path.join(os.getcwd(), "assets")
        watermark   = os.path.join(assets, random.choice([
            "Thick_asian_watermark.png",
            "Thick_asian_watermark_2.png",
            "Thick_asian_watermark_3.png"
        ]))
        lut_path    = os.path.join(assets, "Cobi_3.CUBE")
        captions    = os.path.join(assets, "thick_asian_captions.txt")
        metadata_tag = "brand=thick_asian"

        # 1) download the source
        subprocess.run([
            "wget", "-q", "--header=User-Agent:Mozilla/5.0",
            "-O", in_mp4, video_url
        ], check=True)

        # 2) pick & wrap a caption
        with open(captions, encoding="utf-8") as f:
            pool = [l.strip() for l in f if l.strip()]
        caption = wrap_caption(random.choice(pool))

        # 3) randomize visual params
        ob    = round(random.uniform(0.6, 0.7), 2)
        os_   = round(random.uniform(0.85, 0.95), 2)
        ot    = round(random.uniform(0.4, 0.6), 2)
        sb    = random.uniform(0.85, 1.0)
        ss    = random.uniform(1.1, 1.25)
        st    = random.uniform(0.9, 1.1)
        fr    = round(random.uniform(29.87, 30.1), 3)

        # 4) pick a heart and scale it to 256×256 before overlay
        heart_input = os.path.join(
            assets,
            random.choice(["heart_1.png","heart_2.png","heart_3.png"])
        )

        # 5) assemble the complex filter
        fc = (
            "[1:v]split=3[wb][ws][wt];"
              f"[wb]scale=iw*{sb}:ih*{sb},format=rgba,colorchannelmixer=aa={ob}[bounce];"
              f"[ws]scale=iw*{ss}:ih*{ss},format=rgba,colorchannelmixer=aa={os_}[static];"
              f"[wt]scale=iw*{st}:ih*{st},format=rgba,colorchannelmixer=aa={ot}[top];"

            "[0:v]hflip,setpts=PTS+0.001/TB,"
              "scale=iw*0.98:ih*0.98,"
              "crop=iw-8:ih-8:(iw-8)/2:(ih-8)/2,"
              f"lut3d='{lut_path}',"
              "pad=iw+16:ih+16:(ow-iw)/2:(oh-ih)/2,"
              "eq=brightness=0.01:contrast=1.02:saturation=1.03[base];"

            "[base][bounce]overlay=x=main_w-w-40:y=main_h-h-80[b1];"
            "[b1][static]overlay=x=(main_w-w)/2:y=main_h-h-20[b2];"
            "[b2][top]overlay=x=main_w-w-50:y=60[b3];"

            "[b3]drawtext="
              "fontfile=/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf:"
              f"text='{caption}':"
              "fontcolor=white:fontsize=28:box=1:boxcolor=black@0.6:boxborderw=10:"
              "x=(w-text_w)/2:y=h*0.45:enable='between(t,0,4)':"
              "alpha='if(lt(t,3),1,1-(t-3))'[captioned];"

            # force even dims, then scale down the heart
            "[captioned]scale='trunc(iw/2)*2:trunc(ih/2)*2'[scaled];"
            "[2:v]scale=256:256[heart];"
            "[scaled][heart]overlay=10:10:shortest=1[final]"
        )

        # 6) run ffmpeg (capture stderr so we can debug if it fails)
        cmd = [
            "ffmpeg", "-y",
            "-i", in_mp4,
            "-i", watermark,
            "-i", heart_input,
            "-filter_complex", fc,
            "-map", "[final]",
            "-map", "0:a?",
            "-r", str(fr),
            "-g", "48", "-keyint_min", "24", "-sc_threshold", "0",
            "-b:v", "8M", "-maxrate", "8M", "-bufsize", "16M",
            "-preset", "ultrafast",
            "-t", "40",
            "-c:v", "libx264",
            "-c:a", "copy",
            "-metadata", metadata_tag,
            mid_mp4
        ]
        subprocess.run(cmd, check=True, stderr=subprocess.PIPE)

        # 7) strip all metadata/chapters for final output
        subprocess.run([
            "ffmpeg", "-y",
            "-i", mid_mp4,
            "-map_metadata", "-1",
            "-map_chapters", "-1",
            "-c:v", "copy",
            "-c:a", "copy",
            "-metadata", metadata_tag,
            final_mp4
        ], check=True, stderr=subprocess.PIPE)

        return send_file(final_mp4, as_attachment=True)

    except subprocess.CalledProcessError as e:
        err = e.stderr.decode(errors="ignore")
        return {"error": "FFmpeg failed:\n" + err}, 500

    finally:
        for f in (in_mp4, mid_mp4, final_mp4):
            try: os.remove(f)
            except: pass

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
