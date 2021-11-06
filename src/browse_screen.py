from gi.repository import GObject, Gtk
from .utils import emit_signal


SEARCH_BUTTON_CLICKED = "search-button-clicked"


@Gtk.Template(resource_path='/com/doycho/euterpe/gtk/ui/browse-screen.ui')
class EuterpeBrowseScreen(Gtk.Viewport):
    __gtype_name__ = 'EuterpeBrowseScreen'

    __gsignals__ = {
        SEARCH_BUTTON_CLICKED: (GObject.SignalFlags.RUN_FIRST, None, ()),
    }

    search_button = Gtk.Template.Child()

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.search_button.connect("clicked", self._on_search_button)

    def _on_search_button(self, btn):
        emit_signal(self, SEARCH_BUTTON_CLICKED)
