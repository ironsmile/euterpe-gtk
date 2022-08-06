# player_ui.py
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
from gi.repository.GdkPixbuf import Pixbuf
from .entry_list import EuterpeEntryList
from .utils import emit_signal, format_duration
from .player import Repeat, Shuffle


SIGNAL_PAN_DOWN = "pan-down"


@Gtk.Template(resource_path='/com/doycho/euterpe/gtk/ui/player.ui')
class EuterpePlayerUI(Gtk.Viewport):
    __gtype_name__ = 'EuterpePlayerUI'

    __gsignals__ = {
        SIGNAL_PAN_DOWN: (GObject.SignalFlags.RUN_FIRST, None, ()),
    }

    play_pause_button = Gtk.Template.Child()
    shuffle_button = Gtk.Template.Child()
    prev_button = Gtk.Template.Child()
    next_button = Gtk.Template.Child()
    repeat_button = Gtk.Template.Child()
    share_button = Gtk.Template.Child()
    add_button = Gtk.Template.Child()
    track_progess = Gtk.Template.Child()
    pan_down_button = Gtk.Template.Child()
    playlist = Gtk.Template.Child()

    time_elapsed = Gtk.Template.Child()
    time_left = Gtk.Template.Child()

    play_icon = Gtk.Template.Child()
    pause_icon = Gtk.Template.Child()

    repeat_icon = Gtk.Template.Child()
    repeat_song_icon = Gtk.Template.Child()

    track_name = Gtk.Template.Child()
    artist_name = Gtk.Template.Child()

    main_leaflet = Gtk.Template.Child()
    view_playlist_button = Gtk.Template.Child()
    big_player = Gtk.Template.Child()
    play_queue = Gtk.Template.Child()

    artwork = Gtk.Template.Child()

    def __init__(self, euterpe, **kwargs):
        super().__init__(**kwargs)

        self._euterpe = euterpe
        self._player = None
        self._track_len = None
        self._entry_list = EuterpeEntryList()
        self.playlist.add(self._entry_list)

        self.track_progess.set_range(0, 1)

        self.pan_down_button.connect(
            "clicked",
            self._on_pan_down
        )

        self.track_progess.connect(
            "change-value",
            self._on_seek
        )

        self._entry_list.connect(
            "track-clicked",
            self._on_track_clicked
        )

        self.main_leaflet.bind_property(
            'folded',
            self.view_playlist_button, 'visible',
            GObject.BindingFlags.SYNC_CREATE
        )

        self.view_playlist_button.connect(
            "clicked",
            self._on_show_playlist_clicked
        )

        self._artwork_size = 200
        self._default_artwork_icon = self.artwork.get_icon_name()
        self._cancel_artwork_request = None
        self._displayed_artwork_id = None

    def _on_pan_down(self, *args):
        emit_signal(self, SIGNAL_PAN_DOWN)

    def get_pan_down_button(self):
        return self.pan_down_button

    def set_player(self, player):
        self._player = player

        self._player.connect(
            "state-changed",
            self.on_player_state_changed
        )
        self._player.connect(
            "progress",
            self.on_track_progress_changed
        )
        self._player.connect(
            "track-changed",
            self.on_track_changed
        )
        self._player.connect(
            "playlist-changed",
            self.on_player_playlist_changed
        )
        self._player.connect(
            "repeat-changed",
            self.on_repeat_changed
        )
        self._player.connect(
            "shuffle-changed",
            self.on_shuffle_changed
        )

    def on_track_progress_changed(self, player, prog):
        self.change_progress(prog)

    def change_progress(self, prog):
        if prog < 0:
            prog = 0
        if prog > 1:
            prog = 1
        self.track_progess.set_value(prog)

        elapsed = "--:--"
        remainig = "--:--"

        if self._track_len is not None:
            elapsed = format_duration(prog * self._track_len)
            remainig = '-{}'.format(
                format_duration((1 - prog) * self._track_len)
            )

        self.time_elapsed.set_label(elapsed)
        self.time_left.set_label(remainig)

    def on_player_state_changed(self, player):
        if player is not self._player:
            return

        if player.is_active():
            self.track_progess.set_sensitive(True)
            self.play_pause_button.set_sensitive(True)
            self.next_button.set_sensitive(player.has_next())
            self.prev_button.set_sensitive(player.has_previous())

        if player.is_playing():
            self.play_pause_button.set_image(self.pause_icon)
        else:
            self.play_pause_button.set_image(self.play_icon)

        if player.has_ended():
            self.show_nothing_playing()
            self.change_progress(0)

    def on_player_playlist_changed(self, player):
        if player is not self._player:
            return

        self._entry_list.truncate()
        songs = player.get_playlist()
        for song in songs:
            self._entry_list.add(song)
            while (Gtk.events_pending()):
                Gtk.main_iteration()

        track_index = player.get_track_index()
        self._entry_list.set_currently_playing(track_index)

    def show_nothing_playing(self):
        self.track_name.set_label("Not Playing")
        self.artist_name.set_label("--")
        self.track_progess.set_sensitive(False)
        self._track_len = None

    def on_track_changed(self, player):
        track = player.get_track_info()
        if track is None:
            return

        self.track_name.set_label(track.get("title", "n/a"))
        self.artist_name.set_label(track.get("artist", "n/a"))
        self._track_len = track.get("duration", None)

        track_index = player.get_track_index()
        self._entry_list.set_currently_playing(track_index)

        self._request_artwork_image(track)

    def _request_artwork_image(self, track):
        album_id = track.get("album_id", None)
        if album_id is None:
            print("_request_artwork_image: track has no album_id")
            return

        if self._displayed_artwork_id == album_id:
            return

        if self._cancel_artwork_request is not None:
            self._cancel_artwork_request.cancel()

        self._set_default_artwork()

        cancellable = Gio.Cancellable.new()
        self._cancel_artwork_request = cancellable
        self._euterpe.get_album_artwork(
            album_id,
            cancellable,
            self._change_artwork,
            album_id,
        )

    def _change_artwork(self, status, body_stream, cancel, album_id):
        if status is None or status != 200:
            print("_change_artwork: artwork response code: {}".format(status))
            self._set_default_artwork()
            return

        if body_stream is None:
            print("_change_artwork: body_stream was None")
            self._set_default_artwork()
            return

        size = self._artwork_size
        pb = Pixbuf.new_from_stream_at_scale(body_stream, -1, size, True, cancel)
        if pb is None:
            print("_change_artwork: pix buffer was None")
            self._set_default_artwork()
            return

        self._displayed_artwork_id = album_id
        self.artwork.set_from_pixbuf(pb)

    def _set_default_artwork(self):
        self.artwork.set_from_icon_name(*self._default_artwork_icon)

    def on_repeat_changed(self, player):
        repeat = player.get_repeat()
        active = repeat != Repeat.NONE

        act_name = self.repeat_button.get_action_name()
        self.repeat_button.set_action_name(None)
        self.repeat_button.props.active = active
        self.repeat_button.set_action_name(act_name)

        if repeat == Repeat.SONG:
            self.repeat_button.set_image(self.repeat_song_icon)
        else:
            self.repeat_button.set_image(self.repeat_icon)

        self.next_button.set_sensitive(player.has_next())
        self.prev_button.set_sensitive(player.has_previous())

    def on_shuffle_changed(self, player):
        active = player.get_shuffle() != Shuffle.NONE

        act_name = self.shuffle_button.get_action_name()
        self.shuffle_button.set_action_name(None)
        self.shuffle_button.props.active = active
        self.shuffle_button.set_action_name(act_name)

        self.next_button.set_sensitive(player.has_next())
        self.prev_button.set_sensitive(player.has_previous())

    def _on_seek(self, slider, scroll, value):
        if scroll != Gtk.ScrollType.JUMP:
            return False

        if self._player is None:
            return

        self._player.seek(value)
        return False

    def _on_track_clicked(self, entry_list, index):
        if not isinstance(index, int):
            print("track index was not an integer: {}".format(index))
            return

        self._player.play_index(index)

    def _on_show_playlist_clicked(self, btn):
        is_active = btn.get_active()

        to_show = self.big_player
        if is_active:
            to_show = self.play_queue

        self.main_leaflet.set_visible_child(to_show)
