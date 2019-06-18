import logging
import os
import random
import sys

import redis
from bugsnag.handlers import BugsnagHandler
from praw import Reddit
from slackclient import SlackClient

from tor.core.config import config
from tor.core.heartbeat import configure_heartbeat
from tor.core.helpers import clean_list, get_wiki_page, log_header


def configure_tor(cfg):
    """
    Assembles the tor object based on whether or not we've enabled debug mode
    and returns it. There's really no reason to put together a Subreddit
    object dedicated to our subreddit -- it just makes some future lines
    a little easier to type.

    :param r: the active Reddit object.
    :param cfg: the global config object.
    :return: the Subreddit object for the chosen subreddit.
    """
    if cfg.debug_mode:
        tor = cfg.r.subreddit('ModsOfToR')
    else:
        # normal operation, our primary subreddit
        tor = cfg.r.subreddit('transcribersofreddit')

    return tor


def configure_logging(cfg):
    if cfg.bugsnag_api_key:
        bs_handler = BugsnagHandler()
        bs_handler.setLevel(logging.ERROR)
        logging.getLogger('').addHandler(bs_handler)
        logging.info('Bugsnag enabled!')
    else:
        logging.info('Not running with Bugsnag!')

    log_header('Starting!')


def populate_header(cfg):
    cfg.header = ''
    cfg.header = get_wiki_page('format/header', cfg)


def populate_formatting(cfg):
    """
    Grabs the contents of the three wiki pages that contain the
    formatting examples and stores them in the cfg object.

    :return: None.
    """
    # zero out everything so we can reinitialize later
    cfg.audio_formatting = ''
    cfg.video_formatting = ''
    cfg.image_formatting = ''
    cfg.other_formatting = ''

    cfg.audio_formatting = get_wiki_page('format/audio', cfg)
    cfg.video_formatting = get_wiki_page('format/video', cfg)
    cfg.image_formatting = get_wiki_page('format/images', cfg)
    cfg.other_formatting = get_wiki_page('format/other', cfg)


def populate_domain_lists(cfg):
    """
    Loads the approved content domains into the config object from the
    wiki page.

    :return: None.
    """

    cfg.video_domains = []
    cfg.image_domains = []
    cfg.audio_domains = []

    domains = get_wiki_page('domains', cfg)
    domains = ''.join(domains.splitlines()).split('---')

    for domainset in domains:
        domain_list = domainset[domainset.index('['):].strip('[]').split(', ')
        current_domain_list = []
        if domainset.startswith('video'):
            current_domain_list = cfg.video_domains
        elif domainset.startswith('audio'):
            current_domain_list = cfg.audio_domains
        elif domainset.startswith('images'):
            current_domain_list = cfg.image_domains

        current_domain_list += domain_list
        # [current_domain_list.append(x) for x in domain_list]
        logging.debug(f'Domain list populated: {current_domain_list}')


def populate_moderators(cfg):
    # Praw doesn't cache this information, so it requests it every damn time
    # we ask about the moderators. Let's cache this so we can drastically cut
    # down on the number of calls for the mod list.

    # nuke the existing list
    cfg.tor_mods = []

    # this call returns a full list rather than a generator. Praw is weird.
    cfg.tor_mods = cfg.tor.moderator()


def populate_subreddit_lists(cfg):
    """
    Gets the list of subreddits to monitor and loads it into memory.

    :return: None.
    """

    cfg.subreddits_to_check = []
    cfg.upvote_filter_subs = {}
    cfg.no_link_header_subs = []

    cfg.subreddits_to_check = get_wiki_page('subreddits',
                                            cfg).splitlines()
    cfg.subreddits_to_check = clean_list(cfg.subreddits_to_check)
    logging.debug(
        f'Created list of subreddits from wiki: {cfg.subreddits_to_check}'
    )

    for line in get_wiki_page(
        'subreddits/upvote-filtered', cfg
    ).splitlines():
        if ',' in line:
            sub, threshold = line.split(',')
            cfg.upvote_filter_subs[sub] = int(threshold)

    logging.debug(
        f'Retrieved subreddits subject to the upvote filter: '
        f'{cfg.upvote_filter_subs} '
    )

    cfg.subreddits_domain_filter_bypass = get_wiki_page(
        'subreddits/domain-filter-bypass', cfg
    ).split('\r\n')
    cfg.subreddits_domain_filter_bypass = clean_list(
        cfg.subreddits_domain_filter_bypass
    )
    logging.debug(
        f'Retrieved subreddits that bypass the domain filter: '
        f'{cfg.subreddits_domain_filter_bypass} '
    )

    cfg.no_link_header_subs = get_wiki_page(
        'subreddits/no-link-header', cfg
    ).split('\r\n')
    cfg.no_link_header_subs = clean_list(cfg.no_link_header_subs)
    logging.debug(
        f'Retrieved subreddits subject to the upvote filter: '
        f'{cfg.no_link_header_subs} '
    )

    lines = get_wiki_page('subreddits/archive-time', cfg).splitlines()
    cfg.archive_time_default = int(lines[0])
    cfg.archive_time_subreddits = {}
    for line in lines[1:]:
        if ',' in line:
            sub, time = line.split(',')
            cfg.archive_time_subreddits[sub.lower()] = int(time)


def populate_gifs(cfg):
    # zero it out so we can load more
    cfg.no_gifs = []
    cfg.no_gifs = get_wiki_page('usefulgifs/no', cfg).split('\r\n')


def initialize(cfg):
    populate_domain_lists(cfg)
    logging.debug('Domains loaded.')
    populate_subreddit_lists(cfg)
    logging.debug('Subreddits loaded.')
    populate_formatting(cfg)
    logging.debug('Formatting loaded.')
    populate_header(cfg)
    logging.debug('Header loaded.')
    populate_moderators(cfg)
    logging.debug('Mod list loaded.')
    populate_gifs(cfg)
    logging.debug('Gifs loaded.')


def configure_modchat(cfg):
    # Instead of worrying about creating a connection every time we need
    # to send a message, we'll just make one here and pass it around.
    cfg.modchat = SlackClient(
        os.environ.get('SLACK_API_KEY', None)
    )


def build_bot(
    name,
    version,
    full_name=None,
    require_redis=True,
    heartbeat_logging=False
):
    """
    Shortcut for setting up a bot instance. Runs all configuration and returns
    a valid config object.

    :param name: string; The name of the bot to be started; this name must
        match the settings in praw.ini
    :param version: string; the version number for the current bot being run
    :param full_name: string; the descriptive name of the current bot being
        run; this is used for the heartbeat and status
    :param require_redis: bool; triggers the creation of the Redis instance.
        Any bot that does not require use of Redis can set this to False and
        not have it crash on start because Redis isn't running.
    :return: None
    """

    config.r = Reddit(name)
    # this is used to power messages, so please add a full name if you can
    config.name = full_name if full_name else name
    config.bot_version = version
    config.heartbeat_logging = heartbeat_logging
    configure_modchat(config)

    if not require_redis:
        # I'm sorry
        type(config).redis = property(lambda x: (_ for _ in ()).throw(
            NotImplementedError('Redis was disabled during building!')))

    initialize(config)

    if require_redis:
        # we want this to run after the config object is created
        # and for this version, heartbeat requires db access
        configure_heartbeat(config)

    logging.info('Bot built and initialized!')
