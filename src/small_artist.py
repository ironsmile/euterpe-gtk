from gi.repository import GObject, Gtk
from .utils import emit_signal


BUTTON_NEXT_CLICKED = "button-next-clicked"


@Gtk.Template(resource_path='/com/doycho/euterpe/gtk/ui/small-artist.ui')
class EuterpeSmallArtist(Gtk.Viewport):
    __gtype_name__ = 'EuterpeSmallArtist'

    __gsignals__ = {
        BUTTON_NEXT_CLICKED: (GObject.SignalFlags.RUN_FIRST, None, ()),
    }

    name = Gtk.Template.Child()
    open_button = Gtk.Template.Child()

    def __init__(self, artist, **kwargs):
        super().__init__(**kwargs)

        self._artist = artist
        self.name.set_label(artist.get("artist", "<N/A>"))

        self.open_button.connect("clicked", self._on_next_button)

    def _on_next_button(self, pb):
        emit_signal(self, BUTTON_NEXT_CLICKED)

    def get_artist(self):
        return self._artist.copy()
