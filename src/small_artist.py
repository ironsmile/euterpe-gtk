from gi.repository import GObject, Gtk
from .utils import emit_signal
from .async_artwork import AsyncArtwork
from .service import ArtworkSize

BUTTON_NEXT_CLICKED = "button-next-clicked"


@Gtk.Template(resource_path='/com/doycho/euterpe/gtk/ui/small-artist.ui')
class EuterpeSmallArtist(Gtk.Viewport):
    __gtype_name__ = 'EuterpeSmallArtist'

    __gsignals__ = {
        BUTTON_NEXT_CLICKED: (GObject.SignalFlags.RUN_FIRST, None, ()),
    }

    name = Gtk.Template.Child()
    open_button = Gtk.Template.Child()
    image = Gtk.Template.Child()

    def __init__(self, artist, **kwargs):
        super().__init__(**kwargs)

        self._artist = artist
        self.name.set_label(artist.get("artist", "<N/A>"))

        self.open_button.connect("clicked", self._on_next_button)
        self._init_artwork(artist)
        self.connect("destroy", self._on_destroy)

    def _init_artwork(self, artist):
        artist_id = artist.get("artist_id", None)
        if artist_id is None:
            print("EuterpeSmallArtist: no artist ID found for {}".format(artist))
            return

        self._artwork_loader = AsyncArtwork(self.image, 50)
        self._artwork_loader.load_artist_image(artist_id, ArtworkSize.SMALL)

    def _on_destroy(self, *args):
        self._artwork_loader.cancel()

    def _on_next_button(self, pb):
        emit_signal(self, BUTTON_NEXT_CLICKED)

    def get_artist(self):
        return self._artist.copy()
