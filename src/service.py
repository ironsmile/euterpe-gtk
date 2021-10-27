# service.py
#
# Copyright 2021 Doychin Atanasov
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

import sys
import json
import urllib
from .http import Request


class Euterpe:

    @staticmethod
    def check_login_credentials(
        address,
        callback,
        username=None,
        password=None,
        *args
    ):
        '''
            This method checks whether the used address,
            username and password are usable for connecting
            to an Euterpe instance.
        '''

        try:
            if username is None:
                Euterpe.check_unauthenticated(address, callback, *args)
                return

            Euterpe.get_token(address, username, password, callback, *args)
        except Exception:
            sys.excepthook(*sys.exc_info())
            callback(None, None, *args)

    @staticmethod
    def check_unauthenticated(address, callback, *args):
        browse_address = Euterpe.build_url(address, ENDPOINT_BROWSE)
        req = Request(browse_address, callback)
        req.get(*args)

    @staticmethod
    def get_token(address, username, password, callback, *args):
        body = {
            "username": username,
            "password": password,
        }
        login_token_url = Euterpe.build_url(address, ENDPOINT_LOGIN)

        req = Request(login_token_url, callback)
        req.post(
            "application/json",
            bytes(json.dumps(body), 'utf-8'),
            *args
        )

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
