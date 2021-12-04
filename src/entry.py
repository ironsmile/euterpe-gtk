# entry.py
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
from .utils import emit_signal, format_duration


SIGNAL_CLICKED = "clicked"


@Gtk.Template(resource_path='/com/doycho/euterpe/gtk/ui/entry.ui')
class EuterpeEntry(Gtk.Viewport):
    __gtype_name__ = 'EuterpeEntry'

    __gsignals__ = {
        SIGNAL_CLICKED: (GObject.SignalFlags.RUN_FIRST, None, ()),
    }

    title = Gtk.Template.Child()
    track_info = Gtk.Template.Child()
    time = Gtk.Template.Child()

    button = Gtk.Template.Child()

    def __init__(self, song, **kwargs):
        super().__init__(**kwargs)

        title = song.get("title", None)
        if title is not None:
            self.title.set_label(title)

        track_info = []

        artist = song.get("artist", None)
        if artist is not None:
            track_info.append(artist)

        album = song.get("album", None)
        if album is not None:
            track_info.append(album)

        self.track_info.set_label(", ".join(track_info))

        duration = song.get("duration", None)
        if duration is not None:
            self.time.set_label(format_duration(duration))

        self.button.connect("clicked", self._on_button_clicked)

    def set_relief(self, relief):
        self.button.set_relief(relief)

    def _on_button_clicked(self, *args):
        emit_signal(self, SIGNAL_CLICKED)
