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

from gi.repository import GObject, Gtk, Gio
from euterpe_gtk.utils import emit_signal
from euterpe_gtk.widgets.paginated_box_list import PaginatedBoxList
from euterpe_gtk.widgets.box_artist import EuterpeBoxArtist
from euterpe_gtk.widgets.box_album import EuterpeBoxAlbum
from euterpe_gtk.widgets.artist import EuterpeArtist
from euterpe_gtk.widgets.album import EuterpeAlbum
from euterpe_gtk.widgets.image_card import EuterpeImageCard
from euterpe_gtk.widgets.carousel_item import EuterpeCarouselItem
from euterpe_gtk.widgets.track import EuterpeTrack, PLAY_BUTTON_CLICKED, APPEND_BUTTON_CLICKED
from euterpe_gtk.navigator import Navigator
import euterpe_gtk.log as log


@Gtk.Template(resource_path='/com/doycho/euterpe/gtk/ui/browse-screen.ui')
class EuterpeBrowseScreen(Gtk.Viewport):
    __gtype_name__ = 'EuterpeBrowseScreen'

    browse_stack = Gtk.Template.Child()

    not_implemented = Gtk.Template.Child()
    browse_main = Gtk.Template.Child()

    main_actions = Gtk.Template.Child()
    random_albums = Gtk.Template.Child()
    random_albums_loader = Gtk.Template.Child()

    carousel_overlay = Gtk.Template.Child()
    carousel_prev_button = Gtk.Template.Child()
    carousel_next_button = Gtk.Template.Child()

    def __init__(self, win, **kwargs):
        super().__init__(**kwargs)

        self._win = win

        app = Gio.Application.get_default()
        if app is None:
            raise Exception("There is no default application")
        self._euterpe = app.get_euterpe()

        cards  = [
            {
                "title": "Artists",
                "icon": "avatar-default-symbolic",
                "on_click": self._on_browse_artists_button,
            },
            {
                "title":"Albums",
                "icon": "media-optical-cd-audio-symbolic",
                "on_click": self._on_browse_albums_button,
            },
            {
                "title":"Songs",
                "icon": "folder-music-symbolic",
                "on_click": self._on_browse_songs_button,
            },
            {
                "title":"Playlists",
                "icon": "folder-music-symbolic",
                "action": "app.show_playlists",
            },
            {
                "title":"Offline Library",
                "icon": "user-bookmarks-symbolic",
                "on_click": self._show_not_implemented_screen,
            },
            {
                "title":"Search",
                "icon": "system-search-symbolic",
                "action": "app.search",
            },
        ]

        for cardInfo in cards:
            card = EuterpeImageCard(**cardInfo)
            self.main_actions.add(card)

        self._nav = Navigator(self.browse_stack, self.browse_main)
        self._mapped = False
        self.connect(
            "map",
            self._on_mapped
        )

    def get_nav(self):
        return self._nav

    def _on_mapped(self, *args):
        if self._mapped:
            return

        self._mapped = True
        log.debug("browse screen mapped for the first time")
        self._euterpe.get_random_list(
            "album",
            self._on_random_albums_callback,
            per_page=6,
        )
        self.carousel_overlay.add_overlay(self.carousel_next_button)
        self.carousel_overlay.add_overlay(self.carousel_prev_button)

        self.carousel_next_button.connect("clicked", self._on_carousel_next)
        self.carousel_prev_button.connect("clicked", self._on_carousel_prev)

    def _on_carousel_next(self, btn):
        pos = self.random_albums.get_position()
        pages = self.random_albums.get_n_pages()
        if pos+1 >= pages:
            return
        children = self.random_albums.get_children()
        # children is 0-based index while positions in the carousel are 1-based.
        next_pos = int(pos+1)
        self.random_albums.scroll_to(children[next_pos])

    def _on_carousel_prev(self, btn):
        pos = self.random_albums.get_position()
        if pos <= 0:
            return
        children = self.random_albums.get_children()
        # children is 0-based index while positions in the carousel are 1-based.
        prev_pos = int(pos-1)
        self.random_albums.scroll_to(children[prev_pos])

    def _on_random_albums_callback(self, status, body):
        if status != 200:
            self._show_error(
                self.random_albums_loader,
                "Error, HTTP response code {}".format(status),
            )
            return

        if body is None or 'data' not in body:
            self._show_error(
                self.random_albums_loader,
                "Unexpected response from server.",
            )
            return

        self._show_albums_in_carousel(body['data'])

    def _show_albums_in_carousel(self, albums):
        if len(albums) < 1:
            self._show_error(self.random_albums_loader, "No albums found.")
            return

        self.random_albums.foreach(
            self.random_albums.remove
        )

        for album in albums:
            album_widget = EuterpeCarouselItem(album)
            album_widget.connect("clicked", self._on_album_click)
            self.random_albums.add(album_widget)
            while (Gtk.events_pending()):
                Gtk.main_iteration()

    def _on_browse_songs_button(self, btn):
        app = self._win.get_application()
        bl = PaginatedBoxList(app, 'song', self._create_song_widget)
        bl.set_title("Songs Browser")
        self._nav.show_screen(bl)

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
        self._nav.show_screen(bl)

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
        self._nav.show_screen(bl)

    def _create_album_widget(self, album_info):
        album_widget = EuterpeBoxAlbum(album_info)
        album_widget.connect("clicked", self._on_album_click)
        return album_widget

    def _on_album_click(self, album_widget):
        album_dict = album_widget.get_album()
        album_screen = EuterpeAlbum(album_dict)
        self._nav.show_screen(album_screen)

    def _show_not_implemented_screen(self, btn):
        self._nav.show_screen(self.not_implemented)
