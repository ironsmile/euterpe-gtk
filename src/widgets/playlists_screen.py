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

from gi.repository import Gtk

from euterpe_gtk.widgets.paginated_box_list import PaginatedBoxList
from euterpe_gtk.widgets.small_playlist import EuterpeSmallPlaylist
from euterpe_gtk.widgets.playlist import EuterpePlaylist
from euterpe_gtk.navigator import Navigator


@Gtk.Template(resource_path='/com/doycho/euterpe/gtk/ui/playlists-screen.ui')
class EuterpePlaylistsScreen(Gtk.Viewport):
    __gtype_name__ = 'EuterpePlaylistsScreen'

    screen_stack = Gtk.Template.Child()
    back_button = Gtk.Template.Child()

    def __init__(self, win, **kwargs):
        super().__init__(**kwargs)

        self._win = win
        self._main_widget = None

        self.back_button.connect(
            "clicked",
            self._on_back_button
        )

        self.screen_stack.connect(
            "notify::visible-child",
            self._on_screen_stack_change_child
        )
        self._nav = Navigator(self.screen_stack)
        self._show_initial_screen()

    def get_back_button(self):
        return self.back_button

    def _on_screen_stack_change_child(self, stack, event):
        is_main = (self._main_widget is stack.get_visible_child())
        if is_main:
            self.back_button.hide()
        else:
            self.back_button.show()

    def _on_back_button(self, btn):
        children = self.screen_stack.get_children()
        if len(children) <= 1:
            return

        visible_child = self.screen_stack.get_visible_child()
        previous_child = children[-2]
        self.screen_stack.set_visible_child(previous_child)
        self.screen_stack.remove(visible_child)

    def _show_initial_screen(self):
        app = self._win.get_application()
        bl = PaginatedBoxList(app, 'playlist', self._create_playlist_widget)
        self._main_widget = bl
        bl.set_title("Playlists")
        self.screen_stack.add(bl)
        self.screen_stack.set_visible_child(bl)

    def _create_playlist_widget(self, playlist_info):
        playlist_obj = EuterpeSmallPlaylist(playlist_info)
        playlist_obj.connect("button-next-clicked", self.on_playlist_clicked)
        return playlist_obj

    def on_playlist_clicked(self, playlist_widget):
        playlist_info = playlist_widget.get_playlist()
        playlist_screen = EuterpePlaylist(playlist_info, self._win)
        self._nav.show_screen(playlist_screen)
