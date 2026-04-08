#!/usr/bin/env python3
"""
embed_images.py — Download every remote image referenced in an HTML file,
compress it, and inline it as a base64 data URI so the HTML becomes a
single self-contained file with zero external dependencies.

Usage:
    python3 embed_images.py <input.html> [--output <output.html>]
                            [--max-width 1400] [--quality 78]

By default, edits the input file in place. Pass --output to write a new file.

Requires: pillow, requests
    pip install pillow requests
"""

import argparse
import base64
import io
import os
import re
import sys
from urllib.parse import urlparse

try:
    import requests
    from PIL import Image
except ImportError:
    print("ERROR: requires pillow and requests. Run: pip install pillow requests")
    sys.exit(1)


# Match any http(s) image URL in an src="..." or url(...) context
IMG_URL_PATTERN = re.compile(
    r'https?://[^\s"\'<>()]+\.(?:png|jpg|jpeg|webp|gif)(?:\?[^\s"\'<>()]*)?',
    re.IGNORECASE,
)

MIME_TYPES = {
    "png": "image/png",
    "jpg": "image/jpeg",
    "jpeg": "image/jpeg",
    "webp": "image/webp",
    "gif": "image/gif",
}


def extract_urls(html: str) -> list[str]:
    """Return a deduplicated list of image URLs found in the HTML."""
    urls = []
    seen = set()
    for m in IMG_URL_PATTERN.finditer(html):
        u = m.group(0)
        if u not in seen:
            seen.add(u)
            urls.append(u)
    return urls


def download(url: str, referer: str | None = None) -> bytes:
    """Fetch an image with a realistic User-Agent and optional Referer."""
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/120.0.0.0 Safari/537.36"
        )
    }
    if referer:
        headers["Referer"] = referer
    else:
        parsed = urlparse(url)
        headers["Referer"] = f"{parsed.scheme}://{parsed.netloc}/"

    r = requests.get(url, headers=headers, timeout=30, allow_redirects=True)
    r.raise_for_status()
    return r.content


def compress(
    raw: bytes,
    ext: str,
    max_width: int,
    quality: int,
    bg_color: tuple[int, int, int] = (10, 7, 5),
) -> tuple[bytes, str]:
    """
    Resize + recompress. Returns (new_bytes, final_ext).

    PNGs with transparency stay PNG. WebP and JPEG become JPEG.
    """
    img = Image.open(io.BytesIO(raw))

    w, h = img.size
    if w > max_width:
        new_h = int(h * (max_width / w))
        img = img.resize((max_width, new_h), Image.LANCZOS)

    has_alpha = img.mode in ("RGBA", "LA") or (
        img.mode == "P" and "transparency" in img.info
    )

    out = io.BytesIO()
    if ext == "png" and has_alpha:
        img.save(out, "PNG", optimize=True)
        return out.getvalue(), "png"
    elif ext == "gif":
        return raw, "gif"
    else:
        if has_alpha:
            bg = Image.new("RGB", img.size, bg_color)
            bg.paste(img, mask=img.split()[-1])
            img = bg
        else:
            img = img.convert("RGB")
        img.save(out, "JPEG", quality=quality, optimize=True)
        return out.getvalue(), "jpg"


def to_data_uri(data: bytes, ext: str) -> str:
    mime = MIME_TYPES.get(ext, "application/octet-stream")
    b64 = base64.b64encode(data).decode("ascii")
    return f"data:{mime};base64,{b64}"


def url_extension(url: str) -> str:
    """Pull the file extension from a URL, ignoring query strings."""
    path = urlparse(url).path.lower()
    for ext in ("png", "jpg", "jpeg", "webp", "gif"):
        if path.endswith(f".{ext}"):
            return ext
    return "jpg"


def process(
    input_path: str,
    output_path: str,
    max_width: int,
    quality: int,
    referer: str | None,
) -> None:
    with open(input_path, "r", encoding="utf-8") as f:
        html = f.read()

    urls = extract_urls(html)
    if not urls:
        print("No remote image URLs found.")
        return

    print(f"Found {len(urls)} unique image URL(s). Downloading...")

    replacements: dict[str, str] = {}
    total_original = 0
    total_final = 0

    for i, url in enumerate(urls, 1):
        ext = url_extension(url)
        try:
            raw = download(url, referer=referer)
            total_original += len(raw)
            compressed, final_ext = compress(raw, ext, max_width, quality)
            total_final += len(compressed)
            data_uri = to_data_uri(compressed, final_ext)
            replacements[url] = data_uri
            print(
                f"  [{i}/{len(urls)}] {os.path.basename(urlparse(url).path)}: "
                f"{len(raw)//1024}KB -> {len(compressed)//1024}KB"
            )
        except Exception as e:
            print(f"  [{i}/{len(urls)}] FAILED {url}: {e}")

    # Sort longest-first so URL prefixes don't accidentally match.
    for url in sorted(replacements.keys(), key=len, reverse=True):
        html = html.replace(url, replacements[url])

    with open(output_path, "w", encoding="utf-8") as f:
        f.write(html)

    final_size = os.path.getsize(output_path)
    print()
    print(f"Embedded {len(replacements)}/{len(urls)} images")
    print(f"Image payload: {total_original//1024}KB -> {total_final//1024}KB")
    print(f"Final HTML:    {final_size//1024}KB ({output_path})")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Inline all remote images in an HTML file as base64 data URIs."
    )
    parser.add_argument("input", help="Path to the HTML file to process")
    parser.add_argument("--output", "-o", default=None, help="Output path (default: overwrite input)")
    parser.add_argument("--max-width", type=int, default=1400, help="Max image width in pixels")
    parser.add_argument("--quality", type=int, default=78, help="JPEG quality 1-100")
    parser.add_argument("--referer", default=None, help="Referer header to send")
    args = parser.parse_args()

    output = args.output or args.input
    process(args.input, output, args.max_width, args.quality, args.referer)


if __name__ == "__main__":
    main()
