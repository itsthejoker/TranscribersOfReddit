import pytest

from .generators import generate_comment, generate_submission

from tor.context import (
    is_code_of_conduct,
    is_claimed_post_response,
    is_claimable_post,
    has_youtube_captions,
    find_transcription_comment_id,
    find_transcription_id_from_top_comments,
)

import os
import unittest
from unittest.mock import patch, MagicMock


class IsCodeOfConductTest(unittest.TestCase):
    def setUp(self):
        self.comment = generate_comment(author="transcribersofreddit")

    def test_good_messages(self):
        self.comment.submission = generate_submission(flair="Unclaimed")
        self.comment.body = "Hi there! Please read and accept our Code of Conduct so that we can get you started with transcribing. Please read the Code of Conduct below, then respond to this comment with `I accept`.\n\nAfter you respond, I'll process your claim as normal.\n\n---\n\n"
        assert is_code_of_conduct(self.comment)

    def test_bad_messages(self):
        self.comment.submission = generate_submission(flair="Unclaimed")
        self.comment.body = "This post is still unclaimed! Please claim it first or message the mods to take care of this."
        assert not is_code_of_conduct(self.comment)

        self.comment.submission = generate_submission(flair="Completed!")
        self.comment.body = "Awesome, thanks for your help! I'll update your flair to reflect your new count."
        assert not is_code_of_conduct(self.comment)

        self.comment.submission = generate_submission(flair="In Progress")
        self.comment.body = "The post is yours! Best of luck and thanks " 'for helping!\n\nPlease respond with "done" when complete so we ' "can check this one off the list!"
        assert not is_code_of_conduct(self.comment)

        self.comment.submission = generate_submission(flair="In Progress")
        self.comment.body = "I'm sorry, but it looks like someone else has already claimed this post! You can check in with them to see if they need any help, but otherwise I suggest sticking around to see if another post pops up here in a little bit."
        assert not is_code_of_conduct(self.comment)

        self.comment.submission = generate_submission(flair="Completed!")
        self.comment.body = "This post has already been completed! Perhaps you can find a new one on the front page?"
        assert not is_code_of_conduct(self.comment)


class IsUnclaimedTest(unittest.TestCase):
    def setUp(self):
        self.comment = generate_comment(author="transcribersofreddit")

    def test_good_messages(self):
        self.comment.submission = generate_submission(flair="Unclaimed")
        self.comment.body = "This post is still unclaimed! Please claim it first or message the mods to take care of this."
        assert is_claimable_post(self.comment)

    def test_bad_messages(self):
        self.comment.submission = generate_submission(flair="In Progress")
        self.comment.body = "The post is yours! Best of luck and thanks for " 'helping!\n\nPlease respond with "done" when complete so we can ' "check this one off the list!"
        assert not is_claimable_post(self.comment)

        self.comment.submission = generate_submission(flair="Completed!")
        self.comment.body = "This post has already been completed! Perhaps you can find a new one on the front page?"
        assert not is_claimable_post(self.comment)

        self.comment.submission = generate_submission(flair="In Progress")
        self.comment.body = "I'm sorry, but it looks like someone else has already claimed this post! You can check in with them to see if they need any help, but otherwise I suggest sticking around to see if another post pops up here in a little bit."
        assert not is_claimable_post(self.comment)

        self.comment.submission = generate_submission(flair="Completed!")
        self.comment.body = "Awesome, thanks for your help! I'll update your flair to reflect your new count."
        assert not is_claimable_post(self.comment)

        self.comment.submission = generate_submission(flair="Unclaimed")
        self.comment.body = "Hi there! Please read and accept our Code of Conduct so that we can get you started with transcribing. Please read the Code of Conduct below, then respond to this comment with `I accept`.\n\nAfter you respond, I'll process your claim as normal.\n\n---\n\n"
        assert not is_claimable_post(self.comment)


class IsClaimedTest(unittest.TestCase):
    def setUp(self):
        self.comment = generate_comment(author="transcribersofreddit")

    def test_good_messages(self):
        self.comment.submission = generate_submission(flair="In Progress")
        self.comment.body = "The post is yours! Best of luck and thanks for " 'helping!\n\nPlease respond with "done" when complete so we can ' "check this one off the list!"
        assert is_claimed_post_response(self.comment)

        self.comment.submission = generate_submission(flair="In Progress")
        self.comment.body = "I'm sorry, but it looks like someone else has already claimed this post! You can check in with them to see if they need any help, but otherwise I suggest sticking around to see if another post pops up here in a little bit."
        assert is_claimed_post_response(self.comment)

    def test_bad_messages(self):
        self.comment.submission = generate_submission(flair="Completed!")
        self.comment.body = "Awesome, thanks for your help! I'll update your flair to reflect your new count."
        assert not is_claimed_post_response(self.comment)

        self.comment.submission = generate_submission(flair="Unclaimed")
        self.comment.body = "This post is still unclaimed! Please claim it first or message the mods to take care of this."
        assert not is_claimed_post_response(self.comment)

        self.comment.submission = generate_submission(flair="Unclaimed")
        self.comment.body = "Hi there! Please read and accept our Code of Conduct so that we can get you started with transcribing. Please read the Code of Conduct below, then respond to this comment with `I accept`.\n\nAfter you respond, I'll process your claim as normal.\n\n---\n\n"
        assert not is_claimed_post_response(self.comment)

        self.comment.submission = generate_submission(flair="Completed!")
        self.comment.body = "This post has already been completed! Perhaps you can find a new one on the front page?"
        assert not is_claimed_post_response(self.comment)


@pytest.mark.skipif(
    not os.getenv("EXTERNAL_ACCESS"),
    reason="Skipping tests that require access to YouTube (Enable with `EXTERNAL_ACCESS=1`)",
)
class IsYoutubeCaptionTest(unittest.TestCase):
    def test_not_a_link(self):
        link = ""

        assert not has_youtube_captions(link)

    def test_video_with_caption(self):
        link = "https://www.youtube.com/watch?v=RnaEqiVnad0"

        assert has_youtube_captions(link)

    def test_video_without_caption(self):
        link = "https://www.youtube.com/watch?v=AnqN-uN3_wc"
        assert not has_youtube_captions(link)

    def test_other_video_provider(self):
        link = "https://vimeo.com/259878665"
        assert not has_youtube_captions(link)

    def test_non_video(self):
        link = "https://via.placeholder.com/1x1.png"
        assert not has_youtube_captions(link)


class FindTranscriptionWrapperTest(unittest.TestCase):
    def setUp(self):
        self.submission = generate_submission()

    @patch("tor.context.find_transcription_id_from_top_comments", return_value=None)
    @patch("tor.context.find_transcription_id_from_post_history", return_value=None)
    def test_end_to_end_routing(self, mock_history, mock_top_comments):
        assert not find_transcription_comment_id(
            author="abc", post=self.submission, http=None, log=None
        )
        mock_top_comments.assert_called_once()
        mock_history.assert_called_once()

    @patch("tor.context.find_transcription_id_from_top_comments", return_value=None)
    @patch("tor.context.find_transcription_id_from_post_history", return_value="abc123")
    def test_history_comment_found(self, mock_history, mock_top_comments):
        assert find_transcription_comment_id(
            author="abc", post=self.submission, http=None, log=None
        )
        mock_top_comments.assert_called_once()
        mock_history.assert_called_once()

    @patch("tor.context.find_transcription_id_from_top_comments", return_value="abc123")
    @patch("tor.context.find_transcription_id_from_post_history", return_value=None)
    def test_top_level_comment_found(self, mock_history, mock_top_comments):
        assert find_transcription_comment_id(
            author="abc", post=self.submission, http=None, log=None
        )
        mock_top_comments.assert_called_once()
        mock_history.assert_not_called()


@pytest.mark.skip(reason="Reddit is broken, this feature is broken")
class FindTranscriptionInUserHistoryTest(unittest.TestCase):
    def test_stuff(self):
        pass


class FindTranscriptionInTopCommentsTest(unittest.TestCase):
    def setUp(self):
        self.submission = generate_submission()
        self.submission.comments.replace_more.side_effect = None
        self.log = MagicMock(name="logger")

        self.submission.reply("Decoy comment")
        self.submission.reply("other comment")
        self.submission.reply("more comments")

    @patch("tor.context.is_transcription")
    def test_comment_at_top_level(self, mock_tester):
        target = self.submission.reply("This is a transcript")
        mock_tester.side_effect = lambda cmnt: cmnt == target

        found_id = find_transcription_id_from_top_comments(
            author=target.author.name, post=self.submission, log=self.log
        )

        self.log.debug.assert_called_once()

        assert found_id == target.id

    @patch("tor.context.is_transcription")
    def test_nested_comment(self, mock_tester):
        target = self.submission.comments.list()[0].reply("This is a transcript")
        mock_tester.side_effect = lambda cmnt: cmnt == target

        found_id = find_transcription_id_from_top_comments(
            author=target.author.name, post=self.submission, log=self.log
        )

        assert found_id is None
        assert target.id is not None

    @patch("tor.context.is_transcription")
    def test_comment_on_other_submission(self, mock_tester):
        other_submission = generate_submission()
        target = other_submission.reply("This is a transcript")
        mock_tester.side_effect = lambda cmnt: cmnt == target

        found_id = find_transcription_id_from_top_comments(
            author=target.author.name, post=self.submission, log=self.log
        )

        assert found_id is None
        assert target.id is not None
