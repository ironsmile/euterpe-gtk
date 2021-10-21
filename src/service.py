
import requests
import urllib

class Euterpe:

    @staticmethod
    def check_login_credentials(address, username=None, password=None):
        '''
            This method checks whether the used address,
            username and password are usable for connecting
            to an Euterpe instance. On success it returns a
            token if authentication is required or None if
            it is not. If something is wrong then it raises
            an exception.
        '''

        if username is None:
            return Euterpe.check_unauthenticated(address)

        return Euterpe.get_token(address, username, password)

    @staticmethod
    def check_unauthenticated(address):
        browse_address = Euterpe.build_url(address, ENDPOINT_BROWSE)
        resp = requests.get(browse_address)
        if resp.status_code != 200:
            resp.raise_for_status()

        return None

    @staticmethod
    def get_token(address, username, password):
        body = {
            "username": username,
            "password": password,
        }
        login_token_url = Euterpe.build_url(address, ENDPOINT_LOGIN)

        resp = requests.post(login_token_url, json=body)
        if resp != 200:
            resp.raise_for_status()

        respJSON = resp.json()
        if 'token' not in respJSON:
            raise Exception("no token in the JSON response from Euterpe")

        return respJSON["token"]

    @staticmethod
    def build_url(remote_url, endpoint):
        parsed = urllib.parse.urlparse(remote_url)

        # If the remote URL is an domain or a sub-domain without a path
        # component such as https://music.example.com
        if parsed.path == "":
            return urllib.parse.urljoin(remote_url, endpoint)

        if not remote_url.endswith("/"):
            remote_url = remote_url + "/"

        return urllib.parse.urljoin(remote_url, endpoint.lstrip("/"))

    def __init__(self, address, token=None):
        self._remote_address = address
        self._token = token


ENDPOINT_LOGIN = '/v1/login/token/'
ENDPOINT_REGISTER_TOKEN = '/v1/register/token/'
ENDPOINT_SEARCH = '/v1/search/'
ENDPOINT_FILE = '/v1/file/{}'
ENDPOINT_ALBUM_ART = '/v1/album/{}/artwork'
ENDPOINT_BROWSE = "/v1/browse/"
