from typing import Dict, Any

import base64
import random
import uuid

from unittest.mock import MagicMock

import loremipsum
from urllib.parse import urlparse
import praw.models


_missing = object()
users: Dict[str, Any] = {}


def generate_reddit_id():
    """
    Generates a random, reddit-compliant id. Note that it is picked at
    random and might collide with other real or generated reddit ids.
    """
    out = base64.b32encode(uuid.uuid4().bytes).decode().replace("=", "")
    return "".join(random.choices(out, k=6)).lower()


def generate_post_feed_item(
    link=None,
    subreddit="TranscribersOfReddit",
    selftext="",
    author=_missing,
    flair=_missing,
    locked=False,
    archived=False,
    score=1234,
    id_=_missing,
):
    if id_ is _missing:
        ident = generate_reddit_id()
    else:
        ident = id_
    if flair is _missing:
        flair = "Unclaimed"
    if not flair:
        flair = ""

    if author is _missing:
        author = "me"

    base = {
        "kind": "t3",
        "data": {
            "is_self": True,
            "locked": locked,
            "archived": archived,
            "author": author,
            "id": ident,
            "score": score,
            "selftext": selftext,
            "selftext_html": None,
            "domain": f"self.{subreddit}",
            "title": "Something evil this way comes",
            "permalink": f"/r/{subreddit}/comments/{ident}/"
            "something_evil_this_way_comes/",
            "url": None,
            "subreddit": subreddit,
            "link_flair_text": flair,
        },
    }

    if not selftext:
        selftext = "Some html-rendered selftext here."

    if link:
        base["data"]["is_self"] = False
        base["data"]["url"] = link
        base["data"]["domain"] = urlparse(link).hostname
        base["data"]["selftext"] = ""
        base["data"]["selftext_html"] = None
    else:
        base["data"]["selftext"] = selftext
        base["data"][
            "selftext_html"
        ] = "&lt;!-- SC_OFF --&gt;&lt;p&gt;SOME HTML-RENDERED SELFTEXT HERE&lt;/p&gt;&lt;!-- SC_ON --&gt;"

    return base


def generate_subreddit(name="subreddit", submission=None):
    sub = MagicMock(name=name, spec=praw.models.Subreddit)
    sub.kind = "t5"
    sub.id = generate_reddit_id()

    def submit_post(
        title,
        selftext=None,
        url=None,
        flair_id=None,
        flair_text=None,
        resubmit=True,
        send_replies=True,
    ):
        out = submission if submission else generate_submission()
        out.title = title

        return out

    sub.submit.side_effect = submit_post

    return sub


def generate_submission(
    name="post", author=_missing, reply=None, flair=_missing, id_=None
):
    """
    Factory for creating a new Submission mock object.
    """
    sub = MagicMock(name=name, spec=praw.models.Submission)
    sub.kind = "t3"
    if author is _missing:
        author = generate_redditor().name
    sub.author = generate_redditor(username=author)
    if not id_:
        id_ = generate_reddit_id()
    sub.id = id_
    sub.shortlink = f"http://redd.it/{sub.id}"

    if flair is _missing:
        flair = "Unclaimed"
    sub.link_flair_text = flair

    sub.title = " ".join(
        random.choices(loremipsum.Generator().words, k=random.choice(range(1, 5)))
    )

    sub._comments = list()

    sub.comments = MagicMock(name="post comments")

    def list_comments(*args, **kwargs):
        return list(sub._comments)

    def make_comment(body):
        out = reply if reply else generate_comment(submission=sub)
        out.parent.return_value = sub
        out.submission = sub
        out.body = body

        sub._comments.append(out)

        return out

    def flair_choices(*args, **kwargs):
        template = {
            "flair_text": "Foo",
            "flair_template_id": "680f43b8-1fec-11e3-80d1-12313b0b80bc",
            "flair_css_class": "",
            "flair_text_editable": False,
            "flair_position": "left",
        }
        return [
            {**template, **{"flair_text": "Unclaimed", "flair_template_id": "1"}},
            {**template, **{"flair_text": "In Progress", "flair_template_id": "2"}},
            {**template, **{"flair_text": "Completed", "flair_template_id": "3"}},
            {**template, **{"flair_text": "Meta", "flair_template_id": "4"}},
        ]

    sub.comments = MagicMock(name="submission comments")
    sub.comments.list.side_effect = list_comments

    sub.reply.side_effect = make_comment
    sub.mark_read = MagicMock(side_effect=None)

    sub.flair = MagicMock(spec=praw.models.reddit.submission.SubmissionFlair)
    sub.flair.choices.side_effect = flair_choices
    sub.flair.select.return_value = None

    return sub


def generate_comment(
    name="comment",
    submission=None,
    reply=None,
    parent=None,
    author=_missing,
    body="",
    subject="comment reply",
):
    comment = MagicMock(name=name, spec=praw.models.Comment)
    comment.kind = "t1"
    if author is _missing:
        author = generate_redditor().name
    comment.author = generate_redditor(username=author)
    comment.subject = subject
    if not submission:
        submission = generate_submission()
    comment.submission = submission
    comment.id = generate_reddit_id()
    comment.body = body
    if not parent:
        parent = submission
    comment.parent = MagicMock(return_value=parent)

    def make_comment(cmnt_body):
        if reply:
            out = reply
        else:
            out = generate_comment(name="reply", parent=comment, submission=submission)
        out.body = cmnt_body
        return out

    comment.reply = MagicMock(side_effect=make_comment)

    comment.mark_as_read = MagicMock(side_effect=None, return_value=None)

    if parent == submission:
        parent._comments.append(comment)

    return comment


def generate_redditor(name="user", username="me"):
    if users.get(username):
        return users[username]

    redditor = MagicMock(spec=praw.models.Redditor)
    redditor.name = username
    redditor.id = generate_reddit_id()
    users[username] = redditor

    return redditor


def generate_message(name="message", author=_missing, subject="", body=""):
    msg = MagicMock(name=name, spec=praw.models.Message)
    msg.kind = "t4"
    if author is _missing:
        author = generate_redditor().name
    if author is None:
        msg.author = None
    else:
        msg.author = generate_redditor(username=author)
    msg.subject = subject
    msg.body = body
    msg.id = generate_reddit_id()

    msg.mark_as_read = MagicMock(side_effect=None, return_value=None)
    msg.reply = MagicMock(side_effect=None, return_value=None)

    return msg


def generate_inbox(name="reddit.inbox", seed_data=False):
    box = MagicMock(name=name, spec=praw.models.Inbox)

    if seed_data:
        msgs = [
            generate_comment(),
            generate_comment(name="hail"),
            generate_message(),
            generate_message(name="mod_message", author=None),
        ]
        random.shuffle(msgs)
    else:
        msgs = []

    box.unread = MagicMock(side_effect=None, return_value=msgs)

    return box
