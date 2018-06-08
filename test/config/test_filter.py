from tor.config import PostConstraintSet

import unittest


class FilterTest(unittest.TestCase):
    """
    """

    def setUp(self):
        pass

    def test_no_domains_in_settings(self):
        settings = {
            'bypass_domain_filter': False,
            'filters': {
                'domains': {
                    'audio': [],
                    'images': [],
                    'video': [],
                }
            },
        }
        no_domains = PostConstraintSet(_settings=settings)

        assert no_domains.url_allowed('example.com')
        assert no_domains.url_allowed('example.net')
        assert no_domains.url_allowed('foo')

    def test_some_domains_allowed(self):
        settings = {
            'bypass_domain_filter': False,
            'filters': {
                'domains': {
                    'audio': ['example.com'],
                    'images': [],
                    'video': [],
                }
            },
        }
        some_domains = PostConstraintSet(_settings=settings)

        assert some_domains.url_allowed('example.com')
        assert not some_domains.url_allowed('example.net')
        assert not some_domains.url_allowed('foo')

    def test_no_filtering(self):
        settings = {
            'bypass_domain_filter': True,
            'filters': {
                'domains': {
                    'audio': ['example.com'],
                    'images': [],
                    'video': [],
                }
            },
        }
        bypass = PostConstraintSet(_settings=settings)

        assert bypass.url_allowed('example.com')
        assert bypass.url_allowed('example.net')
        assert bypass.url_allowed('foo')

    def test_minimum_upvotes(self):
        settings = {
            'upvote_filter': 18,
        }
        picky_sub = PostConstraintSet(_settings=settings)

        low_post_score = 6
        high_post_score = 382

        assert not picky_sub.score_allowed(low_post_score)
        assert picky_sub.score_allowed(high_post_score)
