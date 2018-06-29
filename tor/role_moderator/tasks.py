from tor_core import OUR_BOTS
from tor_core.config import Config
from tor.context import (
    InvalidState,
    find_transcription_comment_id,
    is_claimable_post,
    is_claimed_post_response,
    is_code_of_conduct,
    has_youtube_captions,
)
from tor.user_interaction import (
    format_bot_response as _,
    message_link,
    post_comment,
    responses as bot_msg,
)
from tor.task_base import Task, InvalidUser

from celery.utils.log import get_task_logger
from celery import current_app as app, signature
from praw.models import Comment

import re
import textwrap


log = get_task_logger(__name__)


MOD_SUPPORT_PHRASES = [
    re.compile("fuck", re.IGNORECASE),
    re.compile("unclaim", re.IGNORECASE),
    re.compile("undo", re.IGNORECASE),
    re.compile("(?:good|bad) bot", re.IGNORECASE),
]


@app.task(bind=True, ignore_result=True, base=Task)
def check_inbox(self):
    """
    Checks all unread messages in the inbox, routing the responses to other queues. This
    effectively transfers tasks from Reddit's inbox to our internal task queuing system,
    reducing the required API calls.
    """
    send_to_slack = signature("tor.role_anyone.tasks.send_to_slack")
    send_bot_message = signature("tor.role_moderator.tasks.send_bot_message")
    process_comment = signature("tor.role_moderator.tasks.process_comment")
    process_admin_command = signature("tor.role_moderator.tasks.process_admin_command")

    for item in reversed(list(self.reddit.inbox.unread(limit=None))):

        # NOTE: We compare the `kind` attribute due to testing issues with
        #   `isinstance()`. We can mock out the objects with MagicMock now and
        #   have fewer classes loaded in this context.

        if item.kind == "t1":  # Comment
            if "username mention" in item.subject.lower():
                log.info(f"Username mention by /u/{item.author.name}")
                send_bot_message.delay(
                    to=item.author.name,
                    subject="Username Call",
                    body=_(bot_msg["mention"]),
                )

            else:
                process_comment.delay(item.id)

        elif item.kind == "t4":  # Message
            # Very rarely we may actually get a message from Reddit admins, in
            # which case there will be no author attribute
            if item.author is None:
                log.info(f"Received message from the admins: {item.subject}")
                send_to_slack.delay(
                    f"*Incoming message without an author*\n\n"
                    f"**Subject:** {item.subject}\n\n"
                    f"{item.body}",
                    "#general",
                )

            elif item.subject and item.subject[0] == "!":
                process_admin_command.delay(
                    author=item.author.name,
                    subject=item.subject,
                    body=item.body,
                    message_id=item.id,
                )
            else:
                log.info(
                    f"Received unhandled message from /u/{item.author.name}. Subject: {repr(item.subject)}"
                )
                send_to_slack.delay(
                    f"Unhandled message by [/u/{item.author.name}](https://reddit.com/user/{item.author.name})\n\n"
                    f"**Subject:** {item.subject}\n\n"
                    f"{item.body}"
                    "#general"
                )

        else:  # pragma: no cover

            # There shouldn't be any other types than Message and Comment,
            # but on the off-chance there is, we'll log what it is here.
            send_to_slack.delay(
                f"Unhandled, unknown inbox item: {type(item).__name__}", "#botstuffs"
            )
            log.warning(f"Unhandled, unknown inbox item: {type(item).__name__}")

        item.mark_read()


@app.task(bind=True, ignore_result=True, base=Task)
def process_admin_command(self, author, subject, body, message_id):
    """
    This task is the basis for all other admin commands. It does not farm it out to
    another task per command, rather it runs it in the existing task.

    Steps:
    - Check for permissions
    - Retrieve associated function as a callable
    - Call said function with the commands (author, body, svc)
    - Send the response from the function as a reply back to the invoking message.
    """
    send_bot_message = signature("tor.role_moderator.tasks.send_bot_message")
    send_to_slack = signature("tor.role_anyone.tasks.send_to_slack")

    # It only makes sense to have this be scoped to /r/ToR
    config = Config.subreddit("TranscribersOfReddit")
    command_name = subject.lower()[1:]  # Lowercase and remove the initial '!'

    if not config.commands.allows(command_name).by_user(author):
        log.warning(f"DENIED: {author} is not allowed to call {command_name}")
        send_to_slack.delay(
            f":rotating_light::rotating_light: DENIED! :rotating_light::rotating_light:\n\n"
            f"{author} tried to `{command_name}` but was not permitted to do so",
            "#general",
        )
        return

    log.info(f"{author} called {command_name} with args {repr(body)}")

    func = config.commands.func(command_name)
    response = func(author=author, body=body, svc=self)

    log.debug(
        f"Responding to {command_name} with {repr(body)} -> " f"{repr(response)}."
    )

    send_bot_message.delay(body=_(response), message_id=message_id)


@app.task(bind=True, ignore_result=True, base=Task)
def update_post_flair(self, submission_id, flair):
    """
    Updates the flair of the original post to the pre-existing flair template id
    given the string value of the flair. If there is no pre-existing styling for
    that flair choice, task will error out with ``NotImplementedError``.

    EXAMPLE:
        ``flair`` is "unclaimed", sets the post to "Unclaimed" with pre-existing
        styling
    """
    post = self.reddit.submission(submission_id)

    for choice in post.flair.choices():
        if choice["flair_text"].lower() == flair.lower():
            # NOTE: This is hacky if we have multiple styles for the same flair.
            #   That said, we shouldn't rely on visual style if we're being
            #   truly accessible...
            post.flair.select(flair_template_id=choice["flair_template_id"])
            return

    raise NotImplementedError(f"Unknown flair, {repr(flair)}, for post")


@app.task(bind=True, ignore_result=True, base=Task)
def send_bot_message(
    self, body, message_id=None, to=None, subject="Just bot things..."
):
    """
    Sends a message as /u/TranscribersOfReddit

    If this is intended to be a reply to an existing message:
    - fill out the ``message_id`` param with a ref to the previous message

    If no previous context:
    - fill out the ``to`` param with the author's username
    - fill out the ``subject`` param with the subject of the message

    One of these _must_ be done.
    """
    sender = self.reddit.user.me().name
    if sender != "transcribersofreddit":
        raise InvalidUser(
            f"Attempting to send message as {sender} instead of the official ToR bot"
        )

    if message_id:
        self.reddit.message(message_id).reply(body)
    elif to:
        self.reddit.redditor(to).message(subject, body)
    else:
        raise NotImplementedError(
            "Must give either a value for ``message_id`` or ``to``"
        )


def process_mod_intervention(comment: Comment):
    """
    Triggers an alert in Slack with a link to the comment if there is something
    offensive or in need of moderator intervention
    """
    send_to_slack = signature("tor.role_anyone.tasks.send_to_slack")

    phrases = []
    for regex in MOD_SUPPORT_PHRASES:
        matches = regex.search(comment.body)
        if not matches:
            continue

        phrases.append(matches.group())

    if len(phrases) == 0:
        # Nothing offensive here, why did this function get triggered?
        return

    # Wrap each phrase in double-quotes (") and commas in between
    phrase = '"' + '", "'.join(phrases) + '"'

    title = "Mod Intervention Needed"
    message = f"Detected use of {phrase} <{comment.submission.shortlink}>"

    send_to_slack.delay(
        f":rotating_light::rotating_light: {title} :rotating_light::rotating_light:\n\n{message}",
        "#general",
    )


@app.task(bind=True, ignore_result=True, base=Task)
def process_comment(self, comment_id):
    """
    Processes a notification of comment being made, routing to other tasks as
    is deemed necessary
    """
    accept_code_of_conduct = signature("tor.role_anyone.tasks.accept_code_of_conduct")
    unhandled_comment = signature("tor.role_anyone.tasks.unhandled_comment")
    claim_post = signature("tor.role_moderator.tasks.claim_post")
    verify_post_complete = signature("tor.role_moderator.tasks.verify_post_complete")

    reply = self.reddit.comment(comment_id)

    if reply.author.name in OUR_BOTS:
        return

    body = reply.body.lower()

    # This should just be a filter that doesn't stop further processing
    process_mod_intervention(reply)

    if is_code_of_conduct(reply.parent()):
        if re.search(r"\bi accept\b", body):
            accept_code_of_conduct.delay(reply.author.name)
            claim_post.delay(reply.id, verify=False, first_claim=True)
        else:
            unhandled_comment.delay(comment_id=reply.id, body=reply.body)

    elif is_claimable_post(reply.parent()):
        if re.search(r"\bclaim\b", body):
            claim_post.delay(reply.id)
        else:
            unhandled_comment.delay(comment_id=reply.id, body=reply.body)

    elif is_claimed_post_response(reply.parent()):
        if re.search(r"\b(?:done|deno)\b", body):
            verify_post_complete.delay(comment_id=reply.id)
        elif re.search(r"(?=<^|\W)!override\b", body):
            # TODO: Handle `!override`
            pass
        else:
            unhandled_comment.delay(comment_id=reply.id, body=reply.body)


# TODO: Test support
@app.task(bind=True, ignore_result=True, base=Task)
def claim_post(self, comment_id, verify=True, first_claim=False):
    """
    Macro for a couple tasks:
      - Update flair: ``Unclaimed`` -> ``In Progress``
      - Post response: ``Hey, you have the post!``
    """
    update_post_flair = signature("tor.role_moderator.tasks.update_post_flair")

    comment = self.reddit.comment(comment_id)

    if verify and not self.redis.sismember("accepted_CoC", comment.author.name):
        raise InvalidState(
            f"Unable to claim a post without first accepting " f"the code of conduct"
        )

    if not is_claimable_post(comment.parent(), override=True):
        raise InvalidState(
            f"Unable to claim a post that is not claimable. "
            f"https://redd.it/{comment.id}"
        )

    update_post_flair.delay(comment.submission.id, "In Progress")
    if first_claim:
        # TODO: replace with first-timer response
        post_comment(repliable=comment, body=bot_msg["claim_success"])
    else:
        post_comment(repliable=comment, body=bot_msg["claim_success"])


# TODO: Test support
@app.task(bind=True, ignore_result=True, base=Task)
def verify_post_complete(self, comment_id):
    mark_post_complete = signature("tor.role_moderator.tasks.mark_post_complete")

    comment = self.reddit.comment(comment_id)

    if not comment.submission.author.name == "transcribersofreddit":
        raise InvalidState(
            f"Unable to mark post as done if it's not a "
            f"transcribable post. https://redd.it/{comment.id}"
        )

    if not self.redis.sismember("accepted_CoC", comment.author.name):
        raise InvalidState(
            f"Unable to complete post without first accepting " f"the code of conduct"
        )

    if not is_claimed_post_response(comment.parent(), override=True):
        raise InvalidState(
            f"Unable to claim a post that is not claimable. "
            f"https://redd.it/{comment.id}"
        )

    other_post_id = comment.submission.id_from_url(comment.submission.url)
    other_post = self.reddit.submission(other_post_id)

    transcription_id = find_transcription_comment_id(
        author=comment.author.name, post=other_post, http=self.http, log=log
    )
    if transcription_id:
        mark_post_complete.delay(comment.submission.id, "Completed!")
    else:
        post_comment(repliable=comment, body=bot_msg["no_transcript_found"])


# TODO: Test support
@app.task(bind=True, ignore_result=True, base=Task)
def mark_post_complete(self, comment_id):
    """
    This task exists separately so we may manually mark a post as complete via
    the `celery` command, or by `!override` comment
    """

    update_post_flair = signature("tor.role_moderator.tasks.update_post_flair")
    bump_user_transcriptions = signature(
        "tor.role_anyone.tasks.bump_user_transcriptions"
    )

    comment = self.reddit.comment(comment_id)

    bump_user_transcriptions.delay(username=comment.author.name, by=1)
    update_post_flair.delay(comment.submission.id, "Completed!")


# TODO: Test support
@app.task(bind=True, ignore_result=True, base=Task)
def post_to_tor(self, sub, title, link, domain, post_id, media_link=None):
    """
    Posts a transcription to the /r/ToR front page

    Params:
        sub - Subreddit name that this comes from
        title - The original title of the post from the other subreddit
        link - The link to the original post from the other subreddit
        domain - The domain of the original post's linked content
        media_link - The link to the media in need of transcription
    """
    if not media_link:
        log.warn(
            f"Attempting to post content with no media link. ({sub}: [{domain}] {repr(title)})"
        )
        return

    # If youtube transcript is found, skip posting it to /r/ToR
    if has_youtube_captions(media_link):
        log.info(f"Found youtube captions for {media_link}... skipped.")
        self.redis.sadd("complete_post_ids", post_id)
        self.redis.incr("total_posted", amount=1)
        self.redis.incr("total_new", amount=1)

        return

    update_post_flair = signature("tor.role_moderator.tasks.update_post_flair")

    config = Config.subreddit(sub)
    title = textwrap.shorten(title, width=250, placeholder="...")

    post_type = config.templates.url_type(domain)
    post_template = config.templates.content(domain)
    footer = config.templates.footer

    submission = self.reddit.subreddit("TranscribersOfReddit").submit(
        title=f'{sub} | {post_type.title()} | "{title}"', url=link
    )

    update_post_flair.delay(submission.id, "Unclaimed")

    # Add completed post to tracker
    self.redis.sadd("complete_post_ids", post_id)
    self.redis.incr("total_posted", amount=1)
    self.redis.incr("total_new", amount=1)

    # TODO: Queue a job for OCR to handle this comment
    reply = bot_msg["intro_comment"].format(
        post_type=post_type,
        formatting=post_template,
        footer=footer,
        message_url=message_link(subject="General Questions"),
    )
    post_comment(repliable=submission, body=reply)
