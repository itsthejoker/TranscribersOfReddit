from urllib.parse import quote as uri_escape
import textwrap

from tor import __version__

from collections import deque

faq_link = "https://www.reddit.com/r/TranscribersOfReddit/wiki/index"
source_link = "https://github.com/GrafeasGroup/tor_worker"

responses = {
    "mention": (
        "Hi there! Thanks for pinging me!\n\n"
        "Due to some changes with how Reddit and individual subreddits handle "
        "bots, I can't be summoned directly to your comment anymore. If "
        "there's something that you would like assistance with, please post "
        "a link in /r/DescriptionPlease, and one of our lovely volunteers will "
        "be along shortly.\n\nThanks for using our services! We hope we can "
        "make your day a little bit better :)\n\nCheers,\n\n"
        "The Mods of /r/TranscribersOfReddit"
    ),
    "intro_comment": (
        "If you would like to claim this post, please respond to this comment "
        "with the word `claiming` or `claim` in your response. I will "
        "automatically update the flair so that only one person is worker on a "
        "post at any given time."
        "\n\n"
        "When you're done, please comment again with `done`. Your flair will "
        "be updated to reflect the number of posts you've transcribed and "
        "they will be marked as completed."
        "\n\n"
        "Post type: {post_type}. Please use the following formatting:"
        "\n\n---\n\n"
        "{formatting}"
        "\n\n---\n\n"
        "## Footer"
        "\n\n"
        "When you're done, please put the following footer at the **bottom** "
        "of your post:"
        "\n\n---\n\n"
        "{footer}"
        "\n\n---\n\n"
        "If you have any questions, feel free to [message the mods!]("
        "{message_url})"
    ),
    "claim_success": (
        "The post is yours! Best of luck and thanks for helping!"
        "\n\n"
        'Please respond with "done" when complete so we can check this one off '
        "the list!"
    ),
}


def message_link(to="/r/TranscribersOfReddit", subject="Bot Questions", message=""):
    return (
        "https://www.reddit.com/message/compose?"
        "to={to}&subject={sub}&message={msg}".format(
            to=uri_escape(to), sub=uri_escape(subject), msg=uri_escape(message)
        )
    )


def format_bot_response(message):
    """
    Formats the response message the bot sends out to users via comment or
    message. Often aliased as `_()`
    """
    message_the_mods_link = message_link(
        to="/r/TranscribersOfReddit", subject="Bot Questions"
    )

    footer = " | ".join(
        [
            f"v{__version__}",
            f"This message was posted by a bot.",
            f"[FAQ]({faq_link})",
            f"[Source]({source_link})",
            f"Questions? [Message the mods!]({message_the_mods_link})",
        ]
    )
    return f"{message}\n\n---\n\n{footer}"


def post_comment(repliable, body):
    """
    Posts paginated replies to a comment, chaining each page as a reply to the
    previous comment "page".

    :param repliable: Some object that responds to ``.reply()`` with str input
                      and repliable object output.
    :param body: String value for the body of a comment to be made
    :return: The last page of the comments that were posted.
    """
    reddit_max_length = 9900  # 10k chars with 100 chars for margin of error

    # We calculate max length of each page as max reddit-imposed length minus
    # the bot footer on each "page". But it has to be greater than zero
    # characters wide.
    max_length = max(reddit_max_length - len(format_bot_response("")), 1)

    # Split into pages of comments
    body_parts = deque(CommentWrapper(max_chars=max_length).wrap(body))

    # Now that we've split it up into parts, we'll leave one comment per page,
    # replying to the last comment for each page.
    last = repliable
    while len(body_parts) > 0:
        part = body_parts.popleft()
        last = last.reply(format_bot_response(part))

    # The last page is what we return in case we need to reply treating all
    # pages as if they are one comment.
    return last


class CommentWrapper(object):
    """
    Splits comments that are too long for later pagination. Assumes comments are
    in markdown syntax and headings use the ``# some header`` syntax instead of
    the underline approach.

        >>> wrapper = CommentWrapper()
        >>> pages = wrapper.wrap(some_long_text)
        >>> for page in pages:
        >>>     print(page + '\n\nEOF\n\n')
    """

    def __init__(self, max_chars=9950):
        self.max_chars = max_chars

    def wrap(self, blob):
        """
        Splits off ``blob`` into pages, delimited by the ``max_chars`` setting
        on initialization.

        :param blob: string data that is the comment to be paginated
        :return: list of each comment "page"
        """
        self._pages = []
        self._page = ""
        placeholder = " \\[...\\]"

        for line in blob.splitlines():
            while True:
                if len(self._page + line) <= self.max_chars:
                    # If we can add the entire line without going over character
                    # limit, do it and move on.
                    self._page += line
                    break  # while
                elif len(line) > self.max_chars:
                    chars_left = self.max_chars - len(self._page)

                    # We're going to use textwrap so we don't split in the
                    # middle of words. We'll wrap to the max character length
                    # that we safely can, then treat the remainder as a line for
                    # the next iteration in the while-loop.

                    assert chars_left > 0, f"{repr(line)} is failure"

                    # TODO: modify settings so we don't strip spaces or anything
                    wrapped = textwrap.wrap(
                        line, width=chars_left, placeholder=placeholder
                    )
                    self._page += wrapped[0]
                    self._new_page()

                    line = line[len(wrapped[0]) :]
                    continue  # while
                else:
                    # For simplicity, we're going to start a new page for
                    # any grouping. Probably will change that to be specific
                    # groupings (headers, blockquotes, etc.) later.
                    self._new_page()
                    continue  # while

        return list(self._pages)

    def _new_page(self):
        self._pages.append(self._page)
        self._page = ""
