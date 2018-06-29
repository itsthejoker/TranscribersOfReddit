from tor.role_moderator.tasks import process_admin_command

from ..celery import (
    signature,
    reset_signatures,
    # assert_no_tasks_called,
    assert_only_tasks_called,
)
from ..generators import generate_message

import unittest
from unittest.mock import patch, MagicMock


class ProcessAdminCommandTest(unittest.TestCase):
    def setUp(self):
        reset_signatures()
        self.msg = generate_message()

    @patch("tor.role_moderator.tasks.Config")
    @patch("tor.role_moderator.tasks.signature", side_effect=signature)
    def test_import_tasks(self, mock_signature, mock_config):
        mock_config.subreddit = MagicMock(
            name="Config.subreddit", return_value=mock_config
        )

        process_admin_command(
            subject="!ping", author="me", body="derp", message_id=self.msg.id
        )
        assert_only_tasks_called("tor.role_moderator.tasks.send_bot_message")
        mock_config.commands.func.assert_called_once_with("ping")

    @patch("tor.role_moderator.tasks.Config")
    @patch("tor.role_moderator.tasks.signature", side_effect=signature)
    def test_routing_blacklist(self, mock_signature, mock_config):
        mock_config.subreddit = MagicMock(
            name="Config.subreddit", return_value=mock_config
        )

        process_admin_command(
            subject="!blacklist", author="me", body="you", message_id=self.msg.id
        )

        assert_only_tasks_called("tor.role_moderator.tasks.send_bot_message")
        mock_config.commands.func.assert_called_once_with("blacklist")

    @patch("tor.role_moderator.tasks.Config")
    @patch("tor.role_moderator.tasks.signature", side_effect=signature)
    def test_not_allowed_to_run_command(self, mock_signature, mock_config):
        mock_config.subreddit = MagicMock(
            name="Config.subreddit", return_value=mock_config
        )
        mock_auth = MagicMock(name="command permission")
        mock_config.commands.allows.return_value = mock_auth
        mock_auth.by_user.return_value = False

        process_admin_command(
            subject="!blacklist", author="bad_actor", body="me", message_id=self.msg.id
        )

        assert_only_tasks_called("tor.role_anyone.tasks.send_to_slack")
        mock_config.commands.func.assert_not_called()
