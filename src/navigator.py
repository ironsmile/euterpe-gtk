
class Navigator(object):
    '''
        Navigator is a navigation primitive which could be used to show a
        GTK widget on top of certain stack.
    '''

    def __init__(self, gtk_stack):
        self._stack = gtk_stack

    def show_screen(self, widget):
        self._stack.add(widget)
        self._stack.set_visible_child(widget)
