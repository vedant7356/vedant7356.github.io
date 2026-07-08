# Vedant Mobile Portfolio

An interactive, Android-flavored mobile portfolio ("VedantOS") — a single-page
static site. Originally mocked up in [Claude Design](https://claude.ai/design)
and restructured here for production: all assets extracted to `/assets`, no build
step required.

## Run it

It's a static site — serve the folder over HTTP (don't open `index.html` via
`file://`, some features need an HTTP origin):

```bash
python3 serve.py 8080     # binds 0.0.0.0; forces correct .mov MIME (see below)
```

Then open <http://localhost:8080>. To test on a phone on the same Wi-Fi, use your
machine's LAN IP instead of `localhost` (e.g. `http://192.168.1.23:8080`).

> Use `serve.py`, not `python3 -m http.server`, for two reasons:
> 1. **MIME** — the HEVC train clips are `.mov` and must be sent as
>    `video/quicktime`; the plain module may guess `application/octet-stream`,
>    which Safari refuses to decode.
> 2. **HTTP Range requests** — iOS/iPadOS AVFoundation *requires* real `206`
>    partial responses to play media; `http.server` ignores `Range` and replies
>    `200` with the full body, which iOS treats as a broken media server (video
>    silently never plays — desktop browsers tolerate it). `serve.py` implements
>    proper `206`/`416` handling.
>
> **Production:** any real web server (nginx, Apache, CDN, GitHub Pages, Netlify)
> already does both correctly — just confirm `.mov → video/quicktime` is in the
> MIME map (nginx: `video/quicktime mov;` in `mime.types`).

## Structure

```
index.html          The page. Plain HTML/CSS/JS driven by the dc runtime.
support.js          dc runtime (component/binding engine). Loaded first.
resume-data.js      Resume data + the resume PDF as base64 (VP_RESUME_B64).
assets/
  hero/             120-frame scroll-scrub hero sequence + still frames
  video/            train easter-egg clips + project demo videos
  img/              section / project / certificate / memory images
    certs/  mems/
  resume/           extracted resume PDF (also embedded in resume-data.js)
```

## Asset registry (`window.__resources`)

`index.html` injects `window.__resources` in `<head>` — a map of the design
bundle's UUIDs to their extracted `/assets` paths. The boot preloader reads its
values to drive the loading progress bar; application logic was left untouched.

## External dependencies (loaded from CDN at runtime)

- Google Fonts (Space Grotesk, Roboto, Roboto Mono, Material Symbols)
- pdf.js (`cdn.jsdelivr.net`) — renders the in-page resume preview

An internet connection is needed for fonts and the resume preview; all other
assets are served locally from `/assets`.

## Notes

- The train "Boilermaker Special" easter egg renders as transparent video where
  the browser supports an alpha video codec, and falls back to transparent PNGs
  (`assets/img/train-*.png`) otherwise:
  - **Chrome / Firefox / Android** → VP9-alpha WebM (`assets/video/train-pass-*.webm`) ✅ present
  - **Safari / iOS** → HEVC-with-alpha `.mov` (`assets/video/train_pass_{1,2}_hevc_v2.mov`) ✅ present
  - Both `.mov` are registered in `window.__resources`; the boot preloader only
    fetches the encoding the current browser can actually play (see the filter in
    `initBoot()`), so no browser downloads the other format's megabytes.
  - Selection + Safari-safe detection lives in `trainMakeVideo()` / `trainDetectAlpha()`
    in `index.html`.
  - **Service mode:** the train starts suspended — tapping the FAB shows an
    "in the service bay" toast instead of dispatching. **Long-press the FAB
    (~1.3s)** to toggle: it shakes, grows, and fills like a progress bar
    (green when enabling, Purdue gold when heading back into service). On
    enable it announces the Purdue Special, runs a first pass immediately,
    then the normal 60s timer takes over.
    Initial state: `this.trainServiceMode = true` in `initTrain()`.
  - The boot screen preloads **everything** the page references (hero frames,
    train media for the playable codec — even while suspended — project videos,
    section photos, CSS backgrounds, linked PDFs), so nothing streams
    half-loaded on first use over mobile connections.

  ### Regenerating the HEVC `.mov` files

  The `.mov` were transcoded from the VP9-alpha WebM sources with ffmpeg + macOS
  VideoToolbox. **Critical gotcha:** ffmpeg's *native* `vp9` decoder silently drops
  the WebM alpha layer (BlockAdditional) and yields opaque video — you **must** force
  the `libvpx-vp9` input decoder or the result is a solid rectangle:

  The deployed `_v3` files were produced with **Apple's own encoder** (`avconvert`,
  macOS built-in) rather than ffmpeg's VideoToolbox wrapper — AVFoundation writes
  the exact HEVC-alpha auxiliary-layer signaling iOS hardware decoders expect,
  which third-party muxers can get subtly wrong in ways `ffprobe` cannot reveal:

  ```bash
  # 1. Decode WebM alpha (MUST use libvpx-vp9 — see gotcha above), clean the
  #    alpha plane (floor <24 to true 0), write a lossless ProRes 4444 intermediate:
  ffmpeg -y -c:v libvpx-vp9 -i assets/video/train-pass-1.webm -an \
    -vf "lut=a='if(lt(val,24),0,(val-24)*255/231)'" \
    -c:v prores_ks -profile:v 4444 -pix_fmt yuva444p10le /tmp/prores_1.mov

  # 2. Apple-native HEVC-with-alpha:
  avconvert --replace --source /tmp/prores_1.mov \
    --preset PresetHEVC1920x1080WithAlpha \
    --output assets/video/train_pass_1_hevc_v3.mov
  ```

  Files are version-suffixed (`_v3`) to bust iOS's aggressive media cache — bump
  the suffix (and the three references in `index.html`: `window.__resources`,
  `trainMakeVideo()`, the `initBoot()` preload filter) whenever you re-encode.
  They're ~7–8 MB each; only Safari/iOS downloads them, and the boot preloader
  fetches just the format the browser can play.

  Verify alpha survived (ffprobe's `pix_fmt` is misleadingly `yuv420p` for both
  WebM and HEVC-alpha — instead decode a frame to RGBA and check the alpha byte):

  ```bash
  ffmpeg -v error -ss 3 -i assets/video/train_pass_1_hevc_v2.mov -frames:v 1 \
    -pix_fmt rgba -f rawvideo - | python3 -c \
    "import sys;a=sys.stdin.buffer.read()[3::4];print('min alpha',min(a),'-> has transparency' if min(a)<250 else '-> OPAQUE (bad)')"
  ```
- The raw Claude Design handoff bundle lives in `_import/` (git-ignored) and is
  not required to run the site.
