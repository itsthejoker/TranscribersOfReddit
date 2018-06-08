import youtube
from praw.models import Comment

"""
These methods are used for detecting the current state of a post (e.g., claimed,
unclaimed, done) and the surrounding context based on the specific comment data
given.

This helps reduce the amount of data we _have_ to store in Redis.
"""


class InvalidState(Exception):
    pass


def is_code_of_conduct(comment: Comment):
    if 'code of conduct' in comment.body.lower():
        return True

    return False


def is_claimed_post_response(comment: Comment):
    if 'in progress' in comment.submission.link_flair_text.lower():
        return True

    return False


def is_claimable_post(comment: Comment, override=False):
    # Need to accept the CoC before claiming
    if not override and is_code_of_conduct(comment):
        return False

    if 'unclaimed' in comment.submission.link_flair_text.lower():
        return True

    return False


def is_transcription(comment: Comment):
    if "^^I'm&#32;a&#32;human&#32;volunteer&#32;" in comment.body.lower():
        return True

    return False


def has_youtube_captions(link):
    if not link:
        return False
    if 'youtu' not in link:
        return False

    video = youtube.Video(link)

    if not video.captions:
        return False

    # Any other criteria we want to filter on from the video metadata?

    return True
