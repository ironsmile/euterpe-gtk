# box_album.py
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

from gi.repository import GObject, Gtk
from euterpe_gtk.utils import emit_signal
from euterpe_gtk.async_artwork import AsyncArtwork
import euterpe_gtk.log as log


SIGNAL_CLICKED = "clicked"


@Gtk.Template(resource_path='/com/doycho/euterpe/gtk/ui/box-album.ui')
class EuterpeBoxAlbum(Gtk.Viewport):
    __gtype_name__ = 'EuterpeBoxAlbum'

    __gsignals__ = {
        SIGNAL_CLICKED: (GObject.SignalFlags.RUN_FIRST, None, ()),
    }

    name = Gtk.Template.Child()
    artist = Gtk.Template.Child()
    image = Gtk.Template.Child()
    button = Gtk.Template.Child()

    def __init__(self, album, **kwargs):
        super().__init__(**kwargs)

        self._album = album
        self.name.set_label(album.get("album", "<N/A>"))
        self.artist.set_label(album.get("artist", "<N/A>"))

        self.button.connect("clicked", self._on_click)
        self._init_artwork(album)
        self.connect("destroy", self._on_destroy)

    def _init_artwork(self, album):
        album_id = album.get("album_id", None)
        if album_id is None:
            log.warning("EuterpeBoxAlbum: no album ID found for {}", album)
            return

        self._artwork_loader = AsyncArtwork(self.image, 150)
        self._artwork_loader.load_album_image(album_id)

    def _on_click(self, pb):
        emit_signal(self, SIGNAL_CLICKED)

    def _on_destroy(self, *args):
        self._artwork_loader.cancel()

    def get_album(self):
        return self._album.copy()
