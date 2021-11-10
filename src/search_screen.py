from gi.repository import GObject, Gtk
from .utils import emit_signal

from .small_album import EuterpeSmallAlbum
from .small_artist import EuterpeSmallArtist
from .track import EuterpeTrack


HEADER_CHANGED = "header-changed"


@Gtk.Template(resource_path='/com/doycho/euterpe/gtk/ui/search-screen.ui')
class EuterpeSearchScreen(Gtk.Box):
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

    def __init__(self, euterpe, player, **kwargs):
        super().__init__(**kwargs)

        self._euterpe = euterpe
        self._player = player

        self._search_results = []

        self.main_search_box.connect("activate", self.on_search_changed)
        self.play_all_search_results.connect(
            "clicked",
            self.on_play_all_search_results
        )

        self.search_loading_indicator.bind_property(
            'active',
            self.search_results_container, 'visible',
            GObject.BindingFlags.INVERT_BOOLEAN
        )

    def _cleanup_search_results(self):
        self.search_result_viewport.foreach(
            self.search_result_viewport.remove
        )
        self.search_result_songs.foreach(
            self.search_result_songs.remove
        )
        self.search_result_albums.foreach(
            self.search_result_albums.remove
        )
        self.search_result_artists.foreach(
            self.search_result_artists.remove
        )

    def on_search_changed(self, search_entry):
        search_term = search_entry.get_text()
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

    def search_for(self, search_term):
        if search_term is None:
            print("received None instead of a search term, aborting")
            return

        self.search_loading_indicator.start()
        self.search_loading_indicator.set_visible(True)
        self._euterpe.search(search_term, self._on_search_result)

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

        self._search_results = body

        album_to_tracks = {}
        artists_to_tracks = {}
        for track in body:
            album_id = track["album_id"]
            album = album_to_tracks.get(album_id, {
                "tracks": 0,
                "artist": track.get("artist", "n/a"),
                "album": track.get("album", "n/a")
            })
            if album["tracks"] == 0:
                album_to_tracks[album_id] = album
            album["tracks"] += 1

            artist_id = track["artist_id"]
            artist = artists_to_tracks.get(artist_id, {
                "tracks": 0,
                "artist": track.get("artist", "n/a")
            })
            if artist["tracks"] == 0:
                artists_to_tracks[artist_id] = artist
            artist["tracks"] += 1

        albums = sorted(
            album_to_tracks.items(),
            key=lambda v: v[1]["tracks"],
            reverse=True
        )

        # Try to remove this from memory as fast as possible.
        album_to_tracks = None

        for album_id, album_info in albums[:10]:
            album_info["album_id"] = album_id
            al_obj = EuterpeSmallAlbum(album_info)
            self.search_result_albums.add(al_obj)

        artists = sorted(
            artists_to_tracks.items(),
            key=lambda v: v[1]["tracks"],
            reverse=True
        )

        artists_to_tracks = None

        for artist_id, artist_info in artists[:10]:
            artist_info["artist_id"] = artist_id
            al_obj = EuterpeSmallArtist(artist_info)
            self.search_result_artists.add(al_obj)

        for track in body[:5]:
            tr_obj = EuterpeTrack(track)
            self.search_result_songs.add(tr_obj)
            tr_obj.connect("play-button-clicked", self.on_track_set)

        self.search_result_viewport.add(self.search_result_list)
        self.search_result_list.show()

    def on_play_all_search_results(self, btn):
        self._player.set_playlist(self._search_results)
        self._player.play()

    def on_track_set(self, trackObj):
        if self._player is None:
            print("trying to set track when there is no player active")
            return

        track = trackObj.get_track()

        self._player.set_playlist([track])
        self._player.play()
