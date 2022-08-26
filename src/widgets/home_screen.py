# home_screen.py
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
import time

from gi.repository import GObject, Gtk
from euterpe_gtk.utils import emit_signal
from euterpe_gtk.widgets.box_album import EuterpeBoxAlbum
from euterpe_gtk.widgets.box_artist import EuterpeBoxArtist
from euterpe_gtk.widgets.album import EuterpeAlbum
from euterpe_gtk.widgets.artist import EuterpeArtist
from euterpe_gtk.navigator import Navigator


# Duration of seconds for which a recently added albums/artists will be
# valid.
REFRESH_INTERVAL = 60 * 60 * 24

SIGNAL_ADDED_ALBUMS_RESTORED = "state-added-albums-restored"
SIGNAL_ADDED_ARTISTS_RESTORED = "state-added-artists-restored"


@Gtk.Template(resource_path='/com/doycho/euterpe/gtk/ui/home-screen.ui')
class EuterpeHomeScreen(Gtk.Viewport):
    __gtype_name__ = 'EuterpeHomeScreen'

    __gsignals__ = {
        SIGNAL_ADDED_ALBUMS_RESTORED: (GObject.SignalFlags.RUN_FIRST, None, ()),
        SIGNAL_ADDED_ARTISTS_RESTORED: (GObject.SignalFlags.RUN_FIRST, None, ()),
    }

    screen_stack = Gtk.Template.Child()
    main_screen = Gtk.Template.Child()
    back_button = Gtk.Template.Child()

    recently_added_artists = Gtk.Template.Child()
    recently_added_albums = Gtk.Template.Child()

    def __init__(self, win, **kwargs):
        super().__init__(**kwargs)
        self._win = win

        self.back_button.connect(
            "clicked",
            self._on_back_button
        )

        self._recently_added_last_updated = None
        self._recently_added_artists = []
        self._recently_added_albums = []

        self.screen_stack.connect(
            "notify::visible-child",
            self._on_screen_stack_change_child
        )
        self._nav = Navigator(self.screen_stack)

        self.connect(
            SIGNAL_ADDED_ALBUMS_RESTORED,
            self._on_state_added_albums,
        )
        self.connect(
            SIGNAL_ADDED_ARTISTS_RESTORED,
            self._on_state_added_artists,
        )

    def set_added_albums(self, albums):
        self._recently_added_albums = albums
        emit_signal(self, SIGNAL_ADDED_ALBUMS_RESTORED)

    def set_added_artists(self, artists):
        self._recently_added_artists = artists
        emit_signal(self, SIGNAL_ADDED_ARTISTS_RESTORED)

    def _on_state_added_artists(self, *args):
        if len(self._recently_added_artists) < 1:
            self._show_error("No albums found.")
            return

        self.recently_added_artists.foreach(
            self.recently_added_artists.remove
        )

        for artist in self._recently_added_artists:
            artist_widget = EuterpeBoxArtist(artist)
            artist_widget.connect("clicked", self._on_artist_click)
            self.recently_added_artists.add(artist_widget)
            while (Gtk.events_pending()):
                Gtk.main_iteration()

    def _on_state_added_albums(self, *args):
        if len(self._recently_added_albums) < 1:
            self._show_error("No albums found.")
            return

        self.recently_added_albums.foreach(
            self.recently_added_albums.remove
        )

        for album in self._recently_added_albums:
            album_widget = EuterpeBoxAlbum(album)
            album_widget.connect("clicked", self._on_album_click)
            self.recently_added_albums.add(album_widget)
            while (Gtk.events_pending()):
                Gtk.main_iteration()

    def get_back_button(self):
        return self.back_button

    def restore_state(self, store):
        state = store.get_object("recently_added")
        if (
            state is not None and 'last_updated' in state
            and isinstance(state['last_updated'], float)
            and state['last_updated'] + REFRESH_INTERVAL > time.time()
        ):
            self._recently_added_albums = state["albums"]
            emit_signal(self, SIGNAL_ADDED_ALBUMS_RESTORED)

            self._recently_added_artists = state["artists"]
            emit_signal(self, SIGNAL_ADDED_ARTISTS_RESTORED)
            return

        euterpe = self._win.get_euterpe()
        euterpe.get_recently_added(
            "album",
            self._on_recently_added_albums_callback
        )
        euterpe.get_recently_added(
            "artist",
            self._on_recently_added_artists_callback
        )

    def store_state(self, store):
        if self._recently_added_last_updated is None:
            return

        state = {
            "last_updated": self._recently_added_last_updated,
            "artists": self._recently_added_artists,
            "albums": self._recently_added_albums,
        }
        store.set_object("recently_added", state)

    def _on_recently_added_albums_callback(self, status, body):
        if status != 200:
            self._show_error("Error, HTTP response code {}".format(status))
            return

        if body is None or 'data' not in body:
            self._show_error("Unexpected response from server.")
            return

        self._recently_added_last_updated = time.time()
        self.set_added_albums(body['data'])

    def _on_recently_added_artists_callback(self, status, body):
        if status != 200:
            self._show_error("Error, HTTP response code {}".format(status))
            return

        if body is None or 'data' not in body:
            self._show_error("Unexpected response from server.")
            return

        self._recently_added_last_updated = time.time()
        self.set_added_artists(body['data'])

    def _show_error(self, container, error_message):
        container.foreach(container.remove)

        err = Gtk.Label.new()
        err.set_label(error_message)
        err.set_line_wrap(True)
        container.add(err)
        err.show()

    def _on_screen_stack_change_child(self, stack, event):
        is_main = (self.main_screen is stack.get_visible_child())
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

    def _on_album_click(self, album_widget):
        album_dict = album_widget.get_album()
        album_screen = EuterpeAlbum(album_dict, self._win)
        self._nav.show_screen(album_screen)

    def _on_artist_click(self, artist_widget):
        artist_dict = artist_widget.get_artist()
        artist_screen = EuterpeArtist(artist_dict, self._win, self._nav)
        self._nav.show_screen(artist_screen)
