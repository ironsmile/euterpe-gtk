# mini_player.py
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

from gi.repository import GObject, Gtk, GLib
from euterpe_gtk.utils import emit_signal
import euterpe_gtk.log as log

SIGNAL_PAN_UP = "pan-up"


@Gtk.Template(resource_path='/com/doycho/euterpe/gtk/ui/mini-player.ui')
class EuterpeMiniPlayer(Gtk.Viewport):
    __gtype_name__ = 'EuterpeMiniPlayer'

    __gsignals__ = {
        SIGNAL_PAN_UP: (GObject.SignalFlags.RUN_FIRST, None, ()),
    }

    play_pause_button = Gtk.Template.Child()
    track_name = Gtk.Template.Child()
    artist_name = Gtk.Template.Child()
    track_progess = Gtk.Template.Child()
    play_button_icon = Gtk.Template.Child()
    pause_button_icon = Gtk.Template.Child()
    show_big_player_button = Gtk.Template.Child()

    def __init__(self, player, **kwargs):
        super().__init__(**kwargs)

        self._player = player
        # _player_signals is mapping between signal name and signal ID connected
        # for self._player.
        self._player_signals = {}

        self.show_big_player_button.connect(
            "clicked",
            self.on_show_big_player_clicked
        )
        self._first_state_changed_signal = player.connect(
            "state-changed",
            self.on_first_player_state_change
        )
        self.connect(
            "map",
            self.on_mapped
        )
        self.connect(
            "unmap",
            self.on_unmapped
        )

    def on_first_player_state_change(self, player):
        '''
            This signal handler is ran only up to the first state change when the
            player is active. It shows the widget and then disconnects itself.
        '''
        if player is not self._player:
            return

        if not player.is_active():
            return

        self.show()
        if self._first_state_changed_signal is not None:
            player.handler_disconnect(self._first_state_changed_signal)
            self._first_state_changed_signal = None

    def on_player_state_changed(self, player):
        if player is not self._player:
            return

        if player.is_playing():
            self.play_pause_button.set_image(self.pause_button_icon)
        else:
            self.play_pause_button.set_image(self.play_button_icon)

        if player.has_ended():
            self.change_progress(0)

    def on_track_progress_changed(self, player, progress):
        self.change_progress(progress)

    def on_track_changed(self, player):
        track = player.get_track_info()
        if track is None:
            return

        self.track_name.set_label(track.get("title", "n/a"))
        self.artist_name.set_label(track.get("artist", "n/a"))

    def change_progress(self, prog):
        if prog < 0:
            prog = 0
        if prog > 1:
            prog = 1
        self.track_progess.set_fraction(prog)

    def on_show_big_player_clicked(self, btn):
        emit_signal(self, SIGNAL_PAN_UP)

    def on_mapped(self, *args):
        log.debug("mini player mapped")

        self._connect_player_handler(
            "progress",
            self.on_track_progress_changed,
            self._set_current_progress
        )
        self._connect_player_handler(
            "track-changed",
            self.on_track_changed,
            self.on_track_changed
        )
        self._connect_player_handler(
            "state-changed",
            self.on_player_state_changed,
            self.on_player_state_changed
        )

    def on_unmapped(self, *args):
        log.debug("mini player unmapped")

        self._disconnect_player_handler("state-changed")
        self._disconnect_player_handler("progress")
        self._disconnect_player_handler("track-changed")

    def _disconnect_player_handler(self, name):
        signal_id = self._player_signals.get(name, None)
        if signal_id is None:
            return
        self._player.handler_disconnect(signal_id)
        self._player_signals[name] = None

    def _connect_player_handler(self, name, handler, restore_state):
        '''
        This method connects a handler to the named signal of the self._player.

        First, it make sure that the player signal with name `name` is disconnected.
        Then it schedules `restore_state` to be ran with self._player. And only
        then connects the signal to the handler.
        '''
        self._disconnect_player_handler(name)
        GLib.idle_add(restore_state, self._player)
        signal_id = self._player.connect(name, handler)
        self._player_signals[name] = signal_id

    def _set_current_progress(self, player):
        progress = player.get_progress()
        if progress is not None:
            self.change_progress(progress)
