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

from gi.repository import GObject, Gtk, Gio, Handy
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

    tracks_clamp = Gtk.Template.Child()
    track_list = Gtk.Template.Child()
    play_button = Gtk.Template.Child()
    more_button = Gtk.Template.Child()
    loading_spinner = Gtk.Template.Child()

    play_button = Gtk.Template.Child()
    append_to_queue = Gtk.Template.Child()
    delete_playlist = Gtk.Template.Child()
    edit_playlist = Gtk.Template.Child()
    done_editing_button = Gtk.Template.Child()
    remove_selected_button = Gtk.Template.Child()

    def __init__(self, playlist, **kwargs):
        super().__init__(**kwargs)

        app = Gio.Application.get_default()
        if app is None:
            raise Exception("There is no default application")

        self._app = app

        self._win = app.props.active_window
        self._playlist = playlist
        self._playlist_tracks = []

        self._refresh_playlist_info()

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
        self.edit_playlist.connect(
            "clicked",
            self._on_edit_button
        )
        self.done_editing_button.connect(
            "clicked",
            self._on_edit_done_button
        )
        self.remove_selected_button.connect(
            "clicked",
            self._on_remove_selected_button
        )

        self.loading_spinner.bind_property(
            'active',
            self.tracks_clamp, 'visible',
            GObject.BindingFlags.INVERT_BOOLEAN
        )

        self._disable_actions_on_spinner(self.loading_spinner)
        self.connect("realize", self._on_realize)
        self.connect("unrealize", self._on_unrealize)

    def _refresh_playlist_info(self):
        self.playlist_name.set_label(self._playlist.get("name", "<Unnamed>"))
        descr = self._playlist.get("description", None)
        if descr is None or descr == "":
            self.description.hide()
        else:
            self.description.set_label(descr)

        self.playlist_name.set_label(self._playlist.get("name", "<Unnamed>"))
        self._set_tracks_info()

    def _on_realize(self, widget):
        self.tracks_clamp.set_visible(False)
        self._win.get_euterpe().get_playlist(self._playlist["id"], self._on_playlist_result)

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
            self._show_spinner()

            self._win.get_euterpe().delete_playlist(
                self._playlist["id"],
                self._on_delete_response,
            )

        dialog.destroy()

    def _on_delete_response(self, status, body):
        if status != 204:
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

    def _set_tracks_info(self):
        tracks_count = self._playlist.get("tracks_count", 0)
        if tracks_count == 0:
            self.info.hide()
            return

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

        self.info.set_label(tracks_info)
        self.info.show()

    def _format_duration(self, ms):
        if ms is not None:
            return format_duration(ms)
        return "unknown duration"

    def _on_unrealize(self, *args):
        for child in self.track_list.get_children():
            child.destroy()

    def _on_playlist_result(self, status, body):
        self.track_list.foreach(self.track_list.remove)
        self._hide_spinner()

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

        self._playlist = body
        if "tracks" in self._playlist:
            del(self._playlist["tracks"])
        self._refresh_playlist_info()

        if len(playlist_tracks) == 0:
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
        #!TODO: change this so that it does not use "pack_start"
        label = Gtk.Label.new()
        label.set_text(text)
        self.track_list.pack_start(label, True, True, 0)
        label.show()

    def _on_edit_button(self, btn):
        self.enter_edit_mode()

    def _on_edit_done_button(self, btn):
        self.exit_edit_mode()

    def _show_spinner(self):
        self.loading_spinner.set_visible(True)
        self.loading_spinner.start()

    def _hide_spinner(self):
        self.loading_spinner.set_visible(False)
        self.loading_spinner.stop()

    def _on_remove_selected_button(self, btn):
        selected = self.track_list.get_selected_rows()
        if len(selected) < 1:
            return

        self._show_spinner()
        selected_indx = [r.get_index() for r in selected]
        self._app.get_euterpe().change_playlist(
            self._playlist["id"],
            self._on_playlist_changed,
            remove_indeces=selected_indx,
        )

    def _on_playlist_changed(self, status, body):
        if status < 200 or status >= 300:
            self._show_error("HTTP response code {}.".format(status))
            return

        self._win.get_euterpe().get_playlist(self._playlist["id"], self._on_playlist_result)

    def enter_edit_mode(self):
        self.play_button.set_visible(False)
        self.more_button.set_visible(False)
        self.done_editing_button.set_visible(True)
        self.remove_selected_button.set_visible(True)
        self.track_list.set_selection_mode(Gtk.SelectionMode.MULTIPLE)

    def exit_edit_mode(self):
        self.play_button.set_visible(True)
        self.more_button.set_visible(True)
        self.done_editing_button.set_visible(False)
        self.remove_selected_button.set_visible(False)
        self.track_list.set_selection_mode(Gtk.SelectionMode.NONE)
