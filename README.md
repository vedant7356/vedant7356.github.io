# 📱 VedantOS — Interactive Mobile Portfolio

A single-page portfolio built as an **Android-style phone OS**. Every section borrows the visual language of a familiar Google app — projects live in a Play Store, achievements in Play Games, community work in a Photos-style memory feed, and the resume in a Files-app viewer — stitched together with scroll-driven animation, haptics, and a hidden train easter egg. 🚂

**🌐 Live:** https://vedantprabhu.dev

It's a fully static site — no build step, no bundler. Just HTML, CSS, and hand-written JavaScript on top of a small custom runtime.

---

## ✨ Features

- 🎬 **Scroll-scrubbed hero** — a 120-frame WebP sequence driven frame-by-frame off scroll position (steadier than autoplay video), with oversized display typography.
- 🛍️ **Projects — Play Store metaphor** — Work / Personal / Early Access tabs, publisher groupings, and per-project detail pages with embedded demo videos.
- 🏆 **Achievements — Play Games styling** — hackathon wins laid out as unlockable game achievements.
- 📸 **Leadership & Community — Google Photos "Memories"** — 3D photo-stack rows for leadership roles, guest lectures, and community work.
- 📄 **Resume — Files by Google viewer** — in-page PDF preview with view/download.
- 🚂 **Boilermaker Special easter egg** — a transparent-video train that crosses the screen on a "Call the Train" button, complete with screen rumble, UI sway, and device haptics. Starts in a "service bay" state; long-press the button (~1.3s) to bring it into service. 🔧
- ⚡ **Full-page boot preloader** — preloads every asset the page references (hero frames, demo videos, section photos, the playable train codec) so nothing streams half-loaded on a phone connection.

---

## 🧰 Tech Stack

**🧱 Core**
- HTML5, CSS3, vanilla JavaScript (ES6+)
- `support.js` — a small custom component / reactive-binding runtime ("dc"), loaded before everything else. All app code is hand-written vanilla JS — no framework code in the page itself (the runtime mounts through a prebuilt React UMD internally).
- Zero build tooling — the source ships as-is.

**🎨 Design system & UI**
- Android / Material-inspired design language throughout
- Google Fonts: **Space Grotesk** (display), **Roboto** & **Roboto Mono** (body / mono), **Material Symbols** (icons)

**🎞️ Media & animation**
- Scroll-scrubbed WebP frame sequence for the hero
- CSS transforms/animations and an SVG animated PCB background with data-pulse effects
- Transparent-video easter egg with per-browser codec selection:
  - Chrome / Firefox / Android → **VP9-alpha WebM**
  - Safari / iOS → **HEVC-with-alpha `.mov`**
  - Fallback → transparent **PNG** cutouts
- 📳 **Web Vibration API** for haptic feedback

**📄 Resume**
- **pdf.js** (via CDN) for the in-page PDF preview
- Resume shipped both as an extracted PDF in `/assets/resume` and base64-embedded in `resume-data.js`

**🛠️ Dev & tooling**
- `serve.py` — a custom Python 3 static server that gets two things right that `http.server` doesn't (see below)
- ffmpeg + Apple `avconvert` for the HEVC-alpha transcode pipeline

**☁️ Hosting**
- GitHub Pages (static)

---

## 🚀 Running Locally

It's a static site, but serve it over HTTP — don't open `index.html` via `file://`, since some media features need a real HTTP origin:

```bash
python3 serve.py 8080     # binds 0.0.0.0
```

Then open http://localhost:8080. To test on a phone on the same Wi-Fi, swap `localhost` for your machine's LAN IP (e.g. `http://192.168.1.23:8080`). 📲

**⚠️ Why `serve.py` instead of `python3 -m http.server`:**

1. **MIME types** — the HEVC train clips are `.mov` and must be sent as `video/quicktime`. The stdlib server may guess `application/octet-stream`, which Safari refuses to decode.
2. **HTTP Range requests** — iOS/iPadOS AVFoundation *requires* real `206` partial responses to play media. `http.server` ignores `Range` and returns `200` with the full body, which iOS treats as a broken media server (video silently never plays; desktop browsers tolerate it). `serve.py` implements proper `206`/`416` handling.

**In production** (nginx, Apache, a CDN, GitHub Pages, Netlify) both are handled for you — just confirm `.mov → video/quicktime` is in the MIME map (nginx: `video/quicktime mov;` in `mime.types`).

---

## 🗂️ Project Structure

```
index.html          The page. Plain HTML/CSS/JS driven by the dc runtime.
support.js          dc runtime (component / binding engine). Loaded first.
resume-data.js      Resume data + the resume PDF as base64 (VP_RESUME_B64).
serve.py            Dev server with correct MIME + HTTP Range support.
assets/
  hero/             120-frame scroll-scrub hero sequence + still frames
  video/            train easter-egg clips + project demo videos
  img/              section / project / certificate / memory images
    certs/  mems/
  resume/           extracted resume PDF (also embedded in resume-data.js)
```

### 🗺️ Asset registry (`window.__resources`)

`index.html` injects `window.__resources` in `<head>` — a map of asset IDs to their `/assets` paths. The boot preloader reads its values to drive the loading progress bar.

---

## 🧭 Browser Support & Media Notes

The Boilermaker Special train renders as **transparent video** where the browser supports an alpha video codec, and falls back to transparent PNGs (`assets/img/train-*.png`) otherwise:

- The boot preloader only fetches the encoding the current browser can actually play (see the filter in `initBoot()`), so no browser downloads the other format's megabytes.
- Codec selection and Safari-safe detection live in `trainMakeVideo()` / `trainDetectAlpha()`.

### 🎥 Regenerating the HEVC `.mov` files

The `.mov` files are transcoded from the VP9-alpha WebM sources. Two gotchas worth documenting:

1. 💡 ffmpeg's **native** `vp9` decoder silently drops the WebM alpha layer and yields opaque video — you **must** force the `libvpx-vp9` input decoder.
2. 💡 The shipped files were produced with **Apple's own encoder** (`avconvert`), not ffmpeg's VideoToolbox wrapper. AVFoundation writes the exact HEVC-alpha auxiliary-layer signaling iOS hardware decoders expect, which third-party muxers can get subtly wrong in ways `ffprobe` won't reveal.

```bash
# 1. Decode WebM alpha (MUST use libvpx-vp9), clean the alpha plane,
#    write a lossless ProRes 4444 intermediate:
ffmpeg -y -c:v libvpx-vp9 -i assets/video/train-pass-1.webm -an \
  -vf "lut=a='if(lt(val,24),0,(val-24)*255/231)'" \
  -c:v prores_ks -profile:v 4444 -pix_fmt yuva444p10le /tmp/prores_1.mov

# 2. Apple-native HEVC-with-alpha:
avconvert --replace --source /tmp/prores_1.mov \
  --preset PresetHEVC1920x1080WithAlpha \
  --output assets/video/train_pass_1_hevc_v3.mov
```

Files are version-suffixed (`_v3`) to bust iOS's aggressive media cache — bump the suffix (and the three references in `index.html`: `window.__resources`, `trainMakeVideo()`, and the `initBoot()` preload filter) whenever you re-encode.

Verify the alpha survived — `ffprobe`'s `pix_fmt` misleadingly reports `yuv420p` for both formats, so decode a frame to RGBA and inspect the alpha byte instead:

```bash
ffmpeg -v error -ss 3 -i assets/video/train_pass_1_hevc_v3.mov -frames:v 1 \
  -pix_fmt rgba -f rawvideo - | python3 -c \
  "import sys;a=sys.stdin.buffer.read()[3::4];print('min alpha',min(a),'-> has transparency' if min(a)<250 else '-> OPAQUE (bad)')"
```

---

## 📝 License

© Vedant. All rights reserved.
