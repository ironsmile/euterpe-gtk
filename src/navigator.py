
class Navigator(object):
    '''
        Navigator is a navigation primitive which could be used to show a
        GTK widget on top of certain stack.
    '''

    def __init__(self, gtk_stack, root_screen):
        self._stack = gtk_stack
        self._root_screen = root_screen

    def show_screen(self, widget):
        self._stack.add(widget)
        self._stack.set_visible_child(widget)

    def go_back(self):
        """
        Removes the visible child and replaces is with the one "below" it in the stack.
        If there is only one child it does nothing.

        Returns the removed child. None if nothing was done.
        """
        children = self._stack.get_children()
        if len(children) <= 1:
            return

        visible_child = self._stack.get_visible_child()
        previous_child = children[-2]
        self._stack.set_visible_child(previous_child)
        self._stack.remove(visible_child)
        return visible_child

    def set_root_scree(self, widget):
        self._root_screen = widget

    def is_root_screen(self):
        """
        Returns true when the currently visible screen is the stack's root screen.
        """
        return self._stack.get_visible_child() is self._root_screen

    def connect_stack_change(self, callback):
        self._stack.connect("notify::visible-child", callback, self)
