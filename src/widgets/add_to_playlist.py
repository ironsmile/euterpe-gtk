# add_to_playlist.py
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

import re

from gi.repository import Gtk, Gio, GObject, Pango
import euterpe_gtk.log as log

@Gtk.Template(resource_path='/com/doycho/euterpe/gtk/ui/add-to-playlist.ui')
class AddToPlaylist(Gtk.Dialog):
    __gtype_name__ = 'AddToPlaylist'

    loading_spinner = Gtk.Template.Child()
    list_with_playlists = Gtk.Template.Child()
    playlist_filter = Gtk.Template.Child()
    add_button = Gtk.Template.Child()
    cancel_button = Gtk.Template.Child()
    status_page = Gtk.Template.Child()

    def __init__(self, tracks, **kwargs):
        super().__init__(**kwargs)

        self._tracks = tracks

        app = Gio.Application.get_default()
        if app is None:
            raise Exception("There is no default application")

        self._app = app
        self._euterpe = app.get_euterpe()

        self.connect("response",self._on_response)
        self.connect("realize", self._on_realize)

        self.cancel_button.connect("clicked", self._on_cancel)
        self.loading_spinner.bind_property(
            'active',
            self.list_with_playlists, 'visible',
            GObject.BindingFlags.INVERT_BOOLEAN
        )

        self.loading_spinner.bind_property(
            'active',
            self.playlist_filter, 'sensitive',
            GObject.BindingFlags.INVERT_BOOLEAN
        )

        self.list_with_playlists.set_filter_func(self._filter_func)
        self.playlist_filter.connect("changed", self._on_filter_changed)
        self.list_with_playlists.connect("row-selected", self._on_selection_change)
        self.add_button.connect("clicked", self._on_added_to_playlist)

    def _on_response(self, dialog, response_id):
        if response_id == Gtk.ResponseType.DELETE_EVENT:
            return
        log.warning("add to playlist dialog received strange response: {response_id}".format(
            response_id=response_id,
        ))

    def _on_realize(self, widget):
        self.list_with_playlists.set_visible(False)
        self._euterpe.get_playlists(self._on_playlists_received)

    def _on_cancel(self, btn):
        self.destroy()

    def _hide_spinner(self):
        self.loading_spinner.stop()
        self.loading_spinner.set_visible(False)

    def _show_spinner(self):
        self.loading_spinner.start()
        self.loading_spinner.set_visible(True)

    def _on_playlists_received(self, status, body):
        if status != 200:
            self._show_loading_error("HTTP response code {}.".format(status))
            return

        if len(body) == 0:
            self._show_loading_error("Empty response from server.")
            return

        if "playlists" not in body:
            self._show_loading_error("Unexpected response from server. No 'playlists' property.")
            return

        for playlist in body["playlists"]:
            self.list_with_playlists.add(PlaylistRow(playlist))

        if "next" in body and len(body["next"]) > 0:
            # There are more pages with playlists. Continue adding them to the list.
            self._euterpe.make_request(body["next"], self._on_playlists_received)
        else:
            # This was the last page with playlists. We can hide the spinner now.
            self._hide_spinner()

    def _show_loading_error(self, text):
        self.list_with_playlists.foreach(
            self.list_with_playlists.remove
        )

        self.status_page.set_title("Error Getting Playlists")
        self.status_page.set_description(text)
        self.status_page.set_icon_name("dialog-error-symbolic")
        self._hide_spinner()

    def _on_filter_changed(self, *args):
        self.list_with_playlists.invalidate_filter()

    def _filter_func(self, row, *user_data):
        filter_text = self.playlist_filter.get_text()
        if len(filter_text) < 1:
            return True
        playlist_row = row.get_child()
        return re.search(filter_text, playlist_row.get_name(), re.IGNORECASE)

    def _on_selection_change(self, box, row):
        if row is None:
            self.add_button.set_sensitive(False)
        else:
            self.add_button.set_sensitive(True)

    def _on_added_to_playlist(self, btn):
        selected = self.list_with_playlists.get_selected_row()
        if selected is None:
            return

        playlist_row = selected.get_child()

        self._show_spinner()
        self._euterpe.change_playlist(
            playlist_row.get_playlist_id(),
            self._on_playlist_changed,
            add_track_ids= [t["id"] for t in self._tracks],
        )

    def _on_playlist_changed(self, status, body):
        if status < 200 or status >= 300:
            self._show_loading_error("HTTP response code {}.".format(status))
            return

        self.destroy()

class PlaylistRow(Gtk.Bin):
    __gtype_name__ = 'PlaylistRow'

    def __init__(self, playlist, **kwargs):
        super().__init__(**kwargs)
        self._playlist = playlist

        pl_widget = Gtk.Label(
            ellipsize=Pango.EllipsizeMode.END,
            single_line_mode=True,
            justify=Gtk.Justification.LEFT,
        )
        pl_widget.set_text(playlist["name"])
        pl_widget.show()
        self.add(pl_widget)
        self.show()

    def get_playlist_id(self):
        return self._playlist["id"]

    def get_name(self):
        return self._playlist["name"]
