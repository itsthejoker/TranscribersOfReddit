import pytest
import random

from tor.role_moderator.tasks import (
    persist_transcription_count,
    # verify_post_complete,
)

from tor.role_anyone.tasks import bump_user_transcriptions

from ..celery import (
    signature,
    reset_signatures,
    # assert_not_tasks_called,
    # assert_only_tasks_called,
)
from ..generators import (
    # generate_redditor,
    generate_comment,
    generate_submission,
)

import unittest
from unittest.mock import patch, MagicMock, ANY

import requests


@pytest.mark.skip(reason="Needs to be implemented")
class VerifyTranscriptionTest(unittest.TestCase):
    def setUp(self):
        reset_signatures()
        submission = generate_submission(flair="In Progress")
        parent = generate_comment(
            body="The post is yours!",
            author="transcribersofreddit",
            submission=submission,
        )
        self.comment = parent.reply("done")

        transcribable_post = generate_submission(flair="")
        self.transcription = transcribable_post.reply("")

        submission.link = transcribable_post

    @patch("tor.role_moderator.tasks.signature", side_effect=signature)
    @patch("tor.role_moderator.tasks.verify_post_complete.http", spec=requests.Session)
    @patch("tor.role_moderator.tasks.verify_post_complete.reddit")
    def test_verify_complete_transcription(
        self, mock_reddit, mock_http, mock_signature
    ):
        mock_reddit.comment = MagicMock(name="comment", return_value=self.comment)


class TranscriptionBumpTest(unittest.TestCase):
    @patch("tor.role_anyone.tasks.User")
    @patch("tor.role_anyone.tasks.signature", side_effect=signature)
    @patch("tor.role_anyone.tasks.bump_user_transcriptions.redis")
    def test_bump_transcription_count(self, mock_redis, mock_signature, mock_user):
        initial = random.choice(range(80))
        bump = random.choice(range(10))
        u = MagicMock()
        mock_user.return_value = u

        u.get.return_value = initial

        bump_user_transcriptions("abc", bump)
        mock_user.assert_called_with("abc", redis_conn=mock_redis)
        u.get.assert_called_with("transcriptions")
        u.set.assert_called_with("transcriptions", initial + bump)

        signature(
            "tor.role_moderator.tasks.persist_transcription_count"
        ).delay.assert_called()

    @patch("tor.role_moderator.tasks.User")
    @patch("tor.role_moderator.tasks.signature", side_effect=signature)
    @patch("tor.role_moderator.tasks.persist_transcription_count.redis")
    @patch("tor.role_moderator.tasks.persist_transcription_count.reddit")
    def test_persisting_transcription(
        self, mock_reddit, mock_redis, mock_signature, mock_user
    ):
        transcription_count = random.choice(range(90))
        _missing = object()

        def user_hash_get(key, default_value=_missing):
            return {"transcriptions": transcription_count}.get(key, default_value)

        mock_reddit.subreddit.return_value = mock_reddit
        mock_reddit.flair = MagicMock(name="reddit.flair")

        data = {}
        mock_reddit.flair.set.side_effect = lambda *args, **kwargs: data.update(kwargs)

        u = MagicMock(name="user")
        mock_user.return_value = u
        u.get.side_effect = user_hash_get

        persist_transcription_count("abc")

        u.get.assert_any_call("transcriptions", ANY)
        u.get.assert_any_call("flair_title", ANY)
        mock_reddit.flair.set.assert_called_once_with(
            redditor="abc", text=ANY, css_class=ANY
        )

        assert "text" in data.keys()
        assert f"{transcription_count} Γ - Beta Tester" in data["text"]
