import logging

from bugsnag.handlers import BugsnagHandler

from tor.core.config import config
from tor.core.heartbeat import configure_heartbeat
from tor.core.helpers import clean_list, get_wiki_page, log_header


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
    cfg.header = cfg.get_wiki_page('format/header')


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

    cfg.audio_formatting = cfg.get_wiki_page('format/audio')
    cfg.video_formatting = cfg.get_wiki_page('format/video')
    cfg.image_formatting = cfg.get_wiki_page('format/images')
    cfg.other_formatting = cfg.get_wiki_page('format/other')


def populate_domain_lists(cfg):
    """
    Loads the approved content domains into the config object from the
    wiki page.

    :return: None.
    """

    cfg.video_domains = []
    cfg.image_domains = []
    cfg.audio_domains = []

    domains = cfg.get_wiki_page('domains')
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


def populate_subreddit_lists(cfg):
    """
    Gets the list of subreddits to monitor and loads it into memory.

    :return: None.
    """

    cfg.subreddits_to_check = []
    cfg.upvote_filter_subs = {}
    cfg.no_link_header_subs = []

    cfg.subreddits_to_check = cfg.get_wiki_page('subreddits').splitlines()
    cfg.subreddits_to_check = clean_list(cfg.subreddits_to_check)
    logging.debug(
        f'Created list of subreddits from wiki: {cfg.subreddits_to_check}'
    )

    for line in cfg.get_wiki_page('subreddits/upvote-filtered').splitlines():
        if ',' in line:
            sub, threshold = line.split(',')
            cfg.upvote_filter_subs[sub] = int(threshold)

    logging.debug(
        f'Retrieved subreddits subject to the upvote filter: '
        f'{cfg.upvote_filter_subs} '
    )

    cfg.subreddits_domain_filter_bypass = cfg.get_wiki_page('subreddits/domain-filter-bypass').splitlines()
    cfg.subreddits_domain_filter_bypass = clean_list(cfg.subreddits_domain_filter_bypass)
    logging.debug(
        f'Retrieved subreddits that bypass the domain filter: '
        f'{cfg.subreddits_domain_filter_bypass} '
    )

    cfg.no_link_header_subs = cfg.get_wiki_page('subreddits/no-link-header').splitlines()
    cfg.no_link_header_subs = clean_list(cfg.no_link_header_subs)
    logging.debug(
        f'Retrieved subreddits subject to the upvote filter: '
        f'{cfg.no_link_header_subs} '
    )

    lines = cfg.get_wiki_page('subreddits/archive-time').splitlines()
    cfg.archive_time_default = int(lines[0])
    cfg.archive_time_subreddits = {}
    for line in lines[1:]:
        if ',' in line:
            sub, time = line.split(',')
            cfg.archive_time_subreddits[sub.lower()] = int(time)


def populate_gifs(cfg):
    # zero it out so we can load more
    cfg.no_gifs = []
    cfg.no_gifs = cfg.get_wiki_page('usefulgifs/no').splitlines()


def initialize(cfg):
    populate_domain_lists(cfg)
    logging.debug('Domains loaded.')
    populate_subreddit_lists(cfg)
    logging.debug('Subreddits loaded.')
    populate_formatting(cfg)
    logging.debug('Formatting loaded.')
    populate_header(cfg)
    logging.debug('Header loaded.')
    populate_gifs(cfg)
    logging.debug('Gifs loaded.')


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
    initialize(config)

    # we want this to run after the config object is created
    # and for this version, heartbeat requires db access
    configure_heartbeat(config)

    logging.info('Bot built and initialized!')
