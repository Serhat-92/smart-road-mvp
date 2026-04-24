"""Integration tests for RTSP video source."""

import pytest

from ai_inference.pipelines.video_sources import RTSPVideoSource, VideoSourceFactory


def test_rtsp_video_source_factory_creation():
    factory = VideoSourceFactory()
    source_url = "rtsp://admin:admin123@192.168.1.100:554/stream1"
    
    source = factory.create(source_url)
    assert isinstance(source, RTSPVideoSource)
    assert source.source == source_url
    assert source.source_name == source_url


def test_rtsp_video_source_invalid_url():
    with pytest.raises(ValueError, match="RTSP source must start with rtsp://"):
        RTSPVideoSource("http://example.com/video.mp4")


def test_video_source_factory_empty_source():
    factory = VideoSourceFactory()
    with pytest.raises(ValueError, match="Video source must not be empty"):
        factory.create("")
