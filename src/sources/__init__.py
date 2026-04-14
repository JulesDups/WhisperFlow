"""
WhisperFlow - Input sources
Sources d'entrée audio alternatives au micro (URL vidéo, fichier local, etc.)
"""

from .video_source import VideoDownloadResult, VideoMetadata, VideoSource

__all__ = ["VideoDownloadResult", "VideoMetadata", "VideoSource"]
