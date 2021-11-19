from gi.repository import Gtk


@Gtk.Template(resource_path='/com/doycho/euterpe/gtk/ui/simple-list.ui')
class EuterpeSimpleList(Gtk.Viewport):
    __gtype_name__ = 'EuterpeSimpleList'

    __gsignals__ = {}

    contents = Gtk.Template.Child()
    title = Gtk.Template.Child()

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def add(self, widget):
        self.contents.add(widget)

    def set_title(self, text):
        self.title.set_label(text)
