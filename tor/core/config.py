import datetime
import logging
import os
import random
from typing import List

from tor import __root__, __version__
from tor.core import __HEARTBEAT_FILE__

# Load configuration regardless of if bugsnag is setup correctly
try:
    import bugsnag
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


class SubredditConfig(object):
    """
    A collection of Subreddit objects, injected later based on subreddit-specific rules
    """

    @cached_property
    def subreddits(self) -> List[str]:
        return []  # TODO

    @cached_property
    def subreddits_to_check(self) -> List[str]:
        return []  # TODO

    @cached_property
    def subreddits_domain_filter_bypass(self) -> List[str]:
        return []  # TODO

    @cached_property
    def upvote_filter_subs(self) -> List[str]:
        return {}  # TODO

    @cached_property
    def no_link_header_subs(self) -> List[str]:
        return []  # TODO


class MediaConfig(object):
    @cached_property
    def video_formatting(self):
        return ''  # TODO

    @cached_property
    def audio_formatting(self):
        return ''  # TODO

    @cached_property
    def image_formatting(self):
        return ''  # TODO

    @cached_property
    def video_domains(self):
        return []  # TODO

    @cached_property
    def audio_domains(self):
        return []  # TODO

    @cached_property
    def image_domains(self):
        return []  # TODO


class HomeSubredditInfo(object):
    @cached_property
    def mods(self):
        """List of mods of ToR, fetched using PRAW"""
        return []  # TODO

    @cached_property
    def tor_mods(self):
        return []  # TODO

    @cached_property
    def header(self) -> str:
        """
        Templating string for the header of the bot post
        """
        return ''  # TODO

    @cached_property
    def tor(self):
        if self.debug_mode:
            return self.r.subreddit('ModsOfTor')
        else:
            return self.r.subreddit('transcribersofreddit')

    @cached_property
    def no_gifs(self):
        return []  # TODO


class ArchiveConfig(object):
    @cached_property
    def archive_time_default(self):
        """
        delay time for removing posts

        (these are used by u/ToR_archivist)
        """
        return 0  # TODO

    @cached_property
    def archive_time_subreddits(self):
        """
        delay time for removing posts

        (these are used by u/ToR_archivist)
        """
        return {}  # TODO


class Config(MediaConfig, SubredditConfig, HomeSubredditInfo, ArchiveConfig):
    """
    A singleton object for checking global configuration from
    anywhere in the application
    """

    def __init__(self):
        self.perform_header_check = True
        self.debug_mode = False

        # this should get overwritten by the bot process
        self.name = None
        self.bot_version = __version__

        # Global flag to enable/disable placing the triggers for the OCR bot
        self.OCR = True
        self.heartbeat_logging = False
        self.last_post_scan_time = datetime.datetime(1970, 1, 1, 1, 1, 1)

    @cached_property
    def bugsnag_api_key(self):
        key = None
        try:
            with open('bugsnag.key', 'r') as f:
                key = f.readlines().strip()
                return key
        except OSError:
            key = os.getenv('BUGSNAG_API_KEY')
            return key
        finally:
            # This is why it's important to set the value to `key`:
            if bugsnag and key:
                bugsnag.configure(
                    api_key=key,
                    app_version=__version__,
                    project_root=__root__,
                )

    @cached_property
    def modchat(self):
        """
        Slack Client instance
        """
        return None  # TODO

    @cached_property
    def redis(self):
        """
        Lazy-loaded redis connection
        """
        from redis import StrictRedis
        import redis.exceptions

        try:
            url = os.environ.get('REDIS_CONNECTION_URL',
                                 'redis://localhost:6379/0')
            conn = StrictRedis.from_url(url)
            conn.ping()
        except redis.exceptions.ConnectionError:
            logging.fatal("Redis server is not running")
            raise
        return conn

    @cached_property
    def heartbeat_port(self):
        try:
            with open(__HEARTBEAT_FILE__, 'r') as port_file:
                port = int(port_file.readline().strip())
            logging.debug('Found existing port saved on disk')
            return port
        except OSError:
            pass

        while True:
            port = random.randrange(40000, 40200)  # is 200 ports too much?
            if self.redis.sismember('active_heartbeat_ports', port) == 0:
                self.redis.sadd('active_heartbeat_ports', port)

                with open(__HEARTBEAT_FILE__, 'w') as port_file:
                    port_file.write(str(port))
                logging.debug(f'generated port {port} and saved to disk')

                return port


# ----- Compatibility -----
config = Config()
