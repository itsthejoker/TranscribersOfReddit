from tor.config import Templates

import os
from shutil import rmtree as rm_rf
import tempfile
import unittest


class TemplateDeserializerTest(unittest.TestCase):
    """
    Tests that the template deserializer actually grabs the right template data
    """

    @classmethod
    def setUpClass(cls):
        # Scaffold out the directory structure in a temp directory
        cls.dummy_path = tempfile.mkdtemp()

        for post_type in ['audio', 'images', 'other', 'video']:
            pth = os.path.join(cls.dummy_path, 'templates', post_type)
            os.makedirs(pth)
            with open(os.path.join(pth, 'base.md'), 'w') as f:
                f.write(f'default {post_type} content')

    @classmethod
    def tearDownClass(cls):
        # Clean up the scaffolded out directory structure
        rm_rf(cls.dummy_path)

    def video_settings(self):
        """
        Stub for the ``_settings`` attribute of the ``Templates`` class
        """
        return {
            'filters': {
                'domains': {
                    'video': ['vimeo.com', 'youtube.com'],
                    'audio': ['soundcloud.com'],
                    'images': ['imgur.com', 'photobucket.com'],
                },
            },
        }

    def test_default_content(self):
        loader = Templates(base_path=self.dummy_path,
                           _settings=self.video_settings())
        photobucket_file_path = os.path.join(self.dummy_path, 'templates',
                                             'images', 'photobucket.com.md')
        with open(photobucket_file_path, 'w') as f:
            f.write('photobucket images content')
        vimeo_file_path = os.path.join(self.dummy_path, 'templates', 'video',
                                       'vimeo.com.md')
        with open(vimeo_file_path, 'w') as f:
            f.write('vimeo video content')

        # No domain-specific templates
        youtube = loader.content('youtube.com')
        assert youtube.lower() == 'default video content'

        imgur = loader.content('imgur.com')
        assert imgur.lower() == 'default images content'

        soundcloud = loader.content('soundcloud.com')
        assert soundcloud.lower() == 'default audio content'

        facebook = loader.content('fbcdn.net')
        assert facebook.lower() == 'default other content'

        # Have domain-specific templates
        assert os.path.exists(vimeo_file_path)
        vimeo = loader.content('vimeo.com')
        assert vimeo.lower() == 'vimeo video content'
        os.unlink(vimeo_file_path)
        assert not os.path.exists(vimeo_file_path)

        assert os.path.exists(photobucket_file_path)
        photobucket = loader.content('photobucket.com')
        assert photobucket.lower() == 'photobucket images content'
        os.unlink(photobucket_file_path)
        assert not os.path.exists(photobucket_file_path)
