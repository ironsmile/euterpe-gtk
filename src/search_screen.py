from gi.repository import GObject, Gtk

from .small_album import EuterpeSmallAlbum
from .small_artist import EuterpeSmallArtist
from .album import EuterpeAlbum
from .artist import EuterpeArtist
from .track import EuterpeTrack
from .navigator import Navigator
from .simple_list import EuterpeSimpleList


HEADER_CHANGED = "header-changed"


@Gtk.Template(resource_path='/com/doycho/euterpe/gtk/ui/search-screen.ui')
class EuterpeSearchScreen(Gtk.Viewport):
    __gtype_name__ = 'EuterpeSearchScreen'

    __gsignals__ = {
        HEADER_CHANGED: (GObject.SignalFlags.RUN_FIRST, None, (bool,)),
    }

    main_search_box = Gtk.Template.Child()
    search_results_container = Gtk.Template.Child()
    search_result_viewport = Gtk.Template.Child()
    search_loading_indicator = Gtk.Template.Child()
    search_empty_content = Gtk.Template.Child()
    search_result_list = Gtk.Template.Child()
    search_result_songs = Gtk.Template.Child()
    search_result_albums = Gtk.Template.Child()
    search_result_artists = Gtk.Template.Child()
    play_all_search_results = Gtk.Template.Child()
    not_implemented = Gtk.Template.Child()

    see_all_albums_button = Gtk.Template.Child()
    see_all_artists_button = Gtk.Template.Child()
    see_all_songs_button = Gtk.Template.Child()

    screen_stack = Gtk.Template.Child()
    search_main = Gtk.Template.Child()
    back_button = Gtk.Template.Child()

    def __init__(self, win, **kwargs):
        super().__init__(**kwargs)

        self._win = win

        self._search_results = []
        self._found_albums = []
        self._found_artists = []
        self._search_query = ""

        self.back_button.connect(
            "clicked",
            self._on_back_button
        )
        self.main_search_box.connect(
            "activate",
            self.on_search
        )
        self.main_search_box.connect(
            "search-changed",
            self.on_search_term_changed
        )
        self.play_all_search_results.connect(
            "clicked",
            self.on_play_all_search_results
        )
        self.see_all_albums_button.connect(
            "clicked",
            self.on_see_all_albums
        )
        self.see_all_artists_button.connect(
            "clicked",
            self.on_see_all_artists
        )
        self.see_all_songs_button.connect(
            "clicked",
            self.on_see_all_songs
        )
        self.search_loading_indicator.bind_property(
            'active',
            self.search_results_container, 'visible',
            GObject.BindingFlags.INVERT_BOOLEAN
        )
        self.screen_stack.connect(
            "notify::visible-child",
            self._on_screen_stack_change_child
        )
        self._nav = Navigator(self.screen_stack)

    def get_back_button(self):
        return self.back_button

    def _cleanup_search_results(self):
        self.search_result_viewport.foreach(
            self.search_result_viewport.remove
        )
        self.search_result_songs.foreach(
            lambda s: s.destroy()
        )
        self.search_result_albums.foreach(
            lambda a: a.destroy()
        )
        self.search_result_artists.foreach(
            lambda a: a.destroy()
        )
        self._search_results = []
        self._found_albums = []
        self._found_artists = []

    def on_search(self, entry):
        search_term = entry.get_text()
        if search_term == "":
            self._cleanup_search_results()
            self.search_result_viewport.add(
                self.search_empty_content,
            )
            return

        print("searching for '{}'".format(
            search_term,
            type(search_term)
        ))

        self.search_for(search_term)

    def on_search_term_changed(self, entry):
        search_term = entry.get_text()
        if search_term != "":
            return

        # The search entry was set to empty. This is most probably due
        # to clicking on the "backspace" button on the search entry. So
        # just remove all the search results.
        self._cleanup_search_results()
        self.search_result_viewport.add(
            self.search_empty_content,
        )

    def search_for(self, search_term):
        if search_term is None:
            print("received None instead of a search term, aborting")
            return

        self.search_loading_indicator.start()
        self.search_loading_indicator.set_visible(True)

        euterpe = self._win.get_euterpe()
        euterpe.search(search_term, self._on_search_result)

    def _on_search_result(self, status, body, query):
        self.search_loading_indicator.stop()
        self.search_loading_indicator.set_visible(False)

        self._cleanup_search_results()

        if status != 200:
            label = Gtk.Label.new()
            label.set_text("Error searching. HTTP response code {}.".format(
                status
            ))
            self.search_result_viewport.add(label)
            label.show()
            return

        if len(body) == 0:
            label = Gtk.Label.new()
            label.set_text("Nothing found for '{}'.".format(query))
            self.search_result_viewport.add(label)
            label.show()
            return

        self._search_query = query
        self._search_results = body

        album_to_tracks = {}
        artists_to_tracks = {}
        for track in body:
            album_id = track["album_id"]
            album = album_to_tracks.get(album_id, {
                "tracks": 0,
                "artist": track.get("artist", "n/a"),
                "album": track.get("album", "n/a"),
                "album_id": album_id,
            })
            if album["tracks"] == 0:
                album_to_tracks[album_id] = album
            album["tracks"] += 1

            artist_id = track["artist_id"]
            artist = artists_to_tracks.get(artist_id, {
                "tracks": 0,
                "artist": track.get("artist", "n/a"),
                "artist_id": artist_id,
            })
            if artist["tracks"] == 0:
                artists_to_tracks[artist_id] = artist
            artist["tracks"] += 1

            while (Gtk.events_pending()):
                Gtk.main_iteration()

        albums = sorted(
            album_to_tracks.items(),
            key=lambda v: v[1]["tracks"],
            reverse=True
        )
        self._found_albums = [t[1] for t in albums]

        # Try to remove this from memory as fast as possible.
        album_to_tracks = None

        for album_info in self._found_albums[:10]:
            album_widget = self._create_small_album_widget(album_info)
            self.search_result_albums.add(album_widget)

        artists = sorted(
            artists_to_tracks.items(),
            key=lambda v: v[1]["tracks"],
            reverse=True
        )
        self._found_artists = [t[1] for t in artists]

        # Try to remove this from memory as fast as possible.
        artists_to_tracks = None

        for artist_info in self._found_artists[:10]:
            artist_obj = self._create_small_artists_widget(artist_info)
            self.search_result_artists.add(artist_obj)

        for track in body[:10]:
            tr_obj = self._create_track_widget(track)
            self.search_result_songs.add(tr_obj)

        self.search_result_viewport.add(self.search_result_list)
        self.search_result_list.show()

    def on_play_all_search_results(self, btn):
        player = self._win.get_player()
        player.set_playlist(self._search_results)
        player.play()

    def on_album_next(self, album_widget):
        album_dict = album_widget.get_album()
        album_screen = EuterpeAlbum(album_dict, self._win)
        self._nav.show_screen(album_screen)

    def on_artist_next(self, artist_widget):
        artist_dict = artist_widget.get_artist()
        artist_screen = EuterpeArtist(artist_dict, self._win, self._nav)
        self._nav.show_screen(artist_screen)

    def on_track_set(self, track_widget):
        player = self._win.get_player()

        if player is None:
            print("trying to set track when there is no player active")
            return

        track = track_widget.get_track()

        player.set_playlist([track])
        player.play()

    def _create_small_artists_widget(self, artist_info):
        artist_obj = EuterpeSmallArtist(artist_info)
        artist_obj.connect("button-next-clicked", self.on_artist_next)
        return artist_obj

    def _create_small_album_widget(self, album_info):
        album_obj = EuterpeSmallAlbum(album_info)
        album_obj.connect("button-next-clicked", self.on_album_next)
        return album_obj

    def _create_track_widget(self, track_info):
        track_obj = EuterpeTrack(track_info)
        track_obj.connect("play-button-clicked", self.on_track_set)
        return track_obj

    def on_see_all_artists(self, btn):
        artist_list = EuterpeSimpleList(
            self._found_artists,
            self._create_small_artists_widget,
        )
        artist_list.set_title("Artists for search \"{}\"".format(
            self._search_query
        ))

        self._nav.show_screen(artist_list)

    def on_see_all_albums(self, btn):
        album_list = EuterpeSimpleList(
            self._found_albums,
            self._create_small_album_widget,
        )
        album_list.set_title("Albums for search \"{}\"".format(
            self._search_query
        ))

        self._nav.show_screen(album_list)

    def on_see_all_songs(self, btn):
        limit = 500

        songs_list = EuterpeSimpleList(
            self._search_results[:limit],
            self._create_track_widget,
        )
        songs_list.set_title("First {} songs for search \"{}\"".format(
            limit,
            self._search_query
        ))

        self._nav.show_screen(songs_list)

    def _on_screen_stack_change_child(self, stack, event):
        is_main = (self.search_main is stack.get_visible_child())
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
