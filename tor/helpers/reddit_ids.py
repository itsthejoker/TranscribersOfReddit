from praw.models import Submission
from tor.core.config import Config


def create_post_obj(
        cfg: Config,
        post_id: str=None,
        post_url: [str, None]=None,
        tor_url: [str, None]=None,
) -> [None, bool]:
    result = cfg.api.post.create(
        post_id=post_id,
        post_url=post_url,
        tor_url=tor_url
    )



def is_valid(post_id: str, cfg: Config) -> bool:
    """
    Returns True or False based on whether or not we already have this post
    on record. If the get call to the API returns data, then this is a post
    that we've already processed and thus shouldn't touch again. If no data
    is returned, then this is something that we can work on and so return
    False.

    :param post_id: str. The reddit ID of the post in question.
    :param cfg: The global config object.
    """
    result = cfg.api.post.get(post_id=post_id)
    return True if result is None else False


def is_removed(post: Submission, full_check: bool = False) -> bool:
    """
    Reddit does not allow non-mods to tell whether or not a post has been
    removed, which understandably makes it a little difficult to figure out
    whether or not we should remove a post automatically. HOWEVER, as with
    pretty much everything else that Reddit does, they left enough detritus
    that we guess with a relatively high degree of accuracy.

    We can use a combination of checking to see if something is gildable or
    crosspostable (and its current content, if a selfpost) to identify its
    current state:

    flag                    can_gild    is_crosspostable    selftext
    removed                 Y           N                   ""
    dead user               N           Y                   ""
    removed + dead user     N           N                   ""
    deleted post            N           N                   [deleted]

    More information (and where this table is from): https://redd.it/7hfnew

    Because we don't necessarily need to remove a post in certain situations
    (e.g. the user account has been deleted), we can simplify the check. By
    setting `full_check`, we can return True for any issue.
    :param post: The post that we are attempting to investigate.
    :return: True is the post looks like it has been removed, False otherwise.
    """

    if full_check:
        return False if post.is_crosspostable and post.can_gild else True
    else:
        return not post.is_crosspostable
