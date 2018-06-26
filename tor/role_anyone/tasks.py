from tor_core import OUR_BOTS
from tor_core.config import Config
from tor_core.users import User
from tor.task_base import Task

from celery.utils.log import get_task_logger
from celery import (
    current_app as app,
    signature
)


log = get_task_logger(__name__)


@app.task(bind=True, ignore_result=True, base=Task)
def send_to_slack(self, message, channel):
    self.slack.api_call('chat.postMessage',
                        channel=channel,
                        text=message)


@app.task(bind=True, rate_limit='20/m', ignore_result=True, base=Task)
def monitor_own_new_feed(self):
    update_post_flair = signature(
        'tor.role_moderator.tasks.update_post_flair'
    )

    subreddit_name = 'TranscribersOfReddit'
    # config = Config.subreddit(subreddit_name)

    r = self.http.get(f'https://www.reddit.com/r/{subreddit_name}/new.json')
    r.raise_for_status()
    feed = r.json()

    if feed['kind'].lower() != 'listing':  # pragma: no coverage
        raise 'Invalid payload for listing'

    for feed_item in feed['data']['children']:
        if feed_item['kind'].lower() != 't3':  # pragma: no coverage
            log.warning(f'Unsupported kind in /new feed with {repr(feed_item)}')
            continue

        if feed_item['data']['author'] not in OUR_BOTS and \
                not feed_item['data']['link_flair_text']:
            # If any other user posts (besides our bots), apply a "META" flair
            update_post_flair.delay(submission_id=feed_item['data']['id'],
                                    flair='META')

        # TODO: Any other maintenance tasks on our own posts?


@app.task(bind=True, ignore_result=True, base=Task)
def check_new_feeds(self):  # pragma: no coverage
    config = Config()

    for sub in config.subreddits:
        check_new_feed.delay(sub)


@app.task(bind=True, rate_limit='50/m', ignore_result=True, base=Task)
def check_new_feed(self, subreddit):
    # Using `signature` here so we don't have a recursive import loop
    post_to_tor = signature('tor.role_moderator.tasks.post_to_tor')

    config = Config.subreddit(subreddit)

    r = self.http.get(f'https://www.reddit.com/r/{subreddit}/new.json')
    r.raise_for_status()
    feed = r.json()

    if feed['kind'].lower() != 'listing':  # pragma: no coverage
        raise 'Invalid payload for listing'

    cross_posts = 0

    for feed_item in feed['data']['children']:
        log.debug(f'Processing post {repr(feed_item["data"]["title"])}')
        if feed_item['kind'].lower() != 't3':  # pragma: no coverage
            # Only allow t3 (submission) types
            log.warning(f'Unsupported kind in /new feed with {repr(feed_item)}')
            continue
        if feed_item['data']['is_self']:
            # Self-posts don't need to be transcribed. Duh!
            log.debug('Does not support self-posts')
            continue
        if feed_item['data']['locked'] or feed_item['data']['archived']:
            # No way to comment with a transcription if post is read-only
            log.debug('Does not support locked or archived posts')
            continue
        if feed_item['data']['author'] is None:
            # Author gone means deleted, and we don't want to cross-post then
            log.debug('Does not support deleted posts')
            continue
        if self.redis.sismember('post_ids', feed_item['data']['id']):
            # Post is already processed, but may not be completed
            log.debug('Skips already submitted posts')
            continue
        if not config.filters.score_allowed(feed_item['data']['score']):
            # Must meet subreddit-specific settings on score threshold
            log.debug('Skips low scoring posts')
            continue
        if not config.filters.url_allowed(feed_item['data']['domain']):
            # Must be on one of the whitelisted domains (if any given)
            log.debug('Skips posts for a domain that isn\'t whitelisted')
            continue

        post_to_tor.delay(sub=feed_item['data']['subreddit'],
                          title=feed_item['data']['title'],
                          link=feed_item['data']['permalink'],
                          media_link=feed_item['data']['url'],
                          post_id=feed_item['data']['id'],
                          domain=feed_item['data']['domain'])
        cross_posts += 1

    log.info(f'Found {cross_posts} posts for /r/{subreddit}')


@app.task(bind=True, ignore_result=True, base=Task)
def accept_code_of_conduct(self, username):
    send_to_slack = signature('tor.role_anyone.tasks.send_to_slack')

    self.redis.sadd('accepted_CoC', username)

    send_to_slack.delay(
        f'<https://www.reddit.com/u/{username}|/u/{username}> has just '
        f'accepted the CoC!',
        '#general'
    )


@app.task(bind=True, ignore_result=True, base=Task)
def unhandled_comment(self, comment_id, body):
    send_to_slack = signature('tor.role_anyone.tasks.send_to_slack')

    send_to_slack(
        f'**Unhandled comment reply** (https://redd.it/{comment_id})'
        f'\n\n'
        f'{body}',
        '#general'
    )


@app.task(bind=True, ignore_result=True, base=Task)
def bump_user_transcriptions(self, username: str, by: int):
    u = User(username, redis_conn=self.redis)
    count = u.get('transcriptions')
    count += by
    u.set('transcriptions', count)
    u.save()

    # TODO: Call out to reddit to set the flair


@app.task(bind=True, ignore_result=True, base=Task)
def test_system(self):  # pragma: no coverage
    import time
    import random

    log.info('starting task')
    time.sleep(random.choice(range(10)))
    log.info('done with task')
