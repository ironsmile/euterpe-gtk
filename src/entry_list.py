# entry_list.py
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
from .entry import EuterpeEntry
from functools import partial


SIGNAL_TRACK_CLICKED = "track-clicked"


@Gtk.Template(resource_path='/com/doycho/euterpe/gtk/ui/entry-list.ui')
class EuterpeEntryList(Gtk.ScrolledWindow):
    __gtype_name__ = 'EuterpeEntryList'

    __gsignals__ = {
        SIGNAL_TRACK_CLICKED: (GObject.SignalFlags.RUN_FIRST, None, (int,)),
    }

    entry_container = Gtk.Template.Child()

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._songs = []
        self._current_song = None

    def add(self, song):
        if not isinstance(song, dict):
            raise ValueError("only songs allowed to be added")
        song_widget = EuterpeEntry(song)
        self._songs.append(song_widget)
        song_index = len(self._songs) - 1
        song_widget.connect(
            "clicked",
            partial(self._on_track_clicked, song_index)
        )

        self.entry_container.add(song_widget)

    def truncate(self):
        self._songs = []
        self._current_song = None
        for child in self.entry_container.get_children():
            child.destroy()

    def set_currently_playing(self, index):
        if self._current_song is not None:
            self._current_song.set_relief(Gtk.ReliefStyle.NONE)
            self._current_song = None

        if index is None:
            return

        if len(self._songs) == 0 or index < 0 or index >= len(self._songs):
            return

        song_widget = self._songs[index]
        self._current_song = song_widget
        song_widget.set_relief(Gtk.ReliefStyle.NORMAL)
        self.scroll_to(song_widget)

    def _on_track_clicked(self, index, *args):
        emit_signal(self, SIGNAL_TRACK_CLICKED, index)

    def scroll_to(self, widget):
        vadj = self.get_vadjustment()
        coords = widget.translate_coordinates(self, 0, 0)
        if coords is None:
            return
        x, y = coords
        vadj.set_value(min(y, vadj.get_upper()))
