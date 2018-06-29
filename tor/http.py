import requests

from tor import __version__


class Http(requests.Session):
    """
    A reusable HTTP client for interacting with Reddit
    """

    def __init__(self, *args, **kwargs):
        super(Http, self).__init__(*args, **kwargs)
        self.headers.update(
            {
                "User-Agent": f"python:org.grafeas.tor:v{__version__} "
                "(by the mods of /r/TranscribersOfReddit)"
            }
        )
