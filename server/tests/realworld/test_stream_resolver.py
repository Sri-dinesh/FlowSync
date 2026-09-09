import pytest
from app.realworld.pipeline.stream_resolver import StreamResolver


def test_is_stream_url():
    assert StreamResolver.is_stream_url("https://www.youtube.com/watch?v=dQw4w9WgXcQ") is True
    assert StreamResolver.is_stream_url("http://example.com/live.m3u8") is True
    assert StreamResolver.is_stream_url("rtsp://192.168.1.100:554/live") is True
    assert StreamResolver.is_stream_url("C:/videos/traffic.mp4") is False
    assert StreamResolver.is_stream_url("/var/data/video.avi") is False
    assert StreamResolver.is_stream_url("") is False


def test_is_youtube_url():
    assert StreamResolver.is_youtube_url("https://www.youtube.com/watch?v=dQw4w9WgXcQ") is True
    assert StreamResolver.is_youtube_url("https://youtu.be/dQw4w9WgXcQ") is True
    assert StreamResolver.is_youtube_url("https://www.youtube.com/live/dQw4w9WgXcQ") is True
    assert StreamResolver.is_youtube_url("http://youtube.com/watch?v=12345") is True
    assert StreamResolver.is_youtube_url("rtsp://camera.local/stream") is False
    assert StreamResolver.is_youtube_url("https://vimeo.com/123456") is False


@pytest.mark.asyncio
async def test_resolve_passthrough_non_youtube():
    rtsp_url = "rtsp://192.168.1.10:554/h264"
    resolved = await StreamResolver.resolve(rtsp_url)
    assert resolved == rtsp_url

    file_path = "C:/data/video.mp4"
    resolved_file = await StreamResolver.resolve(file_path)
    assert resolved_file == file_path
