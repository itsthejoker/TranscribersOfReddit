import pytest
# from tor.role_moderator.tasks import (
#     verify_post_complete,
# )

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
from unittest.mock import (
    patch,
    MagicMock,
)

import requests


@pytest.mark.skip(reason='Needs to be implemented')
class VerifyTranscriptionTest(unittest.TestCase):

    def setUp(self):
        reset_signatures()
        submission = generate_submission(flair='In Progress')
        parent = generate_comment(
            body='The post is yours!',
            author='transcribersofreddit',
            submission=submission,
        )
        self.comment = parent.reply('done')

        transcribable_post = generate_submission(flair='')
        self.transcription = transcribable_post.reply(
            ''
        )

        submission.link = transcribable_post

    @patch('tor.role_moderator.tasks.signature', side_effect=signature)
    @patch('tor.role_moderator.tasks.verify_post_complete.http',
           spec=requests.Session)
    @patch('tor.role_moderator.tasks.verify_post_complete.reddit')
    def test_verify_complete_transcription(self, mock_reddit, mock_http,
                                           mock_signature):
        mock_reddit.comment = MagicMock(name='comment',
                                        return_value=self.comment)
