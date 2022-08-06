from gi.repository import GObject, Gtk
from .track import EuterpeTrack
from .small_album import EuterpeSmallAlbum
from .album import EuterpeAlbum
from .async_artwork import AsyncArtwork


@Gtk.Template(resource_path='/com/doycho/euterpe/gtk/ui/artist.ui')
class EuterpeArtist(Gtk.Viewport):
    __gtype_name__ = 'EuterpeArtist'

    __gsignals__ = {}

    artist_name = Gtk.Template.Child()
    album_list = Gtk.Template.Child()
    loading_spinner = Gtk.Template.Child()
    image = Gtk.Template.Child()

    def __init__(self, artist, win, nav, **kwargs):
        '''
            Artist is a dict which have an name and id such as:

            {
                "artist": "Artist Name",
                "artist_id": 42,
            }
        '''
        super().__init__(**kwargs)

        self._nav = nav
        self._win = win
        self._artist = artist
        self._albums = []

        artist_name = artist.get("artist", "Unknown")

        self.artist_name.set_label(artist_name)

        win.get_euterpe().search(artist_name, self._on_search_result)
        self.connect("unrealize", self._on_unrealize)
        self._init_artwork(artist)

    def _init_artwork(self, artist):
        artist_id = artist.get("artist_id", None)
        if artist_id is None:
            print("EuterpeArtist: no artist ID found for {}".format(artist))
            return

        self._artwork_loader = AsyncArtwork(self.image, 330)
        self._artwork_loader.load_artist_image(artist_id)

    def _on_search_result(self, status, body, query):
        self.album_list.foreach(self.album_list.remove)

        if status != 200:
            label = Gtk.Label.new()
            label.set_text(
                "Error getting artist. HTTP response code {}.".format(
                    status
                )
            )
            self.album_list.add(label)
            label.show()
            return

        artist_albums = {}
        for track in body:
            if track["artist_id"] != self._artist["artist_id"]:
                continue
            if track["album_id"] in artist_albums:
                continue

            artist_albums[track["album_id"]] = {
                "artist": track["artist"],
                "artist_id": track["artist_id"],
                "album": track["album"],
                "album_id": track["album_id"],
            }

        if len(artist_albums) == 0:
            label = Gtk.Label.new()
            label.set_text("No albums found.")
            self.album_list.add(label)
            label.show()
            return

        for _, album in artist_albums.items():
            alb_obj = EuterpeSmallAlbum(album)
            self.album_list.add(alb_obj)
            alb_obj.connect("button-next-clicked", self.on_on_album_clicked)
            while (Gtk.events_pending()):
                Gtk.main_iteration()

    def on_on_album_clicked(self, album_widget):
        album_dict = album_widget.get_album()
        album_screen = EuterpeAlbum(album_dict, self._win)
        self._nav.show_screen(album_screen)

    def _on_unrealize(self, *args):
        for child in self.album_list.get_children():
            child.destroy()
