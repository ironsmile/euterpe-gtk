# small_playlist.py
#
# Copyright 2025 Doychin Atanasov
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
from euterpe_gtk.utils import emit_signal, format_duration


BUTTON_NEXT_CLICKED = "button-next-clicked"


@Gtk.Template(resource_path='/com/doycho/euterpe/gtk/ui/small-playlist.ui')
class EuterpeSmallPlaylist(Gtk.Viewport):
    __gtype_name__ = 'EuterpeSmallPlaylist'

    __gsignals__ = {
        BUTTON_NEXT_CLICKED: (GObject.SignalFlags.RUN_FIRST, None, ()),
    }

    playlist_name = Gtk.Template.Child()
    playlist_desc = Gtk.Template.Child()
    secondary_info = Gtk.Template.Child()
    playlist_open_button = Gtk.Template.Child()

    def __init__(self, playlist, **kwargs):
        super().__init__(**kwargs)

        self._playlist = playlist
        self.playlist_name.set_label(playlist.get("name", "<Unnamed>"))
        self.playlist_desc.set_label(playlist.get("description", ""))
        self.secondary_info.set_label(self._get_tracks_info())

        self.playlist_open_button.connect("clicked", self._on_next_button)

    def _on_next_button(self, pb):
        emit_signal(self, BUTTON_NEXT_CLICKED)

    def get_playlist(self):
        return self._playlist.copy()

    def _format_duration(self, ms):
        if ms is not None:
            return format_duration(ms)
        return "unknown duration"

    def _get_tracks_info(self):
        tracks_count = self._playlist.get("tracks_count", 0)
        tracks_info = "--"
        if tracks_count == 1:
            tracks_info = "single song"
        elif tracks_count > 1:
            tracks_info = "{} songs".format(tracks_count)

        if tracks_count != 0:
            tracks_info = "{}, {}".format(
                tracks_info,
                self._format_duration(self._playlist.get("duration", None)),
            )

        return tracks_info
