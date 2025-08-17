# playlist.py
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
from euterpe_gtk.widgets.track import EuterpeTrack, PLAY_BUTTON_CLICKED, APPEND_BUTTON_CLICKED
from euterpe_gtk.utils import emit_signal, format_duration
from euterpe_gtk.widgets.playlist_delete_confirm import PlaylistDeleteConfirm


SIGNAL_PLAYLIST_DELETED = "playlist-deleted"


@Gtk.Template(resource_path='/com/doycho/euterpe/gtk/ui/playlist.ui')
class EuterpePlaylist(Gtk.Viewport):
    __gtype_name__ = 'EuterpePlaylist'

    __gsignals__ = {
        SIGNAL_PLAYLIST_DELETED: (GObject.SignalFlags.RUN_FIRST, None, ()),
    }

    playlist_name = Gtk.Template.Child()
    description = Gtk.Template.Child()
    info = Gtk.Template.Child()

    track_list = Gtk.Template.Child()
    play_button = Gtk.Template.Child()
    more_button = Gtk.Template.Child()
    loading_spinner = Gtk.Template.Child()

    play_button = Gtk.Template.Child()
    append_to_queue = Gtk.Template.Child()
    delete_playlist = Gtk.Template.Child()

    def __init__(self, playlist, win, **kwargs):
        super().__init__(**kwargs)

        self._win = win
        self._playlist = playlist
        self._playlist_tracks = []

        self.playlist_name.set_label(playlist.get("name", "<Unnamed>"))

        descr = playlist.get("description", None)
        if descr is None or descr == "":
            self.description.hide()
        else:
            self.description.set_label(descr)

        self.playlist_name.set_label(playlist.get("name", "<Unnamed>"))
        self.info.set_label(self._get_tracks_info())

        self.play_button.connect(
            "clicked",
            self._on_play_button
        )
        self.append_to_queue.connect(
            "clicked",
            self._on_append_button
        )
        self.delete_playlist.connect(
            "clicked",
            self._on_delete_button
        )

        self._disable_actions_on_spinner(self.loading_spinner)
        self.connect("unrealize", self._on_unrealize)
        win.get_euterpe().get_playlist(playlist["id"], self._on_playlist_result)

    def on_track_play_clicked(self, track_widget):
        track = track_widget.get_track()
        player = self._win.get_player()
        player.set_playlist([track])
        player.play()

    def on_track_append_clicked(self, track_widget):
        track = track_widget.get_track()
        player = self._win.get_player()
        player.append_to_playlist([track])

    def show_notification(self, text):
        self._win.show_notification(text)

    def _on_play_button(self, pb):
        player = self._win.get_player()
        player.set_playlist(self._playlist_tracks)
        player.play()

    def _on_append_button(self, ab):
        player = self._win.get_player()
        player.append_to_playlist(self._playlist_tracks)
        self.show_notification("Playlist songs appended to the queue.")

    def _on_delete_button(self, db):
        delete_widget = PlaylistDeleteConfirm()

        delete_widget.connect(
            "response",
            self._on_delete_confirm_response
        )
        delete_widget.set_transient_for(self._win)
        delete_widget.show_all()

    def _on_delete_confirm_response(self, dialog, response_id):
        if response_id == Gtk.ResponseType.DELETE_EVENT:
            return

        if response_id == Gtk.ResponseType.ACCEPT:
            self.track_list.foreach(self.track_list.remove)
            spinner = Gtk.Spinner()
            spinner.set_halign(Gtk.Align.FILL)
            spinner.set_valign(Gtk.Align.FILL)
            self._disable_actions_on_spinner(spinner)
            self.track_list.pack_start(spinner, True, True, 0)
            spinner.show()
            spinner.start()

            self._win.get_euterpe().delete_playlist(
                self._playlist["id"],
                self._on_delete_response,
            )

        dialog.destroy()

    def _on_delete_response(self, status, body):
        if status != 204:
            self.track_list.foreach(self.track_list.remove)
            self._show_error(
                "Error removing a playlist. HTTP response code {}.".format(
                    status
                )
            )
            return

        self.show_notification("Playlist removed.")
        emit_signal(self, SIGNAL_PLAYLIST_DELETED)

    def _disable_actions_on_spinner(self, spinner):
        for obj in [self.play_button, self.more_button]:
            spinner.bind_property(
                'active',
                obj, 'sensitive',
                GObject.BindingFlags.INVERT_BOOLEAN
            )

    def _get_tracks_info(self):
        tracks_count = self._playlist.get("tracks_count", 0)
        tracks_info = "no songs"
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

    def _format_duration(self, ms):
        if ms is not None:
            return format_duration(ms)
        return "unknown duration"

    def _on_unrealize(self, *args):
        for child in self.track_list.get_children():
            child.destroy()

    def _on_playlist_result(self, status, body):
        self.track_list.foreach(self.track_list.remove)

        if status != 200:
            self._show_error(
                "Error getting playlist. HTTP response code {}.".format(
                    status
                )
            )
            return

        playlist_tracks = []
        for track in body.get("tracks", []):
            playlist_tracks.append(track)

        if len(playlist_tracks) == 0:
            label = Gtk.Label.new()
            label.set_text("No songs found.")
            self.track_list.add(label)
            label.show()
            return

        self._playlist_tracks = playlist_tracks

        for track in self._playlist_tracks:
            tr_obj = EuterpeTrack(track)
            self.track_list.add(tr_obj)
            tr_obj.connect(PLAY_BUTTON_CLICKED, self.on_track_play_clicked)
            tr_obj.connect(APPEND_BUTTON_CLICKED, self.on_track_append_clicked)
            while (Gtk.events_pending()):
                Gtk.main_iteration()

    def _show_error(self, text):
        label = Gtk.Label.new()
        label.set_text(text)
        self.track_list.pack_start(label, True, True, 0)
        label.show()
