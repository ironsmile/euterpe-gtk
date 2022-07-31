# paginated_box_list.py
#
# Copyright 2022 Doychin Atanasov
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

from gi.repository import Gtk, GLib

import urllib.parse


@Gtk.Template(resource_path='/com/doycho/euterpe/gtk/ui/paginated-box-list.ui')
class PaginatedBoxList(Gtk.ScrolledWindow):
    '''
    PaginatedBoxList is a widget which gets shows a paginated list of homogenous items.
    '''

    __gtype_name__ = 'PaginatedBoxList'

    __gsignals__ = {}

    flow_container = Gtk.Template.Child()
    title = Gtk.Template.Child()
    page_label = Gtk.Template.Child()

    button_next_page = Gtk.Template.Child()
    button_previous_page = Gtk.Template.Child()

    def __init__(self, euterpe, list_type, create_item_func, **kwargs):
        super().__init__(**kwargs)

        self._list_type = list_type
        self._euterpe = euterpe
        self._create_item_func = create_item_func
        self._widgets_created = False
        self._removed = False

        self._next_page = None
        self._previous_page = None
        self._current_page = '1'

        self.connect("realize", self._create_widgets)
        self.connect("unrealize", self._on_unrealize)

        self.button_next_page.connect(
            "clicked",
            self._on_next_button
        )

        self.button_previous_page.connect(
            "clicked",
            self._on_previous_button
        )

    def _create_widgets(self, *args):
        if self._widgets_created:
            return

        self._widgets_created = True

        uri = self._euterpe.get_browse_uri(self._list_type)
        if uri is None:
            print("the returned browse_url address was None, skipping creating widgets")
            return

        self._euterpe.make_request(uri, self._on_browse_result_callback)

    def _on_browse_result_callback(self, status, body):
        if status != 200:
            self._show_error("Error, HTTP response code {}".format(status))
            return

        if body is None or 'data' not in body:
            self._show_error("Unexpected response from server.")
            return

        if 'previous' in body and body['previous'] != "":
            self._previous_page = body['previous']
            self.button_previous_page.set_sensitive(True)
        else:
            self._previous_page = None
            self.button_previous_page.set_sensitive(False)

        if 'next' in body and body['next'] != "":
            self._next_page = body['next']
            self.button_next_page.set_sensitive(True)
        else:
            self._next_page = None
            self.button_next_page.set_sensitive(False)

        all_pages = '<unknown>'

        if 'pages_count' in body:
            all_pages = body['pages_count']

        page_text = 'Page {} of {}'.format(
            self._current_page,
            all_pages
        )

        self.page_label.set_text(page_text)

        self._remove_items()
        self._populate_items(body['data'])

    def _populate_items(self, items):
        for item in items:
            widget = self._create_item_func(item)
            self.add(widget)
            while (Gtk.events_pending()):
                Gtk.main_iteration()
            if self._removed or not self.get_realized():
                break

        return False

    def _on_next_button(self, btn):
        if self._next_page is None:
            return

        self._set_page_by_url(self._next_page)
        self._euterpe.make_request(self._next_page, self._on_browse_result_callback)

    def _on_previous_button(self, btn):
        if self._previous_page is None:
            return

        self._set_page_by_url(self._previous_page)
        self._euterpe.make_request(self._previous_page, self._on_browse_result_callback)

    def _set_page_by_url(self, url):
        parsed = urllib.parse.urlparse(url)
        qparams =  urllib.parse.parse_qs(parsed.query)
        if 'page' not in qparams or len(qparams['page']) < 1:
            slef._current_page = '<unknown>'
            return

        self._current_page = qparams['page'].pop()

    def _on_unrealize(self, *args):
        self._removed = True
        self._remove_items()

    def _remove_items(self):
        for child in self.flow_container.get_children():
            child.destroy()
            while (Gtk.events_pending()):
                Gtk.main_iteration()

    def add(self, widget):
        self.flow_container.add(widget)

    def set_title(self, text):
        self.title.set_label(text)
