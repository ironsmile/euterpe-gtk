from gi.repository import Gtk, GLib


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
        self._removed = False

        self.connect("realize", self._create_widgets)
        self.connect("unrealize", self._on_unrealize)

    def _create_widgets(self, *args):
        if self._widgets_created:
            return

        self._widgets_created = True

        # Start populating the contents _after_ returning from the "realize".
        # Otherwise this widget is not shown for a long time while its children
        # are being created.
        GLib.timeout_add(
            priority=GLib.PRIORITY_DEFAULT,
            function=self._populate_items,
            interval=50
        )

    def _populate_items(self):
        for item in self._items:
            widget = self._create_item_func(item)
            self.add(widget)
            while (Gtk.events_pending()):
                Gtk.main_iteration()
            if self._removed or not self.get_realized():
                break

        return False

    def _on_unrealize(self, *args):
        self._removed = True
        for child in self.contents.get_children():
            child.destroy()
            while (Gtk.events_pending()):
                Gtk.main_iteration()

    def add(self, widget):
        self.contents.add(widget)

    def set_title(self, text):
        self.title.set_label(text)
