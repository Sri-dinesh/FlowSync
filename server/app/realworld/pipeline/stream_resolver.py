"""
StreamResolver — Resolves YouTube live streams, RTSP, and direct HLS URLs into raw stream endpoints.
Uses yt-dlp to extract optimized .m3u8 live stream URLs for OpenCV/FFmpeg consumption.
"""
from __future__ import annotations

import asyncio
import os
import re
import shutil
import time
from typing import Dict, Optional, Tuple

# In-memory cache for resolved stream URLs: {original_url: (resolved_url, expire_timestamp)}
_URL_CACHE: Dict[str, Tuple[str, float]] = {}
CACHE_TTL_SECONDS = 900  # 15 minutes cache for dynamic tokens

YOUTUBE_REGEX = re.compile(
    r"^(https?://)?(www\.)?(youtube\.com/(watch\?.*v=|live/|embed/)|youtu\.be/)[a-zA-Z0-9_-]+"
)


class StreamResolver:
    """Resolves arbitrary video stream URLs (YouTube live, RTSP, HLS, HTTP) into direct stream endpoints."""

    @staticmethod
    def is_stream_url(url: str) -> bool:
        """Returns True if the string is a network stream URL (not a local file path)."""
        if not isinstance(url, str):
            return False
        clean = url.strip().lower()
        return (
            clean.startswith("http://")
            or clean.startswith("https://")
            or clean.startswith("rtsp://")
            or clean.startswith("rtmp://")
        )

    @staticmethod
    def is_youtube_url(url: str) -> bool:
        """Returns True if the URL points to a YouTube video or live broadcast."""
        if not isinstance(url, str):
            return False
        return bool(YOUTUBE_REGEX.match(url.strip()))

    @classmethod
    async def resolve(cls, url: str) -> str:
        """
        Resolves a stream URL to an OpenCV-compatible direct stream URL.
        - YouTube links are resolved via yt-dlp to direct HLS (.m3u8) manifests.
        - RTSP and direct HTTP streams are returned as-is.
        """
        clean_url = url.strip()
        if not cls.is_stream_url(clean_url):
            return clean_url

        # Check cache
        now = time.time()
        if clean_url in _URL_CACHE:
            cached_url, expires_at = _URL_CACHE[clean_url]
            if now < expires_at:
                return cached_url

        # If it's not YouTube, return directly (e.g. rtsp:// or direct .m3u8)
        if not cls.is_youtube_url(clean_url):
            return clean_url

        # Resolve YouTube live stream using yt-dlp in a worker thread
        resolved = await asyncio.to_thread(cls._extract_youtube_stream, clean_url)
        _URL_CACHE[clean_url] = (resolved, now + CACHE_TTL_SECONDS)
        return resolved

    @classmethod
    def _extract_youtube_stream(cls, youtube_url: str) -> str:
        """Synchronous yt-dlp extraction running in background thread."""
        try:
            import yt_dlp
        except ImportError:
            raise RuntimeError("yt-dlp is not installed. Please run: pip install yt-dlp")

        # Resolve node runtime to solve YouTube's n-challenge and avoid CDN throttling/timeouts
        node_path = shutil.which("node")
        if not node_path:
            for candidate in [
                r"C:\Program Files\nodejs\node.exe",
                r"C:\Program Files (x86)\nodejs\node.exe",
                os.path.expanduser(r"~\AppData\Roaming\npm\node.exe"),
            ]:
                if os.path.exists(candidate):
                    node_path = candidate
                    break

        js_runtimes = {"node": {"path": node_path}} if node_path else {}

        # Configure yt-dlp for ultra-fast, low-latency live HLS format selection
        # Specify player_client (android, ios, mweb) to bypass YouTube page reload/bot detection
        ydl_opts = {
            "format": "best[height<=720][protocol^=m3u8]/best[height<=480][protocol^=m3u8]/best[protocol^=m3u8]/best",
            "extractor_args": {
                "youtube": {
                    "player_client": ["android", "ios", "mweb"]
                }
            },
            "js_runtimes": js_runtimes,
            "remote_components": {"ejs:github"},
            "quiet": True,
            "no_warnings": True,
            "skip_download": True,
            "noplaylist": True,
            "extract_flat": False,
            "socket_timeout": 15,
        }

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(youtube_url, download=False)
            if not info:
                raise ValueError(f"Could not extract stream info from: {youtube_url}")

            # 1. Check direct master manifest URL
            if "url" in info and info["url"]:
                return info["url"]

            # 2. Check formats array for HLS (.m3u8)
            formats = info.get("formats", [])
            for fmt in reversed(formats):
                url = fmt.get("url")
                if url and (".m3u8" in url or fmt.get("protocol", "").startswith("m3u8")):
                    return url

            if formats and "url" in formats[-1]:
                return formats[-1]["url"]

            raise ValueError(f"No playable stream format found for: {youtube_url}")
