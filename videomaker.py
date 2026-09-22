# videomaker.py
# Builds a short vertical quote video: photo + slow zoom + fading caption + optional voice.

import os
import random
import subprocess
import textwrap
import requests

PEXELS_API_KEY = os.environ.get("PEXELS_API_KEY", "")
FONT_PATH = "/usr/share/fonts/truetype/dejavu/DejaVuSerif-Bold.ttf"
ATTRIB_FONT = "/usr/share/fonts/truetype/dejavu/DejaVuSerif.ttf"
TMP_DIR = "/tmp/quotebot"
os.makedirs(TMP_DIR, exist_ok=True)


def fetch_photo(keyword: str, out_path: str) -> str:
    """Download a random free-to-use vertical photo from Pexels matching keyword."""
    url = "https://api.pexels.com/v1/search"
    headers = {"Authorization": PEXELS_API_KEY}
    params = {"query": keyword, "orientation": "portrait", "per_page": 15}
    r = requests.get(url, headers=headers, params=params, timeout=20)
    r.raise_for_status()
    photos = r.json().get("photos", [])
    if not photos:
        raise RuntimeError(f"No photos found for '{keyword}'")
    pick = random.choice(photos)
    img_url = pick["src"]["portrait"]
    img_data = requests.get(img_url, timeout=20).content
    with open(out_path, "wb") as f:
        f.write(img_data)
    return out_path


def wrap_quote(text: str, width: int = 22) -> str:
    """Wrap quote text onto multiple centered lines for the video."""
    return "\n".join(textwrap.wrap(text, width=width))


def make_voice(text: str, out_path: str) -> bool:
    """Generate a spoken version of the quote using gTTS. Returns True if successful."""
    try:
        from gtts import gTTS
        tts = gTTS(text=text, lang="en", slow=False)
        tts.save(out_path)
        return True
    except Exception as e:
        print("Voice generation skipped:", e)
        return False


def build_video(quote: str, attribution: str, photo_path: str, out_path: str,
                 duration: int = 20, voice_path: str = None) -> str:
    """Combine photo + zoom + text into a finished mp4. Returns out_path."""
    quote_file = os.path.join(TMP_DIR, "quote.txt")
    attrib_file = os.path.join(TMP_DIR, "attrib.txt")
    with open(quote_file, "w", encoding="utf-8") as f:
        f.write(wrap_quote(quote))
    with open(attrib_file, "w", encoding="utf-8") as f:
        f.write(attribution)

    frames = duration * 25
    zoom_rate = 0.15 / frames  # spreads the zoom from 1.0 to 1.15 across the full video length
    vf = (
        "scale=2400:3000,"
        "zoompan=z='min(zoom+{zoom_rate},1.15)':d={frames}:s=1080x1350:fps=25,"
        "vignette=PI/5,"
        "drawtext=textfile={qf}:fontfile={font}:fontsize=72:fontcolor=white:"
        "line_spacing=16:x=(w-text_w)/2:y=(h-text_h)/2-60:"
        "alpha='if(lt(t,1),t,1)':shadowcolor=black@0.5:shadowx=2:shadowy=2,"
        "drawtext=textfile={af}:fontfile={afont}:fontsize=32:fontcolor=white@0.85:"
        "x=(w-text_w)/2:y=(h/2)+180:"
        "alpha='if(lt(t,1.3),0,if(lt(t,2.3),(t-1.3),1))'"
    ).format(frames=frames, zoom_rate=zoom_rate, qf=quote_file, font=FONT_PATH,
              af=attrib_file, afont=ATTRIB_FONT)

    cmd = [
        "ffmpeg", "-y", "-loop", "1", "-i", photo_path,
    ]
    if voice_path and os.path.exists(voice_path):
        cmd += ["-i", voice_path]
    cmd += ["-vf", vf, "-t", str(duration), "-r", "25",
            "-c:v", "libx264", "-pix_fmt", "yuv420p"]
    if voice_path and os.path.exists(voice_path):
        cmd += ["-c:a", "aac", "-shortest"]
    cmd += [out_path]

    subprocess.run(cmd, check=True, capture_output=True)
    return out_path
                     
