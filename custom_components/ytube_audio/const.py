"""Constants for the ytube-audio integration."""

DOMAIN = "ytube_audio"

CONF_CACHE_DIR = "cache_dir"
CONF_PROXY_STREAM = "proxy_stream"
CONF_DEFAULT_FORMAT = "default_format"
DEFAULT_CACHE_DIR = "/config/ytube_audio_cache"

SERVICE_PLAY_AUDIO = "play_audio"
SERVICE_SEEK = "seek"
SERVICE_ADD_TO_QUEUE = "add_to_queue"
SERVICE_CLEAR_QUEUE = "clear_queue"
SERVICE_NEXT_TRACK = "next_track"
SERVICE_PREVIOUS_TRACK = "previous_track"
SERVICE_GET_QUEUE = "get_queue"
SERVICE_REMOVE_FROM_QUEUE = "remove_from_queue"
SERVICE_SET_REPEAT = "set_repeat"
SERVICE_SET_SHUFFLE = "set_shuffle"
SERVICE_SET_DEFAULT_FORMAT = "set_default_format"

ATTR_URL = "url"
ATTR_MEDIA_PLAYER = "media_player"
ATTR_PROXY = "proxy"
ATTR_FORMAT = "format"
ATTR_TIMESTAMP = "timestamp"
ATTR_PLAY_NOW = "play_now"
ATTR_INDEX = "index"
ATTR_REPEAT = "repeat"
ATTR_SHUFFLE = "shuffle"

PROXY_PATH = "/api/ytube_audio/stream"

FORMAT_BEST = "best"
FORMAT_M4A = "m4a"
FORMAT_MP3 = "mp3"
FORMAT_OPUS = "opus"

AUDIO_FORMATS = {
    FORMAT_BEST: "bestaudio/best",
    FORMAT_M4A: "bestaudio[ext=m4a]/bestaudio/best",
    FORMAT_MP3: "bestaudio",  # Will need post-processing for true MP3
    FORMAT_OPUS: "bestaudio[acodec=opus]/bestaudio/best",
}

DEFAULT_FORMAT = FORMAT_MP3
