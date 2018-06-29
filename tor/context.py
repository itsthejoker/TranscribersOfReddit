from logging import Logger
from typing import Optional
import time

from praw.models import Comment, Submission
from requests import Session
import youtube

"""
These methods are used for detecting the current state of a post (e.g., claimed,
unclaimed, done) and the surrounding context based on the specific comment data
given.

This helps reduce the amount of data we _have_ to store in Redis.
"""


class InvalidState(Exception):
    pass


def is_code_of_conduct(comment: Comment) -> bool:
    if is_code_of_conduct_body(comment.body):
        return True

    return False


def is_code_of_conduct_body(text: str) -> bool:
    if "code of conduct" in text.lower():
        return True

    return False


def is_claimed_post_response(comment: Comment) -> bool:
    if is_claimed_post_flair(comment.submission.link_flair_text):
        return True

    return False


def is_claimed_post_flair(flair: str) -> bool:
    if "in progress" in flair.lower():
        return True

    return False


def find_transcription_comment_id(
    author: str, post: Submission, http: Session, log: Logger
) -> Optional[str]:
    """
    Search through the top-level comments for a submission for a comment by the
    user, then check if the comment has "the footer". Continue searching until
    both conditions are true, or there are no more top-level comments.

    If no top-level comments matched, perhaps it was removed as if it was spam
    and we need to verify another way. Perhaps by checking the recent post
    history of the given author. If it's there, we'll return the comment id as
    it appears there. Reddit never _really_ deletes stuff, only unlinks it
    from obvious places. (^_^)
    """

    # Search
    comment_id = find_transcription_id_from_top_comments(author, post, log)
    if comment_id:
        return comment_id

    # Search through user's post history to find transcription comment
    return find_transcription_id_from_post_history(
        author=author, post_url=post.shortlink, http=http, log=log
    )


def find_transcription_id_from_top_comments(
    author: str, post: Submission, log: Logger
) -> Optional[str]:
    post.comments.replace_more(limit=0)
    for comment in post.comments.list():
        if not comment.author.name == author:
            continue
        if not is_transcription(comment):
            continue

        log.debug(f"Found proof of u/{author}'s transcription for " f"{post.shortlink}")
        return comment.id

    return None


def find_transcription_id_from_post_history(
    author: str, post_url: str, http: Session, log: Logger
) -> Optional[str]:
    """
    Look through the user's recent post history for some comment on the
    submission's thread, seeing if any of _those_ have "the footer". Continue
    searching for 4 pages of the recent post history (retrieved as an anonymous
    user via HTTP request directly to Reddit) until found.

    Will return `None` if no comment id is found.
    """
    last_id = None
    for page in range(0, 3):  # go back 4 pages of user history
        log.debug(
            f"Checking page {page+1} of u/{author}'s post history for "
            f"proof of transcription for {post_url}"
        )

        if last_id:
            response = http.get(
                f"https://reddit.com/user/{author}.json", params={"before": last_id}
            )
        else:
            response = http.get(f"https://reddit.com/user/{author}.json")
        response.raise_for_status()
        posts = response.json()

        for comment in posts["data"]["children"]:
            last_id = comment["data"]["id"]
            if not is_transcription_body(comment["data"]["body"]):
                continue
            if comment["data"]["link_id"][3:] not in post_url:
                # Skip if not the transcription we're evaluating right now
                continue

            log.debug(f"Found proof of u/{author}'s transcription for " f"{post_url}")
            return comment["data"]["id"]

        log.debug(f"No proof found on page {page+1} for u/{author}")
        time.sleep(3)

    return None


def is_claimable_post(comment: Comment, override=False) -> bool:
    # Need to accept the CoC before claiming
    if not override and is_code_of_conduct(comment):
        return False

    if "unclaimed" in comment.submission.link_flair_text.lower():
        return True

    return False


def is_transcription(comment: Comment) -> bool:
    if is_transcription_body(comment.body):
        return True

    return False


def is_transcription_body(text: str) -> bool:
    if "^^I'm&#32;a&#32;human&#32;volunteer&#32;" in text.lower():
        return True

    return False


def has_youtube_captions(link: str) -> bool:
    if not link:
        return False
    if "youtu" not in link:
        return False

    video = youtube.Video(link)

    if not video.captions:
        return False

    # Any other criteria we want to filter on from the video metadata?

    return True
