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
        "caption_file": "thick_asian_captions.txt"
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
        "caption_file": "gym_baddie_captions.txt"
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
        "caption_file": "polishedform_captions.txt"
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
        metadata_key, metadata_value = config["metadata"].split("=")
        scroll_speed = config["scroll_speed"]

        assets_path = os.path.join(os.getcwd(), "assets")
        watermark_choice = os.path.join(assets_path, random.choice(config["watermarks"]))
        lut_path = os.path.join(assets_path, config["lut"]) if config["lut"] else None

        subprocess.run(["wget", "--header=User-Agent: Mozilla/5.0", "-O", input_file, video_url], check=True)

        opacity_bounce = round(random.uniform(0.6, 0.7), 2)
        opacity_static = round(random.uniform(0.85, 0.95), 2)
        opacity_topleft = round(random.uniform(0.4, 0.6), 2)

        scale_bounce = random.uniform(0.85, 1.0)
        scale_static = random.uniform(1.1, 1.25)
        scale_topleft = random.uniform(0.9, 1.1)

        framerate = round(random.uniform(29.87, 30.1), 3)
        lut_filter = f"lut3d='{lut_path}'," if lut_path else ""

        if "caption_file" in config:
            caption_file = os.path.join(assets_path, config["caption_file"])
            with open(caption_file, "r") as f:
                captions = [line.strip() for line in f if line.strip()]
            chosen_caption = random.choice(captions)
            escaped_caption = chosen_caption.replace(":", "\\:").replace("'", "\\'")
            drawtext_filter = (
                f"drawbox=y=0:color=black@0.6:width=iw:height=90:t=fill:"
                f"enable='gte(t,0)':alpha='if(lt(t,3),1,if(lt(t,4),1-(t-3),0))',"
                f"drawtext=fontfile=/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf:"
                f"text='{escaped_caption}':fontcolor=white:fontsize=28:"
                f"x=(w-text_w)/2:"
                f"y='if(lt(t,0.5),0,if(lt(t,0.8),38 - 10*sin((t-0.5)*20),38))':"
                f"line_spacing=10:"
                f"alpha='if(lt(t,3),1,if(lt(t,4),1-(t-3),0))',"
            )
        else:
            drawtext_filter = ""

        filter_complex = (
            f"[1:v]split=3[wm_bounce][wm_static][wm_top];"
            f"[wm_bounce]scale=iw*{scale_bounce}:ih*{scale_bounce},format=rgba,colorchannelmixer=aa={opacity_bounce}[bounce_out];"
            f"[wm_static]scale=iw*{scale_static}:ih*{scale_static},"
            f"format=rgba,colorchannelmixer=aa={opacity_static},boxblur=10:1[blurred_static];"
            f"[wm_top]scale=iw*{scale_topleft}:ih*{scale_topleft},format=rgba,colorchannelmixer=aa={opacity_topleft}[top_out];"
            f"[0:v]hflip,setpts=PTS+0.001/TB,"
            f"scale=iw*0.98:ih*0.98,"
            f"crop=iw-8:ih-8:(iw-8)/2:(ih-8)/2,"
            f"{lut_filter}"
            f"pad=iw+16:ih+16:(ow-iw)/2:(oh-ih)/2,"
            f"eq=brightness=0.01:contrast=1.02:saturation=1.03,"
            f"{drawtext_filter}"
            f"scale='trunc(iw/2)*2:trunc(ih/2)*2'[base];"
            f"[base][bounce_out]overlay=x='main_w-w-30+10*sin(t*3)':y='main_h-h-60+5*sin(t*2)'[step1];"
            f"[step1][blurred_static]overlay=x='(main_w-w)/2':y='main_h-h-10'[step2];"
            f"[step2][top_out]overlay=x='mod((t*{scroll_speed}),(main_w+w))-w':y=60[final]"
        )

        command = [
            "ffmpeg", "-y", "-i", input_file, "-i", watermark_choice,
            "-filter_complex", filter_complex,
            "-map", "[final]", "-map", "0:a?",
            "-map_metadata", "-1", "-map_chapters", "-1",
            "-r", str(framerate),
            "-g", "48", "-keyint_min", "24", "-sc_threshold", "0",
            "-b:v", "5M", "-maxrate", "5M", "-bufsize", "10M",
            "-preset", "ultrafast",
            "-t", "40",
            "-c:v", "libx264", "-c:a", "copy",
            "-metadata", f"{metadata_key}={metadata_value}",
            watermarked_file
        ]

        subprocess.run(command, check=True)

        subprocess.run([
            "ffmpeg", "-y", "-i", watermarked_file,
            "-map_metadata", "-1", "-map_chapters", "-1",
            "-c:v", "copy", "-c:a", "copy",
            "-metadata", f"{metadata_key}={metadata_value}",
            final_output
        ], check=True)

        return send_file(final_output, as_attachment=True)

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
