default_conf = """
[defaults]
ui = string(default="sdl")
fullscreen = boolean(default=True)
guest_mode = boolean(default=False)
default_subtitles = boolean(default=False)
delayed_rendering = boolean(default=True)

[posters]
poster_width = integer(default=342)

[window]
left_margin = integer(default=0)
right_margin = integer(default=0)
top_margin = integer(default=0)
bottom_margin = integer(default=0)
window_width = integer(default=1366)
window_height = integer(default=768)

[fonts]
font_name = string(default="Liberation Sans")
font_size_menu = integer(min=1, default=16)
font_size_selected = integer(min=1, default=16)
font_size_detail = integer(min=1, default=14)

[metadata]
metadata_root = string
cache_root = string
media_root = string(default=None)
thumbnail_dir = string(default=None)
image_dir = string(default=None)
db_host = string(default=None)
db_file = string(default=None)

[metadata providers]
imdb_cache_dir = string(default="imdb-cache")
imdb_country = string(default="USA")
imdb_language = string(default="English")

tmdb_cache_dir = string(default="tmdb-cache")
iso_3166_1 = string(default="US")
iso_639_1 = string(default="en")
tmdb_poster_size = string(default="w342")

tvdb_cache_dir = string(default="tvdb-cache")

[transcode]
sd_video_bitrate = integer(min=1, default=1800)
hd_width = integer(min=0, default=1280)
hd_560_video_bitrate = integer(min=1, default=2000)
hd_720_video_bitrate = integer(min=1, default=3000)
hd_768_video_bitrate = integer(min=1, default=3200)
hd_1080_video_bitrate = integer(min=1, default=5000)
bonus_bitrate_scale = float(min=0.5, default=0.75)
audio_encoder = string(default="faac")
audio_bitrate = integer(min=1, default=192)
"""

# Subtitles
subtitle_file_extensions = []

user_title_key_map = {}

import time
credit_map = [
    # Title, attribute, limit_category (one of: 'series', 'movies' or None), converter (to change the data; e.g. change a raw timestamp into a month/year for bucketing), reverse sort flag (True or False/None)
    ("By Date Added", "date_added", None, lambda d: time.strftime("%B %Y", time.localtime(d)), True),
    ("By Genre", "genres", None, None, False),
    ("By Film Series", "film_series", "movies", lambda d: unicode(d), False),
    ("By Director", "directors", None, None, False),
    ("By Actor", "cast", None, None, False),
    ("By Executive Producer", "executive_producers", "series", None, False),
    ("By Producer", "producers", "movies", None, False),
    ("By Production Company", "companies", None, None, False),
    ("By Composer", "music", None, None, False),
    ("By Screenwriter", "screenplay_writers", "movies", None, False),
    ("Based on a Novel By", "novel_writers", "movies", None, False),
    ("By Year", "year", None, None, False),
    ("By Years Broadcast", "series_years", "series", None, False),
    ("By Broadcast Network", "network", "series", None, False),
    ("By Number of Seasons", "num_seasons", "series", None, False),
    ("By Rating", "certificate", None, None, False),
    ]

# Clients

client_progs = {
    "game/atari-8bit": "atari800",
    "game/atari-st": "hatari",
    "video/*": "mplayer",
    }

client_args = {
    "atari800": "",
    "hatari": "",
    
    # For mplayer, use SSA/ASS rendering to enable italics, bold, etc
    "mplayer": "-novm -fs -utf8 -ass -ass-color ffffff00 -ass-font-scale 1.4",
    }
