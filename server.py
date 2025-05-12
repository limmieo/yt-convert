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
        config = BRANDS[brand]
        metadata_tag = config["metadata"]
        scroll_speed = config["scroll_speed"]

        assets_path = os.path.join(os.getcwd(), "assets")
        watermark_choice = os.path.join(assets_path, random.choice(config["watermarks"]))
        lut_path = os.path.join(assets_path, config["lut"]) if config["lut"] else None
        caption_file = os.path.join(assets_path, config["captions_file"])

        print(f"[DEBUG] Downloading with yt-dlp: {video_url}")
        subprocess.run([
            "yt-dlp",
            "-f", "bv*[vcodec^=avc1]+ba/best",
            "-o", input_file,
            video_url
        ], check=True)
        print(f"[DEBUG] Video downloaded to: {input_file}")
        print(f"[DEBUG] Watermark used: {watermark_choice}")

        with open(caption_file, "r", encoding="utf-8") as f:
            captions = [line.strip() for line in f if line.strip()]
        selected_caption = random.choice(captions).replace("'", "\\'")

        opacity_bounce = round(random.uniform(0.6, 0.7), 2)
        opacity_static = round(random.uniform(0.85, 0.95), 2)
        opacity_topleft = round(random.uniform(0.4, 0.6), 2)

        scale_bounce = random.uniform(0.85, 1.0)
        scale_static = random.uniform(1.1, 1.25)
        scale_topleft = random.uniform(0.9, 1.1)

        framerate = round(random.uniform(29.87, 30.1), 3)
        lut_filter = f"lut3d='{lut_path}'," if lut_path else ""

        text_filters = (
            "drawbox=x=0:y=60:width=iw:height=40:color=black@0.6:t=fill:enable='between(t,0,4)',"
            f"drawtext=text='{selected_caption}':fontcolor=white:fontsize=28:x=(w-text_w)/2:y=70:enable='between(t,0,4)':alpha='if(lt(t,3),1,1-(t-3))'"
        )

        filter_complex = (
            f"format=yuv420p,"
            f"[1:v]loop=loop=-1:size=1:start=0,split[wm_bounce][wm_static][wm_top];"
            f"[wm_bounce]scale=iw*{scale_bounce}:ih*{scale_bounce},format=rgba,colorchannelmixer=aa={opacity_bounce}[bounce_out];"
            f"[wm_static]scale=iw*{scale_static}:ih*{scale_static},format=rgba,colorchannelmixer=aa={opacity_static}[static_out];"
            f"[wm_top]scale=iw*{scale_topleft}:ih*{scale_topleft},format=rgba,colorchannelmixer=aa={opacity_topleft}[top_out];"
            f"[0:v]hflip,setpts=PTS+0.001/TB,"
            f"scale=iw*0.98:ih*0.98,"
            f"crop=iw-8:ih-8:(iw-8)/2:(ih-8)/2,"
            f"{lut_filter}"
            f"pad=iw+16:ih+16:(ow-iw)/2:(oh-ih)/2,"
            f"eq=brightness=0.01:contrast=1.02:saturation=1.03,"
            f"{text_filters}[base];"
            f"[base][bounce_out]overlay=x='main_w-w-30+10*sin(t*3)':y='main_h-h-60+5*sin(t*2)'[step1];"
            f"[step1][static_out]overlay=x='(main_w-w)/2':y='main_h-h-10'[step2];"
            f"[step2][top_out]overlay=x='mod((t*{scroll_speed}),(main_w+w))-w':y=60,"
            f"scale='trunc(iw/2)*2:trunc(ih/2)*2'[final]"
        )

        print(f"[DEBUG] Final filter_complex string:\n{filter_complex}")

        command = [
            "ffmpeg", "-i", input_file,
            "-i", watermark_choice,
            "-filter_complex", filter_complex,
            "-map", "[final]", "-map", "0:a?",
            "-map_metadata", "-1", "-map_chapters", "-1",
            "-r", str(framerate),
            "-g", "48", "-keyint_min", "24", "-sc_threshold", "0",
            "-c:v", "libx265", "-preset", "medium",
            "-crf", "20",
            "-b:v", "10M", "-maxrate", "15M", "-bufsize", "30M",
            "-t", "40",
            "-c:a", "copy",
            "-metadata", metadata_tag,
            watermarked_file
        ]

        subprocess.run(command, check=True)

        subprocess.run([
            "ffmpeg", "-i", watermarked_file,
            "-map_metadata", "-1", "-map_chapters", "-1",
            "-c:v", "copy", "-c:a", "copy",
            "-metadata", metadata_tag,
            final_output
        ], check=True)

        return {
            "status": "success",
            "original_caption": request.json.get("original_caption", ""),
            "message": "Video processed successfully."
        }

    except subprocess.CalledProcessError as e:
        return {"error": f"FFmpeg error: {str(e)}"}, 500
    except Exception as e:
        return {"error": f"Unexpected error: {str(e)}"}, 500
    finally:
        for f in [input_file, watermarked_file]:
            if os.path.exists(f): os.remove(f)

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
