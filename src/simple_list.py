from gi.repository import Gtk


@Gtk.Template(resource_path='/com/doycho/euterpe/gtk/ui/simple-list.ui')
class EuterpeSimpleList(Gtk.Viewport):
    '''
    EuterpeSimpleList is a widget which gets a list of homogenous items
    and a construction functions for creating a GTK widget from such objects.
    Then on its realization it adds them to its container one by one while
    making sure not to block the main loop.
    '''

    __gtype_name__ = 'EuterpeSimpleList'

    __gsignals__ = {}

    contents = Gtk.Template.Child()
    title = Gtk.Template.Child()

    def __init__(self, items, create_item_func, **kwargs):
        super().__init__(**kwargs)

        self._items = items
        self._create_item_func = create_item_func
        self._widgets_created = False

        self.connect("realize", self._on_create_widgets)
        self.connect("unrealize", self._on_unrealize)

    def _on_create_widgets(self, *args):
        if self._widgets_created:
            return

        self._widgets_created = True

        for item in self._items:
            widget = self._create_item_func(item)
            self.add(widget)
            while (Gtk.events_pending()):
                Gtk.main_iteration()

    def _on_unrealize(self, *args):
        for child in self.contents.get_children():
            child.destroy()

    def add(self, widget):
        self.contents.add(widget)

    def set_title(self, text):
        self.title.set_label(text)
