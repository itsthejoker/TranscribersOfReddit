from tor.role_moderator.tasks import process_comment, process_mod_intervention

from ..celery import (
    signature,
    reset_signatures,
    assert_no_tasks_called,
    assert_only_tasks_called,
)
from ..generators import generate_redditor, generate_comment, generate_submission

import unittest
from unittest.mock import patch, MagicMock


class ProcessConductCommentTest(unittest.TestCase):
    """
    Given that the parent comment is about the code of conduct...
    """

    def setUp(self):
        reset_signatures()
        submission = generate_submission(flair="Unclaimed")
        parent = generate_comment(
            body="You have to sign the code of conduct before you can "
            "claim anything, you dunce.",
            author="transcribersofreddit",
            submission=submission,
        )
        target = parent.reply("I accept. I volunteer as tribute!")

        self.comment = target

    @patch("tor.role_moderator.tasks.signature", side_effect=signature)
    @patch("tor.role_moderator.tasks.process_comment.reddit")
    @patch("tor.role_moderator.tasks.process_mod_intervention", side_effect=None)
    def test_import_tasks(self, mod_intervention, mock_reddit, mock_signature):
        mock_reddit.comment = MagicMock(name="comment", return_value=self.comment)

        process_comment(self.comment.id)

        for mod_task in ["claim_post"]:
            mock_signature.assert_any_call(f"tor.role_moderator.tasks.{mod_task}")
        for anon_task in ["accept_code_of_conduct", "unhandled_comment"]:
            mock_signature.assert_any_call(f"tor.role_anyone.tasks.{anon_task}")

    @patch("tor.role_moderator.tasks.signature", side_effect=signature)
    @patch("tor.role_moderator.tasks.process_comment.reddit")
    @patch("tor.role_moderator.tasks.process_mod_intervention", side_effect=None)
    def test_agree(self, mod_intervention, mock_reddit, mock_signature):
        mock_reddit.comment = MagicMock(name="comment", return_value=self.comment)

        self.comment.body = "I accept the consequences"
        process_comment(self.comment.id)

        mock_reddit.comment.assert_called_with(self.comment.id)

        signature(
            "tor.role_anyone.tasks.accept_code_of_conduct"
        ).delay.assert_called_once_with(self.comment.author.name)
        signature("tor.role_moderator.tasks.claim_post").delay.assert_called_once_with(
            self.comment.id, verify=False, first_claim=True
        )

        assert_only_tasks_called(
            "tor.role_anyone.tasks.accept_code_of_conduct",
            "tor.role_moderator.tasks.claim_post",
        )
        mod_intervention.assert_called_once()

    @patch("tor.role_moderator.tasks.signature", side_effect=signature)
    @patch("tor.role_moderator.tasks.process_comment.reddit")
    @patch("tor.role_moderator.tasks.process_mod_intervention", side_effect=None)
    def test_disagree(self, mod_intervention, mock_reddit, mock_signature):
        mock_reddit.comment = MagicMock(name="comment", return_value=self.comment)

        self.comment.body = "Nah, go screw yourself."
        process_comment(self.comment.id)

        signature(
            "tor.role_anyone.tasks.unhandled_comment"
        ).delay.assert_called_once_with(
            comment_id=self.comment.id, body=self.comment.body
        )
        assert_only_tasks_called("tor.role_anyone.tasks.unhandled_comment")
        mock_reddit.comment.assert_called_with(self.comment.id)
        mod_intervention.assert_called_once()


class ProcessClaimableCommentTest(unittest.TestCase):
    """
    Given that the parent comment indicates the post is unclaimed...
    """

    def setUp(self):
        reset_signatures()
        submission = generate_submission(flair="Unclaimed")
        parent = generate_comment(
            body="This post is unclaimed",
            author="transcribersofreddit",
            submission=submission,
        )
        target = parent.reply("I claim it! I volunteer as tribute!")

        self.comment = target

    @patch("tor.role_moderator.tasks.signature", side_effect=signature)
    @patch("tor.role_moderator.tasks.process_comment.reddit")
    @patch("tor.role_moderator.tasks.process_mod_intervention", side_effect=None)
    def test_import_tasks(self, mod_intervention, mock_reddit, mock_signature):
        mock_reddit.comment = MagicMock(name="comment", return_value=self.comment)

        process_comment(self.comment.id)

        for mod_task in ["claim_post"]:
            mock_signature.assert_any_call(f"tor.role_moderator.tasks.{mod_task}")
        for anon_task in ["accept_code_of_conduct", "unhandled_comment"]:
            mock_signature.assert_any_call(f"tor.role_anyone.tasks.{anon_task}")

    @patch("tor.role_moderator.tasks.signature", side_effect=signature)
    @patch("tor.role_moderator.tasks.process_comment.reddit")
    @patch("tor.role_moderator.tasks.process_mod_intervention", side_effect=None)
    def test_other_bot_commented(self, mod_intervention, mock_reddit, mock_signature):
        mock_reddit.comment = MagicMock(name="comment", return_value=self.comment)

        self.comment.author = generate_redditor(username="transcribot")
        process_comment(self.comment.id)

        assert_no_tasks_called()
        mock_reddit.comment.assert_called_with(self.comment.id)
        mod_intervention.assert_not_called()

    @patch("tor.role_moderator.tasks.signature", side_effect=signature)
    @patch("tor.role_moderator.tasks.process_comment.reddit")
    @patch("tor.role_moderator.tasks.process_mod_intervention", side_effect=None)
    def test_claim(self, mod_intervention, mock_reddit, mock_signature):
        mock_reddit.comment = MagicMock(name="comment", return_value=self.comment)

        self.comment.body = "I claim this land in the name of France!"
        process_comment(self.comment.id)

        signature("tor.role_moderator.tasks.claim_post").delay.assert_called_once_with(
            self.comment.id
        )

        assert_only_tasks_called("tor.role_moderator.tasks.claim_post")
        mock_reddit.comment.assert_called_with(self.comment.id)
        mod_intervention.assert_called_once()

    @patch("tor.role_moderator.tasks.signature", side_effect=signature)
    @patch("tor.role_moderator.tasks.process_comment.reddit")
    @patch("tor.role_moderator.tasks.process_mod_intervention", side_effect=None)
    def test_refuse(self, mod_intervention, mock_reddit, mock_signature):
        mock_reddit.comment = MagicMock(name="comment", return_value=self.comment)

        self.comment.body = "Nah, screw it. I can do it later"
        process_comment(self.comment.id)

        signature("tor.role_anyone.tasks.unhandled_comment").delay.assert_called_once()
        assert_only_tasks_called("tor.role_anyone.tasks.unhandled_comment")
        mock_reddit.comment.assert_called_with(self.comment.id)
        mod_intervention.assert_called_once()

    @patch("tor.role_moderator.tasks.signature", side_effect=signature)
    def test_mod_intervention(self, mock_signature):
        self.comment.body = "Nah, fuck it. I can do it later"

        process_mod_intervention(self.comment)

        signature("tor.role_anyone.tasks.send_to_slack").delay.assert_called_once()

        assert_only_tasks_called("tor.role_anyone.tasks.send_to_slack")


class ProcessDoneCommentTest(unittest.TestCase):
    """
    Given that the parent comment indicates the post is unclaimed...
    """

    def setUp(self):
        reset_signatures()
        submission = generate_submission(flair="In Progress")
        parent = generate_comment(
            body="The post is yours!",
            author="transcribersofreddit",
            submission=submission,
        )
        target = parent.reply("done")

        self.comment = target

    @patch("tor.role_moderator.tasks.signature", side_effect=signature)
    @patch("tor.role_moderator.tasks.process_comment.reddit")
    def test_misspelled_done(self, mock_reddit, mock_signature):
        mock_reddit.comment = MagicMock(name="comment", return_value=self.comment)

        self.comment.body = "deno"
        process_comment(self.comment.id)
        signature(
            "tor.role_moderator.tasks.verify_post_complete"
        ).delay.assert_called_once()
        # TODO: more to come when actual functionality is built-out

        assert_only_tasks_called("tor.role_moderator.tasks.verify_post_complete")
        mock_reddit.comment.assert_any_call(self.comment.id)

    @patch("tor.role_moderator.tasks.signature", side_effect=signature)
    @patch("tor.role_moderator.tasks.process_comment.reddit")
    def test_done(self, mock_reddit, mock_signature):
        mock_reddit.comment = MagicMock(name="comment", return_value=self.comment)
        process_comment(self.comment.id)
        # TODO: more to come when actual functionality is built-out
        signature(
            "tor.role_moderator.tasks.verify_post_complete"
        ).delay.assert_called_once()

        assert_only_tasks_called("tor.role_moderator.tasks.verify_post_complete")
        mock_reddit.comment.assert_any_call(self.comment.id)

    @patch("tor.role_moderator.tasks.signature", side_effect=signature)
    @patch("tor.role_moderator.tasks.process_comment.reddit")
    def test_override_as_admin(self, mock_reddit, mock_signature):
        mock_reddit.comment = MagicMock(name="comment", return_value=self.comment)

        self.comment.body = "!override"
        self.comment.author = generate_redditor(username="tor_mod5")
        process_comment(self.comment.id)
        # TODO: Assert !override task is called

        assert_only_tasks_called(
            # TODO: Assert only the !override task is called
        )
        mock_reddit.comment.assert_any_call(self.comment.id)

    @patch("tor.role_moderator.tasks.signature", side_effect=signature)
    @patch("tor.role_moderator.tasks.process_comment.reddit")
    def test_override_as_anon(self, mock_reddit, mock_signature):
        mock_reddit.comment = MagicMock(name="comment", return_value=self.comment)

        self.comment.body = "!override"
        # TODO: Test exception being thrown because unprivileged user???
        process_comment(self.comment.id)
        # TODO: more to come when actual functionality is built-out

        assert_no_tasks_called()
        # assert_only_tasks_called(
        #     # TODO
        # )
        mock_reddit.comment.assert_any_call(self.comment.id)

    @patch("tor.role_moderator.tasks.signature", side_effect=signature)
    @patch("tor.role_moderator.tasks.process_comment.reddit")
    def test_weird_response(self, mock_reddit, mock_signature):
        mock_reddit.comment = MagicMock(name="comment", return_value=self.comment)

        self.comment.body = "adsflkj232oiqqw123lk1209uasd;"
        process_comment(self.comment.id)

        signature("tor.role_anyone.tasks.unhandled_comment").delay.assert_called_once()

        assert_only_tasks_called("tor.role_anyone.tasks.unhandled_comment")
        mock_reddit.comment.assert_any_call(self.comment.id)
