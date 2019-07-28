import requests
from typing import Dict

class ToR_API(object):
    def __init__(self, token: str=None, key: str=None):
        if token is None or key is None:
            raise Exception('Missing API key or API token!') from None

        self.headers = {
            'Api-Token': token,
            'Api-Secret-Key': key
        }
        self.url = "http://localhost:8000/api/"

        try:
            ping_response = requests.get(
                self.url+"ping/", headers=self.headers
            ).json()
        except requests.exceptions.ConnectionError:
            raise Exception("Cannot connect to API!") from None

        self.volunteer = self.Volunteer(self)
        self.post = self.Post(self)
        self.transcription = self.Transcription(self)

    class Volunteer(object):
        def __init__(self, context):
            self.context = context

        def get(self, username: str=None, id: int=None):
            if username is None and id is None:
                raise Exception('Missing username or ID number!')
            if id:
                url_addition = f"volunteer/{id}/"
            else:
                url_addition = f"volunteer/?username={username}"
            result = requests.get(
                self.context.url + url_addition,
                headers=self.context.headers
            ).json()

            if isinstance(result.get('results'), list):
                result = result.get('results', None)
                if result is not None and len(result) > 0:
                    return result[0]
                else:
                    return None
            else:
                return result

        def plus_one(self, user_obj: Dict=None):
            """
            Creates a dummy transcription for the given user in the event
            that something has gone wrong and a score needs to be manually
            adjusted.

            :param user_obj: the output of self.get()
            :return:
            """
            if not isinstance(user_obj, dict):
                raise Exception("Need previously fetched user in dict form.")
            result = requests.post(
                self.context.url + f"volunteer/{user_obj.get('id')}/gamma_plusone/",
                headers=self.context.headers
            )
            result.raise_for_status()
            return result.json()

        def create(self, username: str=None):
            if not username:
                raise Exception("Must have a username to create a user!")

            result = requests.post(
                self.context.url + 'volunteer/',
                json={'username': username},
                headers=self.context.headers
            )
            return result.json()

    class Post(object):
        def __init__(self, context):
            self.context = context

        def create(self, post_id: str=None, post_url: str=None, tor_url: str=None):
            if post_id is None:
                raise Exception('Missing post_id (str)!')

            data = {
                "post_id": post_id,
                "source": "transcribersofreddit",  # max length for source key
                "tor_url": tor_url,
                "url": post_url
            }
            result = requests.post(
                self.context.url + 'post/',
                json=data,
                headers=self.context.headers
            )
            result.raise_for_status()
            return result.json()

        def get(self, post_id: str=None, id: int=None):
            if post_id is None and id is None:
                raise Exception('Missing post_id (str) or db id (int)!')

            if id:
                url_addition = f"post/{id}/"
            else:
                url_addition = f"post/?post_id={post_id}"

            result = requests.get(
                self.context.url + url_addition,
                headers=self.context.headers
            ).json()

            if isinstance(result.get('results'), list):
                result = result.get('results', None)
                if result is not None and len(result) > 0:
                    return result[0]
                else:
                    return None
            else:
                return result

        def claim(self, post_obj: Dict, volunteer: Dict):
            if not isinstance(post_obj, dict) or not isinstance(volunteer, dict):
                raise Exception(
                    'Must receive both post object and volunteer in dict form!'
                )
            post_id = post_obj.get('id')
            v_id = volunteer.get('id')

            data = {
                'v_id': v_id
            }

            result = requests.post(
                self.context.url + f'post/{post_id}/claim/',
                json=data,
                headers=self.context.headers
            )
            return result.json()


        def done(self, post_obj: Dict, volunteer: Dict):
            if not isinstance(post_obj, dict) or not isinstance(volunteer, dict):
                raise Exception(
                    'Must receive both post object and volunteer in dict form!'
                )
            post_id = post_obj.get('id')
            v_id = volunteer.get('id')

            data = {
                'v_id': v_id
            }

            result = requests.post(
                self.context.url + f'post/{post_id}/done/',
                json=data,
                headers=self.context.headers
            )
            return result.json()

    class Transcription(object):
        def __init__(self, context):
            self.context = context

        def create(
                self,
                post_obj: Dict=None,
                volunteer_obj:Dict =None,
                transcription_text:str=None,
                transcription_url:str=None,
                transcription_id:str=None,
                removed_from_reddit=False
        ):
            if not post_obj:
                raise Exception('Must have the post object provided from API!')
            if not volunteer_obj:
                raise Exception('Must have volunteer object provided from API!')
            if not transcription_text:
                raise Exception('Missing text for transcription!')
            if not transcription_url:
                raise Exception('Missing url for completed transcription!')
            if not transcription_id:
                raise Exception('Missing ID for completed transcription!')

            post_id = post_obj.get('id')
            v_id = volunteer_obj.get('id')

            data = {
                "post_id": post_id,
                "v_id": v_id,
                "t_id": transcription_id,
                "completion_method": "transcribersofreddit",
                "t_url": transcription_url,
                "t_text": transcription_text,
                "removed_from_reddit": removed_from_reddit
            }

            return requests.post(
                self.context.url+'transcription/',
                data=data,
                headers=self.context.headers
            ).json()


t = ToR_API(key="dSA4CbL1MMxJ", token="514d7f83c087873a9070822b8a74f69f")
