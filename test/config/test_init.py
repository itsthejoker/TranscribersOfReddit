from tor.config import Config

import unittest
from unittest.mock import patch


def dummy_json_loader(path):
    if path.endswith('settings.json'):
        return {
            'environment': 'testing',
            'gifs': {
                'no': ['https://no.example.com/'],
                'thumbs_up': ['https://thumbs_up.example.com/'],
            },
        }
    elif path.endswith('subreddits.json'):
        return {
            'me_irl': {},
            'ProgrammingHumor': {},
        }
    elif path.endswith('globals.json'):
        return {
            'environment': 'testing',
            'moderators': [
            ],
        }
    else:
        raise NotImplementedError(path)


class InitConfigTest(unittest.TestCase):
    """
    Tests for the Config object's methods for initialization
    """

    @patch('tor.config.helpers.assert_valid_directory',
           side_effect=None)
    @patch('tor.config.helpers.load_json',
           side_effect=dummy_json_loader)
    def test_default_init(self, mock_loader, mock_valid_directory):
        config = Config()

        mock_valid_directory.assert_called()
        assert config.env in ['development', 'testing', 'production']
        assert config.name == '[default]'
        assert str(config) == 'Default configuration'
        assert config.gifs.no
        assert config.gifs.thumbs_up
        assert 'me_irl' in config.subreddits

    @patch('tor.config.helpers.assert_valid_directory',
           side_effect=None)
    def test_init_with_settings(self, mock_valid_directory):
        config = Config(_settings={'fizz': 'buzz'})

        mock_valid_directory.assert_not_called()
        assert config._settings.get('fizz') == 'buzz'

    @patch('tor.config.helpers.assert_valid_directory',
           side_effect=None)
    def test_init_with_base_path(self, mock_valid_directory):
        config = Config(base_path='/fizz/buzz')

        mock_valid_directory.assert_called()
        assert config._base == '/fizz/buzz'

    @patch('tor.config.helpers.assert_valid_directory',
           side_effect=None)
    @patch('tor.config.helpers.load_json',
           side_effect=dummy_json_loader)
    def test_init_by_factory(self, mock_loader, mock_valid_directory):
        config = Config.subreddit('foo')

        mock_valid_directory.assert_not_called()
        assert config.env in ['development', 'testing', 'production']
        assert config.name == 'foo'
        assert str(config) == '/r/foo configuration'

    @patch('tor.config.helpers.assert_valid_directory',
           side_effect=None)
    @patch('tor.config.helpers.load_json',
           side_effect=dummy_json_loader)
    def test_lazy_loaded_attributes(self, mock_loader, mock_valid_directory):
        config = Config()

        assert hasattr(config.templates, 'content'), 'Config.templates must ' \
            'be of type Templates'
        assert hasattr(config.filters, 'score_allowed'), 'Config.filters must' \
            ' be of type PostConstraintSet'
