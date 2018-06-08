import pytest

from tor.role_moderator.tasks import send_bot_message
from tor.task_base import InvalidUser

from ..generators import (
    generate_redditor,
    generate_message,
)

import unittest
from unittest.mock import patch, MagicMock

import praw.models


class SendBotMessageTest(unittest.TestCase):
    """
    Tests for the ``send_bot_message`` task
    """

    @patch('tor.role_moderator.tasks.send_bot_message.reddit')
    def test_reply_message(self, mock_reddit):
        user = generate_redditor(username='transcribersofreddit')
        msg = generate_message()

        mock_reddit.user = MagicMock(spec=praw.models.User)
        mock_reddit.user.me = MagicMock(return_value=user)

        mock_reddit.message = MagicMock(return_value=msg)

        send_bot_message(message_id=msg.id,
                         body="It's time we met face-to-face")

        mock_reddit.user.me.assert_called_once()
        mock_reddit.message.assert_any_call(msg.id)
        msg.reply.assert_called_once_with("It's time we met face-to-face")

    @patch('tor.role_moderator.tasks.send_bot_message.reddit')
    def test_redditor_recipient(self, mock_reddit):
        user = generate_redditor(username='transcribersofreddit')
        msg = generate_message()

        recipient = generate_redditor(username='me')
        mock_reddit.redditor = MagicMock(return_value=recipient)

        mock_reddit.user = MagicMock(spec=praw.models.User)
        mock_reddit.user.me = MagicMock(return_value=user)

        mock_reddit.message = MagicMock(return_value=msg)

        send_bot_message(
            to=recipient.name,
            subject='Cryptic stuff happening...',
            body="It's time we met face-to-face"
        )

        mock_reddit.user.me.assert_called_once()
        mock_reddit.message.assert_not_called()
        msg.reply.assert_not_called()
        mock_reddit.redditor.assert_called_once()
        recipient.message.assert_called_once_with(
            'Cryptic stuff happening...',
            "It's time we met face-to-face"
        )

    @patch('tor.role_moderator.tasks.send_bot_message.reddit')
    def test_no_input(self, mock_reddit):
        user = generate_redditor(username='transcribersofreddit')

        mock_reddit.user = MagicMock(spec=praw.models.User)
        mock_reddit.user.me = MagicMock(return_value=user)

        with pytest.raises(NotImplementedError):
            send_bot_message('')

        mock_reddit.user.me.assert_called_once()

    @patch('tor.role_moderator.tasks.send_bot_message.reddit')
    def test_bad_task_runner(self, mock_reddit):
        user = generate_redditor(username='someotheruser')

        recipient = generate_redditor(username='me')

        mock_reddit.user = MagicMock(spec=praw.models.User)
        mock_reddit.user.me = MagicMock(return_value=user)
        mock_reddit.redditor = MagicMock(return_value=recipient)

        with pytest.raises(InvalidUser):
            send_bot_message(
                to='me',
                subject='Cryptic stuff happening...',
                body="It's time we met face-to-face"
            )

        mock_reddit.user.me.assert_called_once()
