# small_album.py
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
from .utils import emit_signal


BUTTON_NEXT_CLICKED = "button-next-clicked"


@Gtk.Template(resource_path='/com/doycho/euterpe/gtk/ui/small-album.ui')
class EuterpeSmallAlbum(Gtk.Viewport):
    __gtype_name__ = 'EuterpeSmallAlbum'

    __gsignals__ = {
        BUTTON_NEXT_CLICKED: (GObject.SignalFlags.RUN_FIRST, None, ()),
    }

    album_name = Gtk.Template.Child()
    artist_name = Gtk.Template.Child()
    album_open_button = Gtk.Template.Child()

    def __init__(self, album, **kwargs):
        super().__init__(**kwargs)

        self._album = album
        self.album_name.set_label(album.get("album", "<N/A>"))
        self.artist_name.set_label(album.get("artist", "<N/A>"))

        self.album_open_button.connect("clicked", self._on_next_button)

    def _on_next_button(self, pb):
        emit_signal(self, BUTTON_NEXT_CLICKED)

    def get_album(self):
        return self._album.copy()
