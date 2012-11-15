metadata_root = "/tmp"

subtitle_file_extensions = []

imdb_country = "USA"
imdb_language = "English"
iso_3166_1 = "US"
iso_639_1 = "en"

credit_map = [
    # Title, attribute, limit_category (one of: 'series', 'movies' or None), converter (to change the data; e.g. change a raw timestamp into a month/year for bucketing), reverse sort flag (True or False/None)
    ("By Date Added", "date_added", None, lambda d: time.strftime("%B %Y", time.localtime(d)), True),
    ("By Genre", "genres", None, None, False),
    ("By Film Series", "film_series", "movies", None, False),
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
