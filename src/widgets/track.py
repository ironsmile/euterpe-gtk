# track.py
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

from gi.repository import GObject, Gtk, Gio
from euterpe_gtk.utils import emit_signal, format_duration
from euterpe_gtk.widgets.add_to_playlist import AddToPlaylist


PLAY_BUTTON_CLICKED = "play-button-clicked"
APPEND_BUTTON_CLICKED = "append-button-clicked"


@Gtk.Template(resource_path='/com/doycho/euterpe/gtk/ui/track.ui')
class EuterpeTrack(Gtk.Viewport):
    __gtype_name__ = 'EuterpeTrack'

    __gsignals__ = {
        PLAY_BUTTON_CLICKED: (GObject.SignalFlags.RUN_FIRST, None, ()),
        APPEND_BUTTON_CLICKED: (GObject.SignalFlags.RUN_FIRST, None, ()),
    }

    track_name = Gtk.Template.Child()
    track_info = Gtk.Template.Child()
    track_play_button = Gtk.Template.Child()
    track_append_button = Gtk.Template.Child()
    track_duration = Gtk.Template.Child()
    secondary_info = Gtk.Template.Child()
    track_append_to_playlist = Gtk.Template.Child()

    def __init__(self, track, **kwargs):
        super().__init__(**kwargs)

        app = Gio.Application.get_default()
        if app is None:
            raise Exception("There is no default application")

        self._app = app

        self._track = track
        self.track_name.set_label(track.get("title", "<N/A>"))
        self.track_info.set_label("{}, {}".format(
            self._track.get("artist", "<N/A>"),
            self._track.get("album", "<N/A>"),
        ))
        self._set_seconday_info()
        ms = track.get("duration", None)
        self._set_duration(ms)

        self.track_play_button.connect("clicked", self._on_play_button)
        self.track_append_button.connect("clicked", self._on_append_button)
        self.track_append_to_playlist.connect("clicked", self._on_add_playlist_button)

    def _set_duration(self, ms):
        duration = "n/a"
        if ms is not None:
            duration = format_duration(ms)
        self.track_duration.set_label(duration)

    def _set_seconday_info(self):
        if "bitrate" in self._track:
            self.secondary_info.set_label(" {:d} kbps".format(
                int(self._track["bitrate"] / 1024)
            ))
            self.secondary_info.set_tooltip_text(
                self._track.get("format", "format unknown")
            )
        elif "format" in self._track:
            self.secondary_info.set_label(self._track["format"])
        else:
            self.secondary_info.set_label("")

    def _on_play_button(self, pb):
        emit_signal(self, PLAY_BUTTON_CLICKED)

    def _on_append_button(self, pb):
        emit_signal(self, APPEND_BUTTON_CLICKED)

    def _on_add_playlist_button(self, btn):
        add_widget = AddToPlaylist([self._track])
        add_widget.set_transient_for(self._app.props.active_window)
        add_widget.set_default_size(300,600)
        add_widget.show_all()

    def get_track(self):
        return self._track.copy()
