from gi.repository import GObject, Gtk
from .utils import emit_signal


BUTTON_PLAY_CLICKED = "play-button-clicked"


@Gtk.Template(resource_path='/com/doycho/euterpe/gtk/ui/album.ui')
class EuterpeAlbum(Gtk.Viewport):
    __gtype_name__ = 'EuterpeAlbum'

    __gsignals__ = {
        BUTTON_PLAY_CLICKED: (GObject.SignalFlags.RUN_FIRST, None, ()),
    }

    play_button = Gtk.Template.Child()
    name = Gtk.Template.Child()
    artist_info = Gtk.Template.Child()
    more_button = Gtk.Template.Child()
    more_menu = Gtk.Template.Child()
    track_list = Gtk.Template.Child()

    def __init__(self, album_id, album_name, **kwargs):
        super().__init__(**kwargs)

        self._album_id = album_id
        self._album_name = album_name

    def _on_next_button(self, pb):
        emit_signal(self, BUTTON_PLAY_CLICKED)
