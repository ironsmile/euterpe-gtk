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

from gi.repository import GObject, Gio, GLib
import sys
import json
import mimetypes
import urllib.parse
from euterpe_gtk.http import Request, AsyncRequest, Priority
from euterpe_gtk.utils import emit_signal
import euterpe_gtk.log as log
from enum import Enum

SIGNAL_TOKEN_EXPIRED = "token-expired"

class Euterpe(GObject.Object):

    __gsignals__ = {
        SIGNAL_TOKEN_EXPIRED: (GObject.SignalFlags.RUN_FIRST, None, ()),
    }

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
            GLib.Bytes.new(bytes(json.dumps(body), 'utf-8')),
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
        GObject.GObject.__init__(self)

        self._remote_address = None
        self._token = None
        self._username = None
        self._user_agent = "Euterpe-GTK Player/{}".format(version)

    def set_address(self, address):
        self._remote_address = address

    def get_address(self):
        return self._remote_address

    def set_token(self, token):
        self._token = token

    def get_token(self):
        return self._token

    def set_username(self, username):
        self._username = username

    def get_username(self):
        return self._username

    def search(self, query, callback):
        cb = TokenExpirationCallback(self, JSONBodyCallback(callback))
        address = Euterpe.build_url(self._remote_address, ENDPOINT_SEARCH)
        address = "{}?q={}".format(address, urllib.parse.quote(query, safe=''))
        req = self._create_request(address, cb)
        req.get(query)

    def get_playlist(self, playlist_id, callback):
        cb = TokenExpirationCallback(self, JSONBodyCallback(callback))
        address = Euterpe.build_url(self._remote_address, ENDPOINT_PLAYLIST.format(
            playlist_id,
        ))
        req = self._create_request(address, cb)
        req.get()

    def get_playlists(self, callback, page=1):
        cb = TokenExpirationCallback(self, JSONBodyCallback(callback))
        address = ("{}?per-page=500&page={}".format(
            Euterpe.build_url(self._remote_address, ENDPOINT_PLAYLISTS),
            page,
        ))
        req = self._create_request(address, cb)
        req.get()

    def change_playlist(self, playlist_id, callback,
        name=None, description=None, add_track_ids=None, remove_indeces=None,
    ):
        cb = TokenExpirationCallback(self, callback)
        address = Euterpe.build_url(self._remote_address, ENDPOINT_PLAYLIST.format(
            playlist_id,
        ))
        body = {}

        if name is not None:
            body["name"] = name
        if description is not None:
            body["description"] = description
        if add_track_ids is not None:
            body["add_tracks_by_id"] = add_track_ids
        if remove_indeces is not None:
            body["remove_indeces"] = remove_indeces

        req = self._create_request(address, cb)
        req.patch(
            "appliction/json",
             GLib.Bytes.new(bytes(json.dumps(body), 'utf-8')),
        )

    def create_playlist(self, name, description, callback, *args):
        """
        Creates an empty playlist.
        """
        cb = TokenExpirationCallback(self, JSONBodyCallback(callback))
        address = Euterpe.build_url(self._remote_address, ENDPOINT_PLAYLISTS)
        req = self._create_request(address, cb)
        req.post(
            "application/json",
            GLib.Bytes.new(bytes(json.dumps({"name": name, "description": description}), 'utf-8')),
            *args,
        )

    def delete_playlist(self, playlist_id, callback, *args):
        """
        Deletes a particular playlist from the server.
        """
        cb = TokenExpirationCallback(self, callback)
        address = Euterpe.build_url(self._remote_address, ENDPOINT_PLAYLIST.format(
            playlist_id,
        ))
        req = self._create_request(address, cb)
        req.delete(*args)

    def get_recently_added(self, what, callback):
        if what not in ['album', 'artist']:
            log.warning("unknown rencently added type: {}", what)
            return

        cb = TokenExpirationCallback(self, JSONBodyCallback(callback))
        address = Euterpe.build_url(self._remote_address, ENDPOINT_BROWSE)
        address = "{}?by={}&per-page=10&order-by=id&order=desc".format(
            address,
            urllib.parse.quote(what, safe='')
        )
        req = self._create_request(address, cb)
        req.get()

    def make_request(self, uri, callback):
        full_url = Euterpe.build_url(self._remote_address, uri)
        cb = TokenExpirationCallback(self, JSONBodyCallback(callback))
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

        cb = TokenExpirationCallback(self, callback)
        req = self._create_async_request(address, cancellable, cb, Priority.LOW)
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

        cb = TokenExpirationCallback(self, callback)
        req = self._create_async_request(address, cancellable, cb, Priority.LOW)
        req.get(*args)

    def get_browse_uri(self, what, page=1, per_page=30, order_by="name", order="asc"):
        if what not in ['album', 'artist', 'song']:
            log.warning("unknown browse type: {}", what)
            return None

        if order not in ["asc", "desc"]:
            log.warning("unknown order: {}", order)
            return None

        if order_by not in ["id", "name", "random", "frequency", "recency", "year"]:
            log.warning("unknown order_by: {}", order_by)
            return

        address = "{endpoint}?by={by}&page={page}&per-page={per_page}&order-by={order_by}&order={order}".format(
            endpoint=ENDPOINT_BROWSE,
            by=urllib.parse.quote(what, safe=''),
            per_page=per_page,
            page=page,
            order_by=order_by,
            order=order,
        )

        return address

    def get_playlists_uri(self, page=1, per_page=40):
        address = "{endpoint}?page={page}&per-page={per_page}".format(
            endpoint=ENDPOINT_PLAYLISTS,
            per_page=per_page,
            page=page,
        )

        return address

    def set_album_image(self, album_id, file_name, cancellable, callback, *args):
        '''
        Asynchronously reads a file and then sets it as the image for the
        album identified by `album_id`.

        callback should accept the following arguments:

            * HTTP status of the upload request. May be None on error.
            * Body of the response. Maybe error message on error.
            * The cancel function passed here `cancellable`
            * *`args`
        '''
        artwork_path = ENDPOINT_ALBUM_ART.format(album_id)
        art_url = Euterpe.build_url(self._remote_address, artwork_path)

        mtype, encoding = mimetypes.guess_type(file_name)
        if mtype is None:
            mtype = "image"

        file = Gio.File.new_for_path(file_name)
        file.read_async(GLib.PRIORITY_HIGH, cancellable, self._on_image_open,
            art_url, cancellable, callback, mtype, args)

    def set_artist_image(self, artist_id, file_name, cancellable, callback, *args):
        '''
        Asynchronously reads a file and then sets it as the image for the
        artist identified by `artist_id`.

        callback should accept the following arguments:

            * HTTP status of the upload request. May be None on error.
            * Body of the response. Maybe error message on error.
            * The cancel function passed here `cancellable`
            * *`args`
        '''
        artwork_path = ENDPOINT_ARTIST_ART.format(artist_id)
        art_url = Euterpe.build_url(self._remote_address, artwork_path)

        mtype, encoding = mimetypes.guess_type(file_name)
        if mtype is None:
            mtype = "image"

        file = Gio.File.new_for_path(file_name)
        file.read_async(GLib.PRIORITY_HIGH, cancellable, self._on_image_open,
            art_url, cancellable, callback, mtype, args)

    def _on_image_open(self, obj, res, art_url, cancellable, callback, mtype, args):
        image_stream = obj.read_finish(res)
        if image_stream is None:
            log.warning("failed to open file for uploading to {}", art_url)
            callback(None, "Could open file.", None, *args)
            return

        image_stream.read_bytes_async(
            5 * 1024 * 1024, GLib.PRIORITY_HIGH, cancellable, self._on_image_bytes,
            art_url, cancellable, callback, mtype, args)

    def _on_image_bytes(self, obj, res, art_url, cancellable, callback, mtype, args):
        image_data = obj.read_bytes_finish(res)
        if image_data is None:
            log.warning("failed to read file for uploading to {}", art_url)
            callback(None, "Error while reading file.", None, *args)
            return

        req = self._create_async_request(art_url, cancellable, callback,
                                            Priority.HIGH)

        req.put(mtype, image_data, *args)

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

    def get_track_url(self, track_id):
        return Euterpe.build_url(
            self._remote_address,
            ENDPOINT_FILE.format(track_id),
        )


class JSONBodyCallback:
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


class TokenExpirationCallback:
    '''
    An http.Request callback which will wrap the passed callback
    and emit token expire event on 401 HTTP status codes and use
    src_obj as the event source.
    '''

    def __init__(self, src_obj, callback):
        self._callback = callback
        self._src_obj = src_obj

    def __call__(self, status, *args, **kwargs):
        if status == 401 and self._src_obj.get_token() is not None:
            emit_signal(self._src_obj, SIGNAL_TOKEN_EXPIRED)

        self._callback(status, *args, **kwargs)


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
ENDPOINT_PLAYLISTS = "/v1/playlists"
ENDPOINT_PLAYLIST = "/v1/playlist/{:d}"
