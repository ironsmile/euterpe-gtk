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

from gi.repository import GObject, Gtk, Gio
from euterpe_gtk.utils import emit_signal
from euterpe_gtk.ring_list import RingList
from euterpe_gtk.widgets.box_album import EuterpeBoxAlbum
from euterpe_gtk.widgets.box_artist import EuterpeBoxArtist
from euterpe_gtk.widgets.album import EuterpeAlbum
from euterpe_gtk.widgets.artist import EuterpeArtist
from euterpe_gtk.navigator import Navigator
from euterpe_gtk.player import SIGNAL_TRACK_CHANGED

import euterpe_gtk.log as log

# Duration of seconds for which a recently added albums/artists will be
# valid.
REFRESH_INTERVAL = 60 * 60 * 24

SIGNAL_ADDED_ALBUMS_RESTORED = "state-added-albums-restored"
SIGNAL_ADDED_ARTISTS_RESTORED = "state-added-artists-restored"
SIGNAL_LISTENED_TO_ARTISTS_CHANGED = "state-listened-to-artists-changed"
SIGNAL_LISTENED_TO_ALBUMS_CHANGED = "state-listened-to-albums-changed"


@Gtk.Template(resource_path='/com/doycho/euterpe/gtk/ui/home-screen.ui')
class EuterpeHomeScreen(Gtk.Viewport):
    __gtype_name__ = 'EuterpeHomeScreen'

    __gsignals__ = {
        SIGNAL_ADDED_ALBUMS_RESTORED: (GObject.SignalFlags.RUN_FIRST, None, ()),
        SIGNAL_ADDED_ARTISTS_RESTORED: (GObject.SignalFlags.RUN_FIRST, None, ()),
        SIGNAL_LISTENED_TO_ARTISTS_CHANGED: (GObject.SignalFlags.RUN_FIRST, None, ()),
        SIGNAL_LISTENED_TO_ALBUMS_CHANGED: (GObject.SignalFlags.RUN_FIRST, None, ()),
    }

    screen_stack = Gtk.Template.Child()
    main_screen = Gtk.Template.Child()
    back_button = Gtk.Template.Child()

    recently_added_artists = Gtk.Template.Child()
    recently_added_albums = Gtk.Template.Child()

    recently_listened_to_artists = Gtk.Template.Child()
    recently_listened_to_albums = Gtk.Template.Child()

    recently_listened_artists_empty = Gtk.Template.Child()
    recently_listened_albums_empty = Gtk.Template.Child()

    def __init__(self, win, **kwargs):
        super().__init__(**kwargs)

        app = Gio.Application.get_default()
        if app is None:
            raise Exception("There is no default application")

        self._win = win
        self._player = app.get_player()

        self.back_button.connect(
            "clicked",
            self._on_back_button
        )

        self._recently_added_last_updated = None
        self._recently_added_artists = []
        self._recently_added_albums = []

        self._recently_listened_artists = RingList(10, _compare_artists)
        self._recently_listened_albums = RingList(10, _compare_albums)

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
        self.connect(
            SIGNAL_LISTENED_TO_ALBUMS_CHANGED,
            self._on_recently_listened_to_albums_changed,
        )
        self.connect(
            SIGNAL_LISTENED_TO_ARTISTS_CHANGED,
            self._on_recently_listened_to_artists_changed,
        )
        self._player.connect(
            "track-changed",
            self._on_track_changed,
        )

    def set_added_albums(self, albums):
        self._recently_added_albums = albums
        emit_signal(self, SIGNAL_ADDED_ALBUMS_RESTORED)

    def set_added_artists(self, artists):
        self._recently_added_artists = artists
        emit_signal(self, SIGNAL_ADDED_ARTISTS_RESTORED)

    def _on_state_added_artists(self, *args):
        if len(self._recently_added_artists) < 1:
            self._show_error(self.recently_added_artists, "No artists found.")
            return

        self.recently_added_artists.foreach(
            self.recently_added_artists.remove
        )

        for ind, artist in enumerate(self._recently_added_artists):
            artist_widget = EuterpeBoxArtist(artist)
            artist_widget.connect("clicked", self._on_artist_click)
            self.recently_added_artists.add(artist_widget)
            if ind == 1:
                self.recently_added_artists.scroll_to(artist_widget)
            while (Gtk.events_pending()):
                Gtk.main_iteration()

    def _on_state_added_albums(self, *args):
        if len(self._recently_added_albums) < 1:
            self._show_error(self.recently_added_albums, "No albums found.")
            return

        self.recently_added_albums.foreach(
            self.recently_added_albums.remove
        )

        for ind, album in enumerate(self._recently_added_albums):
            album_widget = EuterpeBoxAlbum(album)
            album_widget.connect("clicked", self._on_album_click)
            self.recently_added_albums.add(album_widget)
            if ind == 1:
                self.recently_added_albums.scroll_to(album_widget)
            while (Gtk.events_pending()):
                Gtk.main_iteration()

    def _on_track_changed(self, *args):
        track = self._player.get_track_info()
        if track is None:
            return

        if "artist" in track and "artist_id" in track:
            changed = self._recently_listened_artists.add({
                "artist": track["artist"],
                "artist_id": track["artist_id"],
            })
            if changed:
                emit_signal(self, SIGNAL_LISTENED_TO_ARTISTS_CHANGED)

        if "artist" in track and "album" in track and "album_id" in track:
            changed = self._recently_listened_albums.add({
                "album": track["album"],
                "artist": track["artist"],
                "album_id": track["album_id"],
            })
            if changed:
                emit_signal(self, SIGNAL_LISTENED_TO_ALBUMS_CHANGED)

    def _on_recently_listened_to_albums_changed(self, *args):
        albums_list = self._recently_listened_albums.list()
        if len(albums_list) < 1:
            self._show_error(self.recently_listened_to_albums,
                self.recently_listened_albums_empty)
            return

        album_boxes = {}
        rc = RemovedAlbumCache(self.recently_listened_to_albums, album_boxes)
        self.recently_listened_to_albums.foreach(rc.remove_and_store)

        for ind, album in enumerate(albums_list):
            album_id = album.get("album_id", None)
            album_widget = None

            if album_id is not None and album_id in album_boxes:
                album_widget = album_boxes[album_id]
            else:
                album_widget = EuterpeBoxAlbum(album)
                album_widget.connect("clicked", self._on_album_click)

            self.recently_listened_to_albums.add(album_widget)
            if ind == 1:
                self.recently_listened_to_albums.scroll_to(album_widget)

            while (Gtk.events_pending()):
                Gtk.main_iteration()

    def _on_recently_listened_to_artists_changed(self, *args):
        artists_list = self._recently_listened_artists.list()
        if len(artists_list) < 1:
            self._show_error(self.recently_listened_to_artists,
                self.recently_listened_artists_empty)
            return

        artist_boxes = {}
        rc = RemovedArtistCache(self.recently_listened_to_artists, artist_boxes)
        self.recently_listened_to_artists.foreach(rc.remove_and_store)

        for ind, artist in enumerate(artists_list):
            artist_id = artist.get("artist_id", None)
            artist_widget = None

            if artist_id is not None and artist_id in artist_boxes:
                artist_widget = artist_boxes[artist_id]
            else:
                artist_widget = EuterpeBoxArtist(artist)
                artist_widget.connect("clicked", self._on_artist_click)

            self.recently_listened_to_artists.add(artist_widget)
            if ind == 1:
                self.recently_listened_to_artists.scroll_to(artist_widget)

            while (Gtk.events_pending()):
                Gtk.main_iteration()

    def get_back_button(self):
        return self.back_button

    def restore_state(self, store):
        '''
        Reads the "recently added" and "recently listened" to from the store
        and adds them to the home widget.

        In case "recently added" is stale (older than REFRESH_INTERVAL) then
        it is first fetched from the server before displayed.
        '''
        self._restore_recently_added(store)
        self._restore_recently_listened_to(store)

    def _restore_recently_added(self, store):
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

    def _restore_recently_listened_to(self, store):
        state = store.get_object("recently_listened_to")
        if state is None or 'albums' not in state or 'artists' not in state:
            # The UI file already shows a message "you haven't listened to
            # anything yet".
            return

        self._recently_listened_artists.replace(state['artists'])
        self._recently_listened_albums.replace(state['albums'])
        emit_signal(self, SIGNAL_LISTENED_TO_ARTISTS_CHANGED)
        emit_signal(self, SIGNAL_LISTENED_TO_ALBUMS_CHANGED)

    def store_state(self, store):
        store.set_object("recently_listened_to", {
            "albums": self._recently_listened_albums.list(),
            "artists": self._recently_listened_artists.list(),
        })

        if self._recently_added_last_updated is None:
            return

        state = {
            "last_updated": self._recently_added_last_updated,
            "artists": self._recently_added_artists,
            "albums": self._recently_added_albums,
        }
        store.set_object("recently_added", state)

    def factory_reset(self):
        self._recently_listened_albums.replace([])
        self._recently_listened_artists.replace([])
        self._recently_added_artists = []
        self._recently_added_albums = []

        emit_signal(self, SIGNAL_LISTENED_TO_ARTISTS_CHANGED)
        emit_signal(self, SIGNAL_LISTENED_TO_ALBUMS_CHANGED)
        emit_signal(self, SIGNAL_ADDED_ALBUMS_RESTORED)
        emit_signal(self, SIGNAL_ADDED_ARTISTS_RESTORED)

    def _on_recently_added_albums_callback(self, status, body):
        if status != 200:
            self._show_error(
                self.recently_added_albums,
                "Error, HTTP response code {}".format(status),
            )
            return

        if body is None or 'data' not in body:
            self._show_error(
                self.recently_added_albums,
                "Unexpected response from server.",
            )
            return

        self._recently_added_last_updated = time.time()
        self.set_added_albums(body['data'])

    def _on_recently_added_artists_callback(self, status, body):
        if status != 200:
            self._show_error(
                self.recently_added_artists,
                "Error, HTTP response code {}".format(status),
            )
            return

        if body is None or 'data' not in body:
            self._show_error(
                self.recently_added_artists,
                "Unexpected response from server.",
            )
            return

        self._recently_added_last_updated = time.time()
        self.set_added_artists(body['data'])

    def _show_error(self, container, error_widget_or_text):
        container.foreach(container.remove)

        if isinstance(error_widget_or_text, Gtk.Widget):
            container.add(error_widget_or_text)
            return

        err = Gtk.Label.new()
        err.set_label(error_widget_or_text)
        err.set_line_wrap(True)
        err.set_justify(Gtk.Justification.CENTER)
        container.add(err)
        err.show()

    def _on_screen_stack_change_child(self, stack, event):
        is_main = (self.main_screen is stack.get_visible_child())
        if is_main:
            self.back_button.hide()
        else:
            self.back_button.show()

    def _on_back_button(self, btn):
        self._nav.go_back()

    def _on_album_click(self, album_widget):
        album_dict = album_widget.get_album()
        album_screen = EuterpeAlbum(album_dict)
        self._nav.show_screen(album_screen)

    def _on_artist_click(self, artist_widget):
        artist_dict = artist_widget.get_artist()
        artist_screen = EuterpeArtist(artist_dict, self._win, self._nav)
        self._nav.show_screen(artist_screen)

def _compare_artists(a, b):
    return a["artist_id"] == b["artist_id"]

def _compare_albums(a, b):
    return a["album_id"] == b["album_id"]

class RemovedAlbumCache(object):
    '''
    RemovedAlbumCache removes GTK Widgets from container but stores them in store_dict
    when they are EuterpeBoxAlbum.
    '''

    def __init__(self, container, store_dict):
        self.container = container
        self.dict = store_dict

    def remove_and_store(self, widget):
        self.container.remove(widget)
        if not isinstance(widget, EuterpeBoxAlbum):
            return

        album_id = widget.get_album().get("album_id", None)
        if album_id is None:
            log.warning("album in RemovedAlbumCache does not have album_id field")
            return

        self.dict[album_id] = widget

class RemovedArtistCache(object):
    '''
    RemovedArtistCache removes GTK Widgets from container but stores them in store_dict
    when they are EuterpeBoxArtist.
    '''

    def __init__(self, container, store_dict):
        self.container = container
        self.dict = store_dict

    def remove_and_store(self, widget):
        self.container.remove(widget)
        if not isinstance(widget, EuterpeBoxArtist):
            return

        artist_id = widget.get_artist().get("artist_id", None)
        if artist_id is None:
            log.warning("artist in RemovedArtistCache does not have artist_id field")
            return

        self.dict[artist_id] = widget
