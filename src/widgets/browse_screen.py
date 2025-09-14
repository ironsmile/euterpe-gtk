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
from euterpe_gtk.utils import emit_signal
from euterpe_gtk.widgets.paginated_box_list import PaginatedBoxList
from euterpe_gtk.widgets.box_artist import EuterpeBoxArtist
from euterpe_gtk.widgets.box_album import EuterpeBoxAlbum
from euterpe_gtk.widgets.artist import EuterpeArtist
from euterpe_gtk.widgets.album import EuterpeAlbum
from euterpe_gtk.widgets.track import EuterpeTrack, PLAY_BUTTON_CLICKED, APPEND_BUTTON_CLICKED
from euterpe_gtk.navigator import Navigator


@Gtk.Template(resource_path='/com/doycho/euterpe/gtk/ui/browse-screen.ui')
class EuterpeBrowseScreen(Gtk.Viewport):
    __gtype_name__ = 'EuterpeBrowseScreen'


    show_artists_button = Gtk.Template.Child()
    show_albums_button = Gtk.Template.Child()
    show_songs_button = Gtk.Template.Child()
    show_offline_library_button = Gtk.Template.Child()

    search_button = Gtk.Template.Child()
    browse_stack = Gtk.Template.Child()

    not_implemented = Gtk.Template.Child()
    browse_main = Gtk.Template.Child()

    def __init__(self, win, **kwargs):
        super().__init__(**kwargs)

        self._win = win

        self.show_offline_library_button.connect(
            "clicked",
            self._show_not_implemented_screen,
        )

        self.show_songs_button.connect(
            "clicked",
            self._on_browse_songs_button,
        )

        self.show_artists_button.connect(
            "clicked",
            self._on_browse_artists_button
        )

        self.show_albums_button.connect(
            "clicked",
            self._on_browse_albums_button
        )

        self._nav = Navigator(self.browse_stack, self.browse_main)

    def get_nav(self):
        return self._nav

    def _on_browse_songs_button(self, btn):
        app = self._win.get_application()
        bl = PaginatedBoxList(app, 'song', self._create_song_widget)
        bl.set_title("Songs Browser")
        self.browse_stack.add(bl)
        self.browse_stack.set_visible_child(bl)

    def _create_song_widget(self, track_info):
        song_widget = EuterpeTrack(track_info)
        song_widget.connect(PLAY_BUTTON_CLICKED, self._on_song_play_request)
        song_widget.connect(APPEND_BUTTON_CLICKED, self._on_song_append_request)
        return song_widget

    def _on_song_play_request(self, song_widget):
        track = song_widget.get_track()
        player = self._win.get_player()
        player.set_playlist([track])
        player.play()

    def _on_song_append_request(self, song_widget):
        track = song_widget.get_track()
        player = self._win.get_player()
        player.append_to_playlist([track])

    def _on_browse_artists_button(self, btn):
        app = self._win.get_application()
        bl = PaginatedBoxList(app, 'artist', self._create_artists_widget)
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
        app = self._win.get_application()
        bl = PaginatedBoxList(app, 'album', self._create_album_widget)
        bl.set_title("Albums Browser")
        self.browse_stack.add(bl)
        self.browse_stack.set_visible_child(bl)

    def _create_album_widget(self, album_info):
        album_widget = EuterpeBoxAlbum(album_info)
        album_widget.connect("clicked", self._on_album_click)
        return album_widget

    def _on_album_click(self, album_widget):
        album_dict = album_widget.get_album()
        album_screen = EuterpeAlbum(album_dict)
        self._nav.show_screen(album_screen)

    def _show_not_implemented_screen(self, btn):
        self.browse_stack.add(self.not_implemented)
        self.browse_stack.set_visible_child(self.not_implemented)
