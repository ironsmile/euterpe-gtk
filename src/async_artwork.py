# async_artwork.py
#
# Copyright 2022 Doychin Atanasov
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

from gi.repository import Gio
from gi.repository.GdkPixbuf import Pixbuf
from euterpe_gtk.service import ArtworkSize
import euterpe_gtk.log as log


class AsyncArtwork(object):

    def __init__(self, gtk_image, size):
        app = Gio.Application.get_default()
        if app is None:
            raise Exception("There is no default application")

        self._euterpe = app.get_euterpe()
        self._image = gtk_image
        self._size = size
        self._previous_request = None
        self._default_icon = gtk_image.get_icon_name()
        self._displayed_artwork_id = None

    def load_album_image(self, album_id, size=ArtworkSize.FULL, force = False):
        if force != True and self._displayed_artwork_id == album_id:
            return

        if self._previous_request is not None:
            self._previous_request.cancel()

        self._set_default_artwork()

        cancellable = Gio.Cancellable.new()
        self._previous_request = cancellable
        self._euterpe.get_album_artwork(
            album_id,
            size,
            cancellable,
            self._change_artwork,
            album_id,
        )

    def load_artist_image(self, artist_id, size=ArtworkSize.FULL):
        if self._displayed_artwork_id == artist_id:
            return

        if self._previous_request is not None:
            self._previous_request.cancel()

        self._set_default_artwork()

        cancellable = Gio.Cancellable.new()
        self._previous_request = cancellable
        self._euterpe.get_artist_artwork(
            artist_id,
            size,
            cancellable,
            self._change_artwork,
            artist_id,
        )

    def _change_artwork(self, status, body_stream, cancel, artwork_id):
        if status is None and body_stream is None:
            self._set_default_artwork()
            return

        if status is None or status != 200:
            # It is quite normal for artworks to be missing. So make sure not to log
            # any messages for status 404.
            if status != 404:
                log.debug("_change_artwork: artwork response code: {}, id: {}",
                        status, artwork_id)
            self._set_default_artwork()
            return

        if body_stream is None:
            log.debug("_change_artwork: body_stream was None, id {}", artwork_id)
            self._set_default_artwork()
            return

        Pixbuf.new_from_stream_at_scale_async(body_stream, self._size, self._size,
            True, cancel, self._on_artwork_pixbuf_ready, artwork_id)

    def _on_artwork_pixbuf_ready(self, obj, res, artwork_id):
        pb = Pixbuf.new_from_stream_finish(res)
        
        if pb is None:
            log.debug("_on_artwork_pixbuf_ready: pix buffer was None, id {}", artwork_id)
            self._set_default_artwork()
            return

        self._displayed_artwork_id = artwork_id
        self._image.set_from_pixbuf(pb)

    def _set_default_artwork(self):
        self._image.set_from_icon_name(*self._default_icon)

    def cancel(self):
        if self._previous_request is None:
            return

        self._previous_request.cancel()
        self._previous_request = None
