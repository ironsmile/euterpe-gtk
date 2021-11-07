from gi.repository import GObject, Gtk
from .utils import emit_signal


SEARCH_BUTTON_CLICKED = "search-button-clicked"


@Gtk.Template(resource_path='/com/doycho/euterpe/gtk/ui/browse-screen.ui')
class EuterpeBrowseScreen(Gtk.Viewport):
    __gtype_name__ = 'EuterpeBrowseScreen'

    __gsignals__ = {
        SEARCH_BUTTON_CLICKED: (GObject.SignalFlags.RUN_FIRST, None, ()),
    }

    show_artists_button = Gtk.Template.Child()
    show_albums_button = Gtk.Template.Child()
    show_songs_button = Gtk.Template.Child()
    show_offline_library_button = Gtk.Template.Child()

    search_button = Gtk.Template.Child()
    browse_stack = Gtk.Template.Child()

    not_implemented = Gtk.Template.Child()
    back_button = Gtk.Template.Child()
    browse_main = Gtk.Template.Child()

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        self.search_button.connect("clicked", self._on_search_button)

        btns = [
            self.show_artists_button,
            self.show_albums_button,
            self.show_songs_button,
            self.show_offline_library_button,
        ]

        for btn in btns:
            btn.connect("clicked", self._show_not_implemented_screen)

        self.back_button.connect(
            "clicked",
            self._on_back_button
        )

        self.browse_stack.connect(
            "notify::visible-child",
            self._on_browse_stack_change_child
        )

    def _on_search_button(self, btn):
        emit_signal(self, SEARCH_BUTTON_CLICKED)

    def _on_back_button(self, btn):
        children = self.browse_stack.get_children()
        if len(children) == 1:
            return

        visible_child = self.browse_stack.get_visible_child()
        previous_child = children[-2]
        self.browse_stack.set_visible_child(previous_child)
        self.browse_stack.remove(visible_child)

    def _show_not_implemented_screen(self, btn):
        self.browse_stack.add(self.not_implemented)
        self.browse_stack.set_visible_child(self.not_implemented)

    def _on_browse_stack_change_child(self, stack, event):
        hide_back = (self.browse_main == stack.get_visible_child())
        if hide_back:
            self.back_button.hide()
        else:
            self.back_button.show()
