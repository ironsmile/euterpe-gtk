# box_artist.py
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


@Gtk.Template(resource_path='/com/doycho/euterpe/gtk/ui/box-artist.ui')
class EuterpeBoxArtist(Gtk.Viewport):
    __gtype_name__ = 'EuterpeBoxArtist'

    __gsignals__ = {
        SIGNAL_CLICKED: (GObject.SignalFlags.RUN_FIRST, None, ()),
    }

    name = Gtk.Template.Child()
    image = Gtk.Template.Child()
    button = Gtk.Template.Child()

    def __init__(self, artist, **kwargs):
        super().__init__(**kwargs)

        self._artist = artist
        self.name.set_label(artist.get("artist", "<N/A>"))

        self.button.connect("clicked", self._on_click)
        self._init_artwork(artist)
        self.connect("destroy", self._on_destroy)

    def _init_artwork(self, artist):
        artist_id = artist.get("artist_id", None)
        if artist_id is None:
            log.warning("EuterpeBoxArtist: no artist ID found for {}", artist)
            return

        self._artwork_loader = AsyncArtwork(self.image, 120)
        self._artwork_loader.load_artist_image(artist_id)

    def _on_click(self, pb):
        emit_signal(self, SIGNAL_CLICKED)

    def _on_destroy(self, *args):
        self._artwork_loader.cancel()

    def get_artist(self):
        return self._artist.copy()
