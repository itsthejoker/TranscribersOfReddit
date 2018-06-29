import pytest

from tor.admin_commands import (
    process_blacklist,
    ping,
    update_and_restart,
    reload_config,
    noop,
    undefined_operation,
)

import unittest
from unittest.mock import patch, MagicMock


class BlacklistTest(unittest.TestCase):
    def setUp(self):
        self.svc = MagicMock(name="Resource access point")
        self.svc.http = MagicMock(name="HTTP client")
        self.svc.redis = MagicMock(name="Redis client")

        self.http_response = MagicMock(name="HTTP response")
        self.svc.http.head.return_value = self.http_response
        self.svc.http.get.return_value = self.http_response

        # Here are the "happy path" responses:
        self.http_response.status_code = 200  # user actually exists
        self.svc.redis.sadd.return_value = 1  # not in the Redis blacklist

    @patch("tor.admin_commands.Config")
    def test_mod_targetting_other_mod(self, mock_config):
        mock_config.subreddit.return_value = mock_config
        mock_config.globals.is_moderator.return_value = True

        out = process_blacklist(author="tor_mod", arg="tor_mod2", svc=self.svc)

        assert (
            " 1 failed" in out and " 0 succeeded" in out
        ), "Mods should not be able to blacklist other mods"

    @patch("tor.admin_commands.Config")
    def test_mod_targetting_nonexistent_user(self, mock_config):
        mock_config.subreddit.return_value = mock_config
        mock_config.globals.is_moderator.return_value = False
        self.http_response.status_code = 404

        out = process_blacklist(author="tor_mod", arg="not_a_user", svc=self.svc)

        assert (
            " 1 failed" in out and " 0 succeeded" in out
        ), "Mods cannot blacklist users that do not exist"

    @patch("tor.admin_commands.Config")
    def test_mod_targetting_blacklisted_user(self, mock_config):
        mock_config.subreddit.return_value = mock_config
        mock_config.globals.is_moderator.return_value = False
        self.svc.redis.sadd.return_value = 0

        out = process_blacklist(author="tor_mod", arg="blacklisted_user", svc=self.svc)

        assert (
            " 1 failed" in out and " 0 succeeded" in out
        ), "Mods cannot re-blacklist users that are already blacklisted"

    @patch("tor.admin_commands.Config")
    def test_mod_targetting_random_user(self, mock_config):
        mock_config.subreddit.return_value = mock_config
        mock_config.globals.is_moderator.return_value = False

        out = process_blacklist(author="tor_mod", arg="random_user", svc=self.svc)

        assert (
            " 0 failed" in out and " 1 succeeded" in out
        ), "Mods should be able to blacklist some users"


class PingTest(unittest.TestCase):
    def setUp(self):
        self.svc = MagicMock(name="Resource access point")

    def test_ping(self):
        out = ping(author="me", arg="Does it matter?", svc=self.svc)

        assert out == "Pong!"


class NoopTest(unittest.TestCase):
    def setUp(self):
        self.svc = MagicMock(name="Resource access point")

    def test_update_and_restart(self):
        out = update_and_restart(author="me", arg="Does it matter?", svc=self.svc)

        assert out == "Nothing to be done."

    def test_reload_config(self):
        out = reload_config(author="me", arg="Does it matter?", svc=self.svc)

        assert out == "Nothing to be done."

    def test_noop(self):
        out = noop(author="me", arg="Does it matter?", svc=self.svc)

        assert out == "Nothing to be done."


class DefaultAdminCommandTest(unittest.TestCase):
    def setUp(self):
        self.svc = MagicMock(name="Resource access point")

    def test_update_and_restart(self):
        with pytest.raises(NotImplementedError, message="Undefined operation"):
            undefined_operation(author="me", arg="Does it matter?", svc=self.svc)
