# browse_screen.py
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
from .paginated_box_list import PaginatedBoxList
from .box_artist import EuterpeBoxArtist
from .box_album import EuterpeBoxAlbum
from .artist import EuterpeArtist
from .album import EuterpeAlbum
from .navigator import Navigator


SEARCH_BUTTON_CLICKED = "search-button-clicked"


@Gtk.Template(resource_path='/com/doycho/euterpe/gtk/ui/browse-screen.ui')
class EuterpeBrowseScreen(Gtk.Viewport):
    __gtype_name__ = 'EuterpeBrowseScreen'

    __gsignals__ = {
        SEARCH_BUTTON_CLICKED: (GObject.SignalFlags.RUN_FIRST, None, ()),
    }

    show_artists_button = Gtk.Template.Child()
    show_albums_button = Gtk.Template.Child()
    show_songs_button = Gtk.Template.Child()
    show_offline_library_button = Gtk.Template.Child()

    search_button = Gtk.Template.Child()
    browse_stack = Gtk.Template.Child()

    not_implemented = Gtk.Template.Child()
    back_button = Gtk.Template.Child()
    browse_main = Gtk.Template.Child()

    def __init__(self, win, **kwargs):
        super().__init__(**kwargs)

        self._win = win
        self.search_button.connect("clicked", self._on_search_button)

        btns = [
            self.show_songs_button,
            self.show_offline_library_button,
        ]

        for btn in btns:
            btn.connect("clicked", self._show_not_implemented_screen)

        self.show_artists_button.connect(
            "clicked",
            self._on_browse_artists_button
        )

        self.show_albums_button.connect(
            "clicked",
            self._on_browse_albums_button
        )

        self.back_button.connect(
            "clicked",
            self._on_back_button
        )

        self.browse_stack.connect(
            "notify::visible-child",
            self._on_browse_stack_change_child
        )
        self._nav = Navigator(self.browse_stack)

    def get_back_button(self):
        return self.back_button

    def _on_browse_artists_button(self, btn):
        euterpe = self._win.get_euterpe()
        bl = PaginatedBoxList(euterpe, 'artist', self._create_artists_widget)
        bl.set_title("Artists Browser")
        self.browse_stack.add(bl)
        self.browse_stack.set_visible_child(bl)

    def _create_artists_widget(self, artist_info):
        artist_widget = EuterpeBoxArtist(artist_info)
        artist_widget.connect("clicked", self._on_artist_click)
        return artist_widget

    def _on_artist_click(self, artist_widget):
        artist_dict = artist_widget.get_artist()
        artist_screen = EuterpeArtist(artist_dict, self._win, self._nav)
        self._nav.show_screen(artist_screen)

    def _on_browse_albums_button(self, btn):
        euterpe = self._win.get_euterpe()
        bl = PaginatedBoxList(euterpe, 'album', self._create_album_widget)
        bl.set_title("Albums Browser")
        self.browse_stack.add(bl)
        self.browse_stack.set_visible_child(bl)

    def _create_album_widget(self, album_info):
        album_widget = EuterpeBoxAlbum(album_info)
        album_widget.connect("clicked", self._on_album_click)
        return album_widget

    def _on_album_click(self, album_widget):
        album_dict = album_widget.get_album()
        album_screen = EuterpeAlbum(album_dict, self._win)
        self._nav.show_screen(album_screen)

    def _on_search_button(self, btn):
        emit_signal(self, SEARCH_BUTTON_CLICKED)

    def _on_back_button(self, btn):
        children = self.browse_stack.get_children()
        if len(children) <= 1:
            return

        visible_child = self.browse_stack.get_visible_child()
        previous_child = children[-2]
        self.browse_stack.set_visible_child(previous_child)
        self.browse_stack.remove(visible_child)

        if visible_child is not self.browse_main and\
                visible_child is not self.not_implemented:
            visible_child.destroy()

    def _show_not_implemented_screen(self, btn):
        self.browse_stack.add(self.not_implemented)
        self.browse_stack.set_visible_child(self.not_implemented)

    def _on_browse_stack_change_child(self, stack, event):
        is_main = (self.browse_main is stack.get_visible_child())
        if is_main:
            self.back_button.hide()
        else:
            self.back_button.show()
