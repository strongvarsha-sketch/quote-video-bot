# videomaker.py
# Builds a short vertical quote video: photo + slow zoom + fading caption + optional voice.

import os
import random
import subprocess
import textwrap
import requests

PEXELS_API_KEY = os.environ.get("PEXELS_API_KEY", "")
TMP_DIR = "/tmp/quotebot"
os.makedirs(TMP_DIR, exist_ok=True)


def _resolve_font(family: str) -> str:
    """Ask fontconfig for the actual file path of a font family.
    This avoids hardcoding paths that can differ between systems."""
    try:
        out = subprocess.run(
            ["fc-match", "-f", "%{file}", family],
            capture_output=True, text=True, check=True, timeout=5,
        )
        path = out.stdout.strip()
        if path and os.path.exists(path):
            return path
    except Exception as e:
        print(f"Font lookup failed for '{family}':", e)
    return "/usr/share/fonts/truetype/dejavu/DejaVuSerif-Bold.ttf"  # safe fallback


# Resolved once at import time.
FONT_LATIN_BOLD = _resolve_font("DejaVu Serif:bold")
FONT_LATIN_REGULAR = _resolve_font("DejaVu Serif")
FONT_DEVANAGARI_BOLD = _resolve_font("Noto Sans Devanagari:bold")
FONT_DEVANAGARI_REGULAR = _resolve_font("Noto Sans Devanagari")

# Keep these names for backward compatibility with the rest of the module.
FONT_PATH = FONT_LATIN_BOLD
ATTRIB_FONT = FONT_LATIN_REGULAR


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


def fetch_photos(keywords: list, count: int, out_dir: str) -> list:
    """Download `count` distinct photos, one per keyword (cycling through keywords if needed)."""
    chosen_keywords = random.sample(keywords, k=min(count, len(keywords)))
    while len(chosen_keywords) < count:
        chosen_keywords.append(random.choice(keywords))
    paths = []
    for i, kw in enumerate(chosen_keywords):
        out_path = os.path.join(out_dir, f"photo_{i}.jpg")
        fetch_photo(kw, out_path)
        paths.append(out_path)
    return paths


def wrap_quote(text: str, width: int = 22) -> str:
    """Wrap quote text onto multiple centered lines for the video."""
    return "\n".join(textwrap.wrap(text, width=width))


def make_voice(text: str, out_path: str, lang: str = "en") -> bool:
    """Generate a spoken version of the quote using gTTS. Returns True if successful.
    Wrapped with a timeout so a slow/unresponsive TTS service can't hang the bot forever."""
    import concurrent.futures

    def _generate():
        from gtts import gTTS
        tts = gTTS(text=text, lang=lang, slow=False)
        tts.save(out_path)

    try:
        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as ex:
            future = ex.submit(_generate)
            future.result(timeout=15)
        return True
    except Exception as e:
        print("Voice generation skipped (timed out or failed):", e)
        return False


def build_video(quote: str, attribution: str, photo_paths, out_path: str,
                 duration: int = 20, voice_path: str = None, lang: str = "en") -> str:
    """Combine 1+ photos (crossfading between them) + zoom + text into a finished mp4."""
    if isinstance(photo_paths, str):
        photo_paths = [photo_paths]
    n = len(photo_paths)

    font_bold = FONT_DEVANAGARI_BOLD if lang == "hi" else FONT_LATIN_BOLD
    font_regular = FONT_DEVANAGARI_REGULAR if lang == "hi" else FONT_LATIN_REGULAR

    quote_file = os.path.join(TMP_DIR, "quote.txt")
    attrib_file = os.path.join(TMP_DIR, "attrib.txt")
    with open(quote_file, "w", encoding="utf-8") as f:
        f.write(wrap_quote(quote, width=18 if lang == "hi" else 22))
    with open(attrib_file, "w", encoding="utf-8") as f:
        f.write(attribution)

    transition = 1.2 if n > 1 else 0.0
    clip_dur = (duration + (n - 1) * transition) / n
    frames_per_clip = max(1, int(round(clip_dur * 25)))
    zoom_rate = 0.15 / frames_per_clip

    # Build ffmpeg inputs: one looped image per clip.
    cmd = ["ffmpeg", "-y"]
    for p in photo_paths:
        cmd += ["-loop", "1", "-t", f"{clip_dur:.3f}", "-i", p]
    audio_index = n
    if voice_path and os.path.exists(voice_path):
        cmd += ["-i", voice_path]

    # Per-clip zoom filters.
    filter_parts = []
    for i in range(n):
        filter_parts.append(
            f"[{i}:v]scale=2400:3000,"
            f"zoompan=z='min(zoom+{zoom_rate:.6f},1.15)':d={frames_per_clip}:s=1080x1350:fps=25[z{i}]"
        )

    # Crossfade the clips together in sequence.
    if n == 1:
        merged_label = "z0"
    else:
        offset = clip_dur - transition
        filter_parts.append(
            f"[z0][z1]xfade=transition=fade:duration={transition:.3f}:offset={offset:.3f}[x1]"
        )
        cumulative = clip_dur * 2 - transition
        prev = "x1"
        for i in range(2, n):
            offset = cumulative - transition
            filter_parts.append(
                f"[{prev}][z{i}]xfade=transition=fade:duration={transition:.3f}:offset={offset:.3f}[x{i}]"
            )
            prev = f"x{i}"
            cumulative = cumulative + clip_dur - transition
        merged_label = prev

    # Caption overlay, applied once across the whole merged video.
    filter_parts.append(
        f"[{merged_label}]vignette=PI/5,"
        f"drawtext=textfile={quote_file}:fontfile={font_bold}:fontsize=72:fontcolor=white:"
        f"line_spacing=16:x=(w-text_w)/2:y=(h-text_h)/2-60:"
        f"alpha='if(lt(t,1),t,1)':shadowcolor=black@0.5:shadowx=2:shadowy=2,"
        f"drawtext=textfile={attrib_file}:fontfile={font_regular}:fontsize=32:fontcolor=white@0.85:"
        f"x=(w-text_w)/2:y=(h/2)+180:"
        f"alpha='if(lt(t,1.3),0,if(lt(t,2.3),(t-1.3),1))'[vout]"
    )

    filter_complex = ";".join(filter_parts)
    cmd += ["-filter_complex", filter_complex, "-map", "[vout]"]
    if voice_path and os.path.exists(voice_path):
        cmd += ["-map", f"{audio_index}:a", "-c:a", "aac", "-shortest"]
    cmd += ["-t", str(duration), "-r", "25", "-c:v", "libx264", "-pix_fmt", "yuv420p", out_path]

    subprocess.run(cmd, check=True, capture_output=True, timeout=120)
    return out_path
                     
