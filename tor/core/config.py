import datetime
import logging
import os
import random
from typing import List

import praw
import prawcore.exceptions
from slackclient import SlackClient

from tor import __friendly_name__, __root__, __version__
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


# @api private
class BotInfo(object):
    @cached_property
    def name(self):
        """
        This is used to power messages, so please add a full name if you can
        """
        if __friendly_name__:
            return __friendly_name__
        else:
            return self.bot_name

    @cached_property
    def bot_name(self):
        if self.debug_mode:
            return 'debug'
        else:
            return os.getenv('BOT_NAME', 'bot')

    @cached_property
    def bot_version(self):
        return __version__

    @cached_property
    def OCR(self):
        """
        Global flag to enable/disable placing the triggers for the OCR bot
        """
        return True

    @cached_property
    def debug_mode(self):
        return bool(os.getenv('DEBUG_MODE', ''))

    @cached_property
    def noop_mode(self):
        return bool(os.getenv('NOOP_MODE', ''))

    @cached_property
    def perform_header_check(self):
        return True

    @cached_property
    def heartbeat_logging(self):
        return False

    @cached_property
    def last_post_scan_time(self):
        return datetime.datetime(1970, 1, 1, 1, 1, 1)


# @api private
class ServiceConfig(BotInfo):
    @cached_property
    def modchat(self):
        """
        Slack Client instance
        """
        return SlackClient(
            os.getenv('SLACK_API_KEY')
        )

    @cached_property
    def r(self):
        return praw.Reddit(self.bot_name)

    @cached_property
    def tor(self):
        """
        Assembles the tor object based on whether or not
        we've enabled debug mode and returns it. There's
        really no reason to put together a Subreddit
        object dedicated to our subreddit -- it just
        makes some future lines a little easier to type.
        """
        if self.debug_mode:
            return self.r.subreddit('ModsOfToR')
        else:
            return self.r.subreddit('transcribersofreddit')

    def get_wiki_page(self, page_name):
        """
        Return the contents of a given wiki page.

        :param page_name: String. The name of the page to be requested.
        :return: String or None. The content of the requested page if
            present else None.
        """
        logging.debug(f'Retrieving wiki page {page_name}')
        try:
            result = self.tor.wiki[page_name].content_md
            if result != '':
                return result
        except prawcore.exceptions.NotFound:
            pass
        return None

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


# @api private
class SubredditConfig(ServiceConfig):
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


# @api private
class MediaConfig(ServiceConfig):
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

    @cached_property
    def __domains(self):
        pass  # TODO


# @api private
class HomeSubredditInfo(ServiceConfig):
    @cached_property
    def mods(self):
        """List of mods of ToR, fetched using PRAW"""
        return list(self.tor.moderator())

    @cached_property
    def tor_mods(self):
        return list(self.tor.moderator())

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


# @api private
class ArchiveConfig(ServiceConfig):
    # TODO: Remove this class since we don't need it for the ToR moderator bot

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


class Config(BotInfo, MediaConfig, SubredditConfig, HomeSubredditInfo, ArchiveConfig):
    """
    A singleton object for checking global configuration from
    anywhere in the application
    """
    pass


# ----- Compatibility -----
config = Config()
