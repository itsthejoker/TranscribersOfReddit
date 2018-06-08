from tor.role_moderator.tasks import post_to_tor
from tor.user_interaction import (
    post_comment,
    format_bot_response as _,
)
from tor import __version__

from ..celery import (
    signature,
    reset_signatures,
    assert_no_tasks_called,
    assert_only_tasks_called,
)
from ..generators import (
    generate_comment,
    generate_submission,
    generate_subreddit,
)

import loremipsum
import unittest
from unittest.mock import patch


class PostToTorTaskTest(unittest.TestCase):

    def setUp(self):
        reset_signatures()

    @patch('tor.role_moderator.tasks.has_youtube_captions',
           return_value=True)
    @patch('tor.role_moderator.tasks.post_comment')
    @patch('tor.role_moderator.tasks.signature', side_effect=signature)
    @patch('tor.role_moderator.tasks.Config')
    @patch('tor.role_moderator.tasks.post_to_tor.reddit')
    @patch('tor.role_moderator.tasks.post_to_tor.redis')
    def test_youtube_with_captions_post(self, mock_redis, mock_reddit,
                                        mock_config, mock_signature,
                                        mock_post_comment, mock_captions):
        comment = generate_comment()
        post = generate_submission(reply=comment)
        sub = generate_subreddit(submission=post)
        mock_reddit.subreddit.return_value = sub
        mock_config.templates.url_type.return_value = 'other'
        mock_config.subreddit.return_value = mock_config

        def stub_post_comment(repliable, body):
            comment.body = _(body)
            return comment

        mock_post_comment.side_effect = stub_post_comment

        reddit_link = 'https://www.reddit.com/r/todayilearned/comments/' \
            '7y9tcj/til_that_when_a_man_had_a_heart_attack_at_a/'

        post_to_tor('subreddit', 'title goes here', reddit_link, 'youtube.com',
                    post_id=post.id,
                    media_link='https://www.youtube.com/watch?v=oHg5SJYRHA0')

        mock_redis.incr.assert_any_call('total_posted', amount=1)
        mock_redis.incr.assert_any_call('total_new', amount=1)

        sub.submit.assert_not_called()
        mock_post_comment.assert_not_called()
        assert_no_tasks_called()

    @patch('tor.role_moderator.tasks.has_youtube_captions',
           return_value=False)
    @patch('tor.role_moderator.tasks.post_comment')
    @patch('tor.role_moderator.tasks.signature', side_effect=signature)
    @patch('tor.role_moderator.tasks.Config')
    @patch('tor.role_moderator.tasks.post_to_tor.reddit')
    @patch('tor.role_moderator.tasks.post_to_tor.redis')
    def test_new_post(self, mock_redis, mock_reddit, mock_config,
                      mock_signature, mock_post_comment, mock_captions):
        comment = generate_comment()
        post = generate_submission(reply=comment)
        sub = generate_subreddit(submission=post)
        mock_reddit.subreddit.return_value = sub
        mock_config.templates.url_type.return_value = 'other'
        mock_config.subreddit.return_value = mock_config

        def stub_post_comment(repliable, body):
            comment.body = _(body)
            return comment

        mock_post_comment.side_effect = stub_post_comment

        reddit_link = 'https://www.reddit.com/r/todayilearned/comments/' \
            '7y9tcj/til_that_when_a_man_had_a_heart_attack_at_a/'

        post_to_tor('subreddit', 'title goes here', reddit_link, 'example.com',
                    post_id=post.id,
                    media_link='https://www.example.com/foo.jpg')

        mock_redis.incr.assert_any_call('total_posted', amount=1)
        mock_redis.incr.assert_any_call('total_new', amount=1)

        sub.submit.assert_called_once()
        mock_post_comment.assert_called_once()
        signature('tor.role_moderator.tasks.update_post_flair').delay \
            .assert_called_once()

        assert_only_tasks_called(
            'tor.role_moderator.tasks.update_post_flair',
        )

        assert f'subreddit | Other | "title goes here"' == post.title
        assert __version__ in comment.body.lower()

    def test_post_comment_pagination(self):
        comment = generate_comment()
        post = generate_submission(reply=comment)

        # Tons of text that needs paginating
        body = '\n\n'.join(
            [' '.join(loremipsum.get_sentences(20)) for _ in range(50)]
        )
        # Also mock up having a _really_ long line
        body += '\n\n'
        body += ' '.join(loremipsum.get_sentences(1000))

        # TADA!! The main event:
        last_comment = post_comment(repliable=post, body=body)

        # Make sure we replied to the previous comment instead of having them
        # all reply as top-level comments
        comment.reply.assert_called_once()
        post.reply.assert_called_once()

        assert last_comment.kind == 't1', 'Return type is not Comment'

        # Find depth of comments
        ptr = last_comment
        num_comments = 0
        for i in range(100):
            num_comments = i

            if ptr.kind != 't1':
                break
            else:
                ptr = ptr.parent()

        assert num_comments > 1, "Comments did not need to be paginated"
