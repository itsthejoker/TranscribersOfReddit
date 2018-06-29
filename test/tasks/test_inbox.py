from tor.role_moderator.tasks import check_inbox

from ..celery import (
    signature,
    reset_signatures,
    # assert_no_tasks_called,
    assert_only_tasks_called,
)
from ..generators import generate_comment, generate_message, generate_inbox

import unittest
from unittest.mock import patch, ANY


class ProcessInboxMessagesTest(unittest.TestCase):
    """
    Tests the routing of certain inbox message types
    """

    def setUp(self):
        reset_signatures()

    @patch("tor.role_moderator.tasks.signature", side_effect=signature)
    @patch("tor.role_moderator.tasks.check_inbox.reddit")
    def test_comment(self, mock_reddit, mock_signature):
        item = generate_comment()
        mock_reddit.inbox = generate_inbox()
        mock_reddit.inbox.unread.return_value = [item]

        check_inbox()

        signature("tor.role_moderator.tasks.process_comment").delay.assert_called_once()

        assert_only_tasks_called("tor.role_moderator.tasks.process_comment")

        item.mark_read.assert_called_once()

    @patch("tor.role_moderator.tasks.signature", side_effect=signature)
    @patch("tor.role_moderator.tasks.check_inbox.reddit")
    def test_mention(self, mock_reddit, mock_signature):
        item = generate_comment(
            subject="username mention",
            body="Just letting you know, /u/me, it's pretty cool.",
        )

        mock_reddit.inbox = generate_inbox()
        mock_reddit.inbox.unread.return_value = [item]

        check_inbox()

        signature(
            "tor.role_moderator.tasks.send_bot_message"
        ).delay.assert_called_once()

        assert_only_tasks_called("tor.role_moderator.tasks.send_bot_message")

        item.mark_read.assert_called_once()

    @patch("tor.role_moderator.tasks.signature", side_effect=signature)
    @patch("tor.role_moderator.tasks.check_inbox.reddit")
    def test_message(self, mock_reddit, mock_signature):
        item = generate_message(
            subject="Yo! I like this subreddit",
            body="Just letting you know, it's pretty cool.",
        )

        mock_reddit.inbox = generate_inbox()
        mock_reddit.inbox.unread.return_value = [item]

        check_inbox()

        signature("tor.role_anyone.tasks.send_to_slack").delay.assert_called_once()

        assert_only_tasks_called("tor.role_anyone.tasks.send_to_slack")
        item.mark_read.assert_called_once()

    @patch("tor.role_moderator.tasks.signature", side_effect=signature)
    @patch("tor.role_moderator.tasks.check_inbox.reddit")
    def test_mod_message(self, mock_reddit, mock_signature):
        item = generate_message(
            author=None, subject="Important announcement!", body="Hehe, just kidding"
        )

        mock_reddit.inbox = generate_inbox()
        mock_reddit.inbox.unread.return_value = [item]

        check_inbox()

        signature("tor.role_anyone.tasks.send_to_slack").delay.assert_called_once_with(
            ANY, "#general"
        )

        assert_only_tasks_called("tor.role_anyone.tasks.send_to_slack")
        item.mark_read.assert_called_once()

    @patch("tor.role_moderator.tasks.signature", side_effect=signature)
    @patch("tor.role_moderator.tasks.check_inbox.reddit")
    def test_admin_command(self, mock_reddit, mock_signature):
        item = generate_message(subject="!ignoreplebians")

        mock_reddit.inbox = generate_inbox()
        mock_reddit.inbox.unread.return_value = [item]

        check_inbox()

        signature(
            "tor.role_moderator.tasks.process_admin_command"
        ).delay.assert_called_once()

        assert_only_tasks_called("tor.role_moderator.tasks.process_admin_command")
        item.mark_read.assert_called_once()
