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
from .http import Request, AsyncRequest, Priority
import euterpe_gtk.log as log
from enum import Enum

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

            It calls callback(<status>, <data>, *args) ad its
            end. Where <status> is the HTTP status of the auth
            request response and <data> is the response body.
        '''

        try:
            if username is None:
                Euterpe.check_unauthenticated(address, callback, *args)
                return

            Euterpe.check_authenticated(
                address,
                username,
                password,
                callback,
                *args,
            )
        except Exception:
            sys.excepthook(*sys.exc_info())
            callback(None, None, *args)

    @staticmethod
    def check_unauthenticated(address, callback, *args):
        browse_address = Euterpe.build_url(address, ENDPOINT_BROWSE)
        req = Request(browse_address, callback)
        req.get(*args)

    @staticmethod
    def check_authenticated(address, username, password, callback, *args):
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

    def __init__(self, version):
        self._remote_address = None
        self._token = None
        self._user_agent = "Euterpe-GTK Player/{}".format(version)

    def set_address(self, address):
        self._remote_address = address

    def set_token(self, token):
        self._token = token

    def search(self, query, callback):
        cb = JSONBodyCallback(callback)
        address = Euterpe.build_url(self._remote_address, ENDPOINT_SEARCH)
        address = "{}?q={}".format(address, urllib.parse.quote(query, safe=''))
        req = self._create_request(address, cb)
        req.get(query)

    def get_recently_added(self, what, callback):
        if what not in ['album', 'artist']:
            log.warning("unknown rencently added type: {}", what)
            return

        cb = JSONBodyCallback(callback)
        address = Euterpe.build_url(self._remote_address, ENDPOINT_BROWSE)
        address = "{}?by={}&per-page=10&order-by=id&order=desc".format(
            address,
            urllib.parse.quote(what, safe='')
        )
        req = self._create_request(address, cb)
        req.get()

    def make_request(self, uri, callback):
        full_url = Euterpe.build_url(self._remote_address, uri)
        cb = JSONBodyCallback(callback)
        req = self._create_request(full_url, cb)
        req.get()

    def get_album_artwork(self, album_id, size, cancellable, callback, *args):
        '''
        Makes a request for an album artwork.

            * album_id (int) - the ID of the album for which to get an image.
            * callback - a function described in the http.AsyncRequest.
        '''
        artwork_path = ENDPOINT_ALBUM_ART.format(album_id)
        address = Euterpe.build_url(self._remote_address, artwork_path)

        if size == ArtworkSize.SMALL:
            address = "{}?size={}".format(address, 'small')

        req = self._create_async_request(address, cancellable, callback, Priority.LOW)
        req.get(*args)

    def get_artist_artwork(self, artist_id, size, cancellable, callback, *args):
        '''
        Makes a request for an artist image.

            * artist_id (int) - the ID of the artist for which to get an image.
            * callback - a function described in the http.AsyncRequest.
        '''
        artwork_path = ENDPOINT_ARTIST_ART.format(artist_id)
        address = Euterpe.build_url(self._remote_address, artwork_path)

        if size == ArtworkSize.SMALL:
            address = "{}?size={}".format(address, 'small')

        req = self._create_async_request(address, cancellable, callback, Priority.LOW)
        req.get(*args)

    def get_browse_uri(self, what):
        if what not in ['album', 'artist']:
            log.warning("unknown browse type: {}", what)
            return None

        address = "{}?by={}&per-page=30&order-by=name&order=asc".format(
            ENDPOINT_BROWSE,
            urllib.parse.quote(what, safe='')
        )

        return address

    def _create_request(self, address, callback):
        '''
        Creates a request which body will be read fully before the callback
        is called.
        '''
        req = Request(address, callback)
        req.set_header("User-Agent", self._user_agent)
        if self._token is not None:
            req.set_header("Authorization", "Bearer {}".format(self._token))
        return req

    def _create_async_request(self, address, cancellable, callback, priority):
        '''
        Creates a request which will cause the callback to be called once the
        response headers have been read. But before the response body has been
        read too.
        '''
        req = AsyncRequest(address, cancellable, callback, priority=priority)
        req.set_header("User-Agent", self._user_agent)
        if self._token is not None:
            req.set_header("Authorization", "Bearer {}".format(self._token))
        return req

    def get_track_url(self, trackID):
        return Euterpe.build_url(
            self._remote_address,
            ENDPOINT_FILE.format(trackID),
        )

    def get_token(self):
        return self._token


class JSONBodyCallback(object):
    '''
    A converter from http.Request callback to a callback which receives
    the body as an python object instead of an input stream.
    '''

    def __init__(self, callback):
        self._callback = callback

    def __call__(self, status, body, *args):
        try:
            responseJSON = json.loads(body)
        except Exception as err:
            log.warning("Failed to parse JSON response: {}",
                err
            )
            self._callback(status, None, *args)
        else:
            self._callback(status, responseJSON, *args)


class ArtworkSize(Enum):
    FULL = 'full'
    SMALL = 'small'


ENDPOINT_LOGIN = '/v1/login/token/'
ENDPOINT_REGISTER_TOKEN = '/v1/register/token/'
ENDPOINT_SEARCH = '/v1/search/'
ENDPOINT_FILE = '/v1/file/{}'
ENDPOINT_ALBUM_ART = '/v1/album/{}/artwork'
ENDPOINT_ARTIST_ART = '/v1/artist/{}/image'
ENDPOINT_BROWSE = "/v1/browse/"
