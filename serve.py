#!/usr/bin/env python3
"""Static dev server for the portfolio.

Two things matter here that plain `python3 -m http.server` gets wrong:

1. MIME: `.mov` MUST be served as `video/quicktime` (host mimetypes registry
   isn't guaranteed to know it), or Safari refuses the HEVC-alpha train clips.

2. HTTP Range requests: iOS/iPadOS AVFoundation *requires* real 206 partial
   responses to play media — it probes with `Range: bytes=0-1` and walks the
   file in slices. SimpleHTTPRequestHandler ignores Range and replies 200 with
   the full body, which desktop browsers tolerate but iOS treats as a broken
   media server (video never reaches canplay). This handler implements 206.

Usage: python3 serve.py [port]   (defaults to 8080, binds 0.0.0.0)
"""
import os
import re
import sys
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer

SimpleHTTPRequestHandler.extensions_map.update({
    ".mov": "video/quicktime",
    ".mp4": "video/mp4",
    ".webm": "video/webm",
    ".webp": "image/webp",
    ".pdf": "application/pdf",
    ".js": "text/javascript",
})

RANGE_RE = re.compile(r"bytes=(\d*)-(\d*)$")


class Handler(SimpleHTTPRequestHandler):
    def end_headers(self):
        # Assets are fetched twice by design (boot-screen prefetch, then decode
        # into Image/video elements) — the second hit must come from cache, or
        # every frame downloads twice. HTML/JS stay uncached for dev freshness.
        if self.path.startswith("/assets/"):
            self.send_header("Cache-Control", "max-age=3600")
        else:
            self.send_header("Cache-Control", "no-store")
        super().end_headers()

    def send_head(self):
        """Range-aware version of SimpleHTTPRequestHandler.send_head."""
        path = self.translate_path(self.path)
        if os.path.isdir(path) or not os.path.isfile(path):
            return super().send_head()  # directory listings / 404s as usual

        range_header = self.headers.get("Range")
        m = RANGE_RE.match(range_header.strip()) if range_header else None
        f = open(path, "rb")
        try:
            size = os.fstat(f.fileno()).st_size
            ctype = self.guess_type(path)

            if not m:
                self.send_response(200)
                self.send_header("Content-Type", ctype)
                self.send_header("Content-Length", str(size))
                self.send_header("Accept-Ranges", "bytes")
                self.end_headers()
                return f

            start_s, end_s = m.groups()
            if start_s == "":
                # suffix range: last N bytes
                length = min(int(end_s), size)
                start, end = size - length, size - 1
            else:
                start = int(start_s)
                end = min(int(end_s), size - 1) if end_s else size - 1
            if start >= size or start > end:
                self.send_response(416)
                self.send_header("Content-Range", "bytes */%d" % size)
                self.end_headers()
                f.close()
                return None

            self.send_response(206)
            self.send_header("Content-Type", ctype)
            self.send_header("Content-Range", "bytes %d-%d/%d" % (start, end, size))
            self.send_header("Content-Length", str(end - start + 1))
            self.send_header("Accept-Ranges", "bytes")
            self.end_headers()
            f.seek(start)
            f._range_remaining = end - start + 1  # consumed by copyfile below
            return f
        except Exception:
            f.close()
            raise

    def copyfile(self, source, outputfile):
        remaining = getattr(source, "_range_remaining", None)
        if remaining is None:
            return super().copyfile(source, outputfile)
        while remaining > 0:
            chunk = source.read(min(65536, remaining))
            if not chunk:
                break
            outputfile.write(chunk)
            remaining -= len(chunk)


if __name__ == "__main__":
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 8080
    ThreadingHTTPServer(("0.0.0.0", port), Handler).serve_forever()
