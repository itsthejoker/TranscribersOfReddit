import pytest

from tor.role_moderator.tasks import update_post_flair

from ..generators import generate_submission

import unittest
from unittest.mock import patch, MagicMock


class UpdatePostFlairTest(unittest.TestCase):
    @patch("tor.role_moderator.tasks.update_post_flair.reddit")
    def test_available_flair(self, mock_reddit):
        post = generate_submission()
        mock_reddit.submission = MagicMock(return_value=post)

        update_post_flair(submission_id="abc123", flair="Unclaimed")

        mock_reddit.submission.assert_called_once()
        post.flair.choices.assert_called_once_with()
        post.flair.select.assert_called_once()

    @patch("tor.role_moderator.tasks.update_post_flair.reddit")
    def test_unavailable_flair(self, mock_reddit):
        post = generate_submission()
        mock_reddit.submission = MagicMock(return_value=post)

        with pytest.raises(NotImplementedError):
            update_post_flair(submission_id="abc123", flair="foo")

        mock_reddit.submission.assert_called_once()
        post.flair.choices.assert_called_once_with()
        post.flair.select.assert_not_called()
