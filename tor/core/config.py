import datetime
import logging
import os
import random
from typing import Dict, List

import redis.exceptions  # type: ignore
from redis import StrictRedis  # type: ignore

from tor import __version__
from tor.core import __HEARTBEAT_FILE__

# Load configuration regardless of if bugsnag is setup correctly
try:
    import bugsnag  # type: ignore
except ImportError:
    # If loading from setup.py or bugsnag isn't installed, we
    # don't want to bomb out completely
    bugsnag = None


_missing = object()


# @see https://stackoverflow.com/a/17487613/1236035
class cached_property(object):
    """A decorator that converts a function into a lazy property.  The
    function wrapped is called the first time to retrieve the result
    and then that calculated result is used the next time you access
    the value::

        class Foo(object):

            @cached_property
            def foo(self):
                # calculate something important here
                return 42

    The class has to have a `__dict__` in order for this property to
    work.
    """

    # implementation detail: this property is implemented as non-data
    # descriptor. non-data descriptors are only invoked if there is no
    # entry with the same name in the instance's __dict__. this allows
    # us to completely get rid of the access function call overhead. If
    # one choses to invoke __get__ by hand the property will still work
    # as expected because the lookup logic is replicated in __get__ for
    # manual invocation.

    def __init__(self, func, name=None, doc=None):
        self.__name__ = name or func.__name__
        self.__module__ = func.__module__
        self.__doc__ = doc or func.__doc__
        self.func = func

    def __get__(self, obj, _type=None):
        if obj is None:
            return self
        value = obj.__dict__.get(self.__name__, _missing)
        if value is _missing:
            value = self.func(obj)
            obj.__dict__[self.__name__] = value
        return value


class BaseConfig:
    """
    A base class used for all media-specific settings, e.g.,
    video, audio, image. This is intended to provide a unified
    interface, regardless of the actual media, to ask questions of
    the configuration:

        - What is the formatting string for this media?
        - What domains are whitelisted for this media?

    The inheritance model here is for easy type-checking from tests,
    allowing for validation of an expected interface in a quicker
    manner.

    Specify overridden values on object instantiation for purposes
    of testing and by pulling from remote source (e.g., Reddit Wiki)
    """

    # Whitelisted domains
    domains: List[str] = []

    formatting = ""


class VideoConfig(BaseConfig):
    """
    Media-specific configuration class for video content

    Initialization should pull from the appropriate Reddit Wiki
    page and fill in the proper values.

    Include any video-specific configuration rules here
    """


class AudioConfig(BaseConfig):
    """
    Media-specific configuration class for audio content

    Initialization should pull from the appropriate Reddit Wiki
    page and fill in the proper values.
    """


class ImageConfig(BaseConfig):
    """
    Media-specific configuration class for image content

    Initialization should pull from the appropriate Reddit Wiki
    page and fill in the proper values.
    """


class OtherContentConfig(BaseConfig):
    """
    Media-specific configuration class for any content that does not
    fit in with the above media types. Articles, mostly.

    Initialization should pull from the appropriate Reddit Wiki
    page and fill in the proper values.
    """


class Subreddit:
    """
    Subreddit-specific configurations

    Intended for asking questions of specific subreddits

    NOTE: WIP - Do not use in its current form
    """

    def __init__(self):
        """
        WIP - Do not use in production code yet
        """
        # TODO: set if upvote filter is needed per-subreddit

    def needs_upvote_filter(self):
        """
        TODO: fill in method based on subreddit rules
        """


class DefaultSubreddit(Subreddit):
    """
    A default configuration for subreddits that don't require
    special rules
    """


class Config(object):
    """
    A singleton object for checking global configuration from
    anywhere in the application
    """

    core_version = __version__
    video_domains: List[str] = []
    audio_domains: List[str] = []
    image_domains: List[str] = []
    video_formatting = ""
    audio_formatting = ""
    image_formatting = ""
    upvote_filter_subs: Dict = {}
    no_link_header_subs: List = []
    tor_mods: List[str] = []

    # Media-specific rules, which are fetchable by a dict key. These
    # are intended to be programmatically accessible based on a
    # parameter given instead of hardcoding the media type in a
    # switch-case style of control structure
    media = {
        "audio": AudioConfig(),
        "video": VideoConfig(),
        "image": ImageConfig(),
        "other": OtherContentConfig(),
    }

    # List of mods of ToR, fetched later using PRAW
    mods: List[str] = []

    # A collection of Subreddit objects, injected later based on
    # subreddit-specific rules
    subreddits: List = []
    subreddits_to_check: List = []
    subreddits_domain_filter_bypass: List = []

    # Templating string for the header of the bot post
    header = ""
    modchat = None  # The actual modchat instance

    no_gifs: List = []

    perform_header_check = True
    debug_mode = False

    # delay times for removing posts; these are used by u/ToR_archivist
    archive_time_default = 0
    archive_time_subreddits: Dict = {}

    # Global flag to enable/disable placing the triggers
    # for the OCR bot
    OCR = True

    # Name of the bot
    name = None
    bot_version = "0.0.0"  # this should get overwritten by the bot process
    # enables debug information for the cherrypy heartbeat server
    heartbeat_logging = False

    last_post_scan_time = datetime.datetime(1970, 1, 1, 1, 1, 1)

    @cached_property
    def bugsnag_api_key(self):
        try:
            return open("bugsnag.key").readline().strip()
        except OSError:
            return os.environ.get("BUGSNAG_API_KEY", None)

    @cached_property
    def redis(self):
        """
        Lazy-loaded redis connection
        """
        try:
            url = os.environ.get("REDIS_CONNECTION_URL", "redis://localhost:6379/0")
            conn = StrictRedis.from_url(url)
            conn.ping()
        except redis.exceptions.ConnectionError:
            logging.fatal("Redis server is not running")
            raise
        return conn

    @cached_property
    def tor(self):
        if self.debug_mode:
            return self.r.subreddit("ModsOfTor")
        else:
            return self.r.subreddit("transcribersofreddit")

    @cached_property
    def heartbeat_port(self):
        try:
            with open(__HEARTBEAT_FILE__, "r") as port_file:
                port = int(port_file.readline().strip())
            logging.debug("Found existing port saved on disk")
            return port
        except OSError:
            pass

        while True:
            port = random.randrange(40000, 40200)  # is 200 ports too much?
            if self.redis.sismember("active_heartbeat_ports", port) == 0:
                self.redis.sadd("active_heartbeat_ports", port)

                with open(__HEARTBEAT_FILE__, "w") as port_file:
                    port_file.write(str(port))
                logging.debug(f"generated port {port} and saved to disk")

                return port


if bugsnag and Config.bugsnag_api_key:
    bugsnag.configure(api_key=Config.bugsnag_api_key, app_version=__version__)

# ----- Compatibility -----
config = Config()
