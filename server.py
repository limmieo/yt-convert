from flask import Flask, request, send_file
import subprocess
import uuid
import os
import random
import yaml

app = Flask(__name__)

# Load brand configurations from external YAML
config_path = os.path.join(os.getcwd(), "config", "brands.yaml")
with open(config_path, 'r', encoding='utf-8') as cfg_file:
    BRANDS = yaml.safe_load(cfg_file)

@app.route('/process/<brand>', methods=['POST'])
def process_video(brand):
    if brand not in BRANDS:
        return {"error": f"Unsupported brand '{brand}'."}, 400

    data = request.get_json() or {}
    video_url = data.get('video_url')
    if not video_url:
        return {"error": "Missing video_url in request."}, 400

    # Prepare temp file paths
    input_file = f"/tmp/{uuid.uuid4()}.mp4"
    watermarked_file = f"/tmp/{uuid.uuid4()}_marked.mp4"
    final_output = f"/tmp/{uuid.uuid4()}_final.mp4"

    try:
        cfg = BRANDS[brand]
        metadata_tag = cfg['metadata']
        scroll_speed = cfg['scroll_speed']

        assets_dir = os.path.join(os.getcwd(), 'assets')
        watermark_file = os.path.join(assets_dir, random.choice(cfg['watermarks']))
        lut_file = os.path.join(assets_dir, cfg['lut']) if cfg.get('lut') else None
        captions_file = os.path.join(assets_dir, cfg['captions_file'])

        # Download input video
        subprocess.run([
            'wget', '--header=User-Agent: Mozilla/5.0', '-O', input_file, video_url
        ], check=True)

        # Pick a random caption
        with open(captions_file, 'r', encoding='utf-8') as f:
            captions = [line.strip() for line in f if line.strip()]
        caption = random.choice(captions).replace("'", "\\'")

        # Randomized filter parameters
        ob, os_, ot = [round(random.uniform(a, b), 2) for a,b in [(0.6,0.7),(0.85,0.95),(0.4,0.6)]]
        sb, ss, st = [random.uniform(a, b) for a,b in [(0.85,1.0),(1.1,1.25),(0.9,1.1)]]
        fr = round(random.uniform(29.87, 30.1), 3)
        lut_filter = f"lut3d='{lut_file}'," if lut_file else ''

        # Build filter_complex: center caption bar + text, overlays, then scale/pad to 1080x1920 for Reels
        fc = (
            "[1:v]split=3[bounce][static][top];"
            f"[bounce]scale=iw*{sb}:ih*{sb},format=rgba,colorchannelmixer=aa={ob}[b_out];"
            f"[static]scale=iw*{ss}:ih*{ss},format=rgba,colorchannelmixer=aa={os_}[s_out];"
            f"[top]scale=iw*{st}:ih*{st},format=rgba,colorchannelmixer=aa={ot}[t_out];"
            "[0:v]hflip,scale=iw*0.98:ih*0.98,crop=iw-8:ih-8:(iw-8)/2:(ih-8)/2,"
            f"{lut_filter}"
            "pad=iw+16:ih+16:(ow-iw)/2:(oh-ih)/2,"
            "eq=brightness=0.01:contrast=1.02:saturation=1.03,"
            # draw centered bar + text
            "drawbox=x=0:y=(ih-40)/2:width=iw:height=40:color=black@0.6:t=fill:enable='between(t,0,4)',"
            f"drawtext=text='{caption}':fontcolor=white:fontsize=28:x=(w-text_w)/2:y=(h-text_h)/2:enable='between(t,0,4)':alpha='if(lt(t,3),1,1-(t-3))'[base];"
            # overlays
            "[base][b_out]overlay=x='main_w-w-30':y='main_h-h-60'[s1];"
            "[s1][s_out]overlay=x='(main_w-w)/2':y='main_h-h-10'[s2];"
            f"[s2][t_out]overlay=x='mod((t*{scroll_speed}),(main_w+w))-w':y=60[preout];"
            # finally, ensure Reels resolution 1080x1920
            "[preout]scale=1080:1920:force_original_aspect_ratio=decrease,"  
            "pad=1080:1920:(1080-iw)/2:(1920-ih)/2:color=black[final]"
        )

        cmd1 = [
            'ffmpeg', '-i', input_file,
            '-i', watermark_file,
            '-filter_complex', fc,
            '-map', '[final]', '-map', '0:a?',
            '-map_metadata', '-1', '-map_chapters', '-1',
            '-r', str(fr),
            '-g', '48', '-keyint_min', '24', '-sc_threshold', '0',
            # high-quality H.264
            '-c:v', 'libx264', '-crf', '18', '-preset', 'slow', '-profile:v', 'high',
            '-c:a', 'copy',
            '-t', '40',
            '-metadata', metadata_tag,
            watermarked_file
        ]
        subprocess.run(cmd1, check=True)

        # Strip metadata/chapters, copy streams
        cmd2 = [
            'ffmpeg', '-i', watermarked_file,
            '-map_metadata', '-1', '-map_chapters', '-1',
            '-c:v', 'copy', '-c:a', 'copy',
            '-metadata', metadata_tag,
            final_output
        ]
        subprocess.run(cmd2, check=True)

        return send_file(final_output, as_attachment=True)

    except subprocess.CalledProcessError as e:
        return {"error": f"FFmpeg error: {e}"}, 500
    except Exception as e:
        return {"error": f"Unexpected error: {e}"}, 500
    finally:
        for path in (input_file, watermarked_file, final_output):
            if os.path.exists(path):
                os.remove(path)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', '5000')))
