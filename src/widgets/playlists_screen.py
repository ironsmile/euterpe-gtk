# playlists_screen.py
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

from euterpe_gtk.widgets.paginated_box_list import PaginatedBoxList
from euterpe_gtk.widgets.small_playlist import EuterpeSmallPlaylist
from euterpe_gtk.widgets.playlist import EuterpePlaylist, SIGNAL_PLAYLIST_DELETED
from euterpe_gtk.navigator import Navigator
import euterpe_gtk.log as log


@Gtk.Template(resource_path='/com/doycho/euterpe/gtk/ui/playlists-screen.ui')
class EuterpePlaylistsScreen(Gtk.Viewport):
    __gtype_name__ = 'EuterpePlaylistsScreen'

    screen_stack = Gtk.Template.Child()
    new_playlist_button = Gtk.Template.Child()

    create_playlist_popover = Gtk.Template.Child()
    new_playlist_name = Gtk.Template.Child()
    new_playlist_description = Gtk.Template.Child()
    create_playlist_button = Gtk.Template.Child()
    create_request_indicator = Gtk.Template.Child()

    def __init__(self, win, **kwargs):
        super().__init__(**kwargs)

        self._win = win
        self._euterpe = self._win.get_application().get_euterpe()
        self._main_widget = None
        self._box_list = None

        self.new_playlist_name.connect(
            "notify::text",
            self._on_new_playlist_title_changed,
            self.create_playlist_button,
        )

        self.create_playlist_button.connect(
            "clicked",
            self._on_create_playlist_clicked,
            self.new_playlist_name,
            self.new_playlist_description,
            self.create_playlist_popover,
        )

        self.create_request_indicator.bind_property(
            'active',
            self.create_playlist_button, 'sensitive',
            GObject.BindingFlags.INVERT_BOOLEAN
        )

        self._nav = Navigator(self.screen_stack, self._main_widget)
        self._mapped = False
        self.connect("map", self._on_mapped)

    def get_nav(self):
        return self._nav

    def _on_mapped(self, *args):
        if self._mapped:
            return

        self._mapped = True
        log.debug("playlist screen mapped for the first time")
        self._show_initial_screen()

    def _show_initial_screen(self):
        app = self._win.get_application()
        bl = PaginatedBoxList(app, 'playlist', self._create_playlist_widget)
        self._main_widget = bl
        bl.set_title("Playlists")
        bl.replace_header_main_action(self.new_playlist_button)
        self._box_list = bl
        self.screen_stack.add(bl)
        self.screen_stack.set_visible_child(bl)
        self._nav.set_root_scree(self._main_widget)

    def _create_playlist_widget(self, playlist_info):
        playlist_obj = EuterpeSmallPlaylist(playlist_info)
        playlist_obj.connect("button-next-clicked", self.on_playlist_clicked)
        return playlist_obj

    def _on_new_playlist_title_changed(self, entry, _, create_button):
        create_button.set_sensitive(len(entry.get_text()) > 0)

    def _on_create_playlist_clicked(self, button, name_entry, desc_entry, popover):
        desc_buffer = desc_entry.get_buffer()

        self._euterpe.create_playlist(
            name_entry.get_text(),
            desc_buffer.get_slice(
                desc_buffer.get_start_iter(),
                desc_buffer.get_end_iter(),
                include_hidden_chars=False,
            ),
            self._create_playlist_callback,
            name_entry,
            desc_entry,
            popover,
        )
        self.create_request_indicator.start()

    def _create_playlist_callback(self, status, body, name_entry, desc_entry, popover):
        self.create_request_indicator.stop()

        if status != 200:
            self._show_error("Error, HTTP response code {}".format(status))
            return

        if "created_playlsit_id" not in body:
            self._show_error("Unexpected response from server.")
            return

        self._win.show_notification("Playlist created.")

        desc_buffer = desc_entry.get_buffer()

        playlist_info = {
            "id": body["created_playlsit_id"],
            "name": name_entry.get_text(),
            "description": desc_buffer.get_slice(
                desc_buffer.get_start_iter(),
                desc_buffer.get_end_iter(),
                include_hidden_chars=False,
            ),
        }

        popover.popdown()
        name_entry.set_text("")
        desc_buffer.set_text("")

        if self._box_list is not None:
            self._box_list.refresh()

        self._show_playlist(playlist_info)

    def _show_error(self, text):
        #!TODO: show the error to the user.
        log.warning(text)

    def on_playlist_clicked(self, playlist_widget):
        playlist_info = playlist_widget.get_playlist()
        self._show_playlist(playlist_info)

    def _show_playlist(self, playlist_info):
        """
        Creates a new playlist object and navigates to it.
        """
        playlist_widget = EuterpePlaylist(playlist_info)
        playlist_widget.connect(SIGNAL_PLAYLIST_DELETED, self._on_playlist_delete)
        self._nav.show_screen(playlist_widget)

    def _on_playlist_delete(self, playlist_widget):
        self._nav.go_back()
        if self._box_list is not None:
            self._box_list.refresh()
