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

from gi.repository import GObject, Gtk, GLib

import urllib.parse
import euterpe_gtk.log as log


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
    loading_indicator = Gtk.Template.Child()
    content = Gtk.Template.Child()
    buttons_container = Gtk.Template.Child()
    browse_error = Gtk.Template.Child()

    button_next_page = Gtk.Template.Child()
    button_previous_page = Gtk.Template.Child()

    button_first_page = Gtk.Template.Child()
    button_last_page = Gtk.Template.Child()

    sorting_type_select = Gtk.Template.Child()
    sorting_direction_select = Gtk.Template.Child()
    sort_type_row = Gtk.Template.Child()
    sort_direction_row = Gtk.Template.Child()

    def __init__(self, app, list_type, create_item_func, **kwargs):
        super().__init__(**kwargs)

        self._list_type = list_type
        self._euterpe = app.get_euterpe()
        self._cfg_store = app.get_cache_store()
        self._create_item_func = create_item_func
        self._widgets_created = False
        self._removed = False

        self._next_page = None
        self._previous_page = None
        self._current_page = 1
        self._pages_count = None

        self._default_order_by = "name"
        self._default_order = "asc"

        self._cfg_namespace = "browse_sorting"
        self._browse_cfg = self._cfg_store.get_object(self._list_type, self._cfg_namespace)
        if self._browse_cfg is None:
            self._browse_cfg = {
                "order_by": self._default_order_by,
                "order": self._default_order,
            }

        self.connect("realize", self._create_widgets)
        self.connect("destroy", self._on_destroy)

        self.button_next_page.connect(
            "clicked",
            self._on_next_button
        )

        self.button_previous_page.connect(
            "clicked",
            self._on_previous_button
        )

        self.button_first_page.connect(
            "clicked",
            self._on_first_page_button
        )

        self.button_last_page.connect(
            "clicked",
            self._on_last_page_button
        )

        self.loading_indicator.bind_property(
            'active',
            self.content, 'visible',
            GObject.BindingFlags.INVERT_BOOLEAN
        )

        self.loading_indicator.bind_property(
            'active',
            self.buttons_container, 'visible',
            GObject.BindingFlags.INVERT_BOOLEAN
        )

        for sort_type in order_by_list_type.get(list_type, []):
            self.sorting_type_select.append(sort_type, order_human_name.get(
                sort_type, sort_type.title()
            ))
            if sort_type == self.get_order_by():
                self.sorting_type_select.set_active_id(sort_type)

        self.sort_type_row.set_activatable_widget(self.sorting_type_select)
        self.sort_type_row.add(self.sorting_type_select)
        self.sorting_type_select.show()

        self.sorting_direction_select.set_active_id(self.get_order())

        self.sort_direction_row.set_activatable_widget(self.sorting_direction_select)
        self.sort_direction_row.add(self.sorting_direction_select)
        self.sorting_direction_select.show()

        self.sorting_direction_select.connect(
            "changed",
            self._on_sorting_changed
        )

        self.sorting_type_select.connect(
            "changed",
            self._on_sorting_changed
        )

    def _store_config(self):
        """
        Stores the config for browsing into the configuration storage object which
        is saved on application exit.
        """
        self._cfg_store.set_object(self._list_type, self._browse_cfg, self._cfg_namespace)
        self._cfg_store.save()

    def get_order_by(self):
        return self._browse_cfg.get("order_by", self._default_order_by)

    def get_order(self):
        return self._browse_cfg.get("order", self._default_order)

    def _create_widgets(self, *args):
        if self._widgets_created:
            return

        self._widgets_created = True

        self.loading_indicator.start()
        self.loading_indicator.set_visible(True)
        self._remove_items()

        uri = self._euterpe.get_browse_uri(self._list_type,
            order_by=self.get_order_by(),
            order=self.get_order())
        if uri is None:
            log.debug("the returned browse_url address was None, skipping creating widgets")
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
            all_pages = int(body['pages_count'])
            self._pages_count = all_pages

        if self.get_order_by() == "random":
            # There is no point of having pages for a random sorting.
            self._current_page = 1
            self._pages_count = 1
            self._previous_page = None
            self._next_page = None
            self.button_next_page.set_sensitive(False)
            self.button_previous_page.set_sensitive(False)

        self.button_first_page.set_sensitive(self._current_page != 1)
        self.button_last_page.set_sensitive(self._current_page != self._pages_count)

        page_text = 'Page {} of {}'.format(
            self._current_page,
            self._pages_count
        )

        self.page_label.set_text(page_text)

        self.loading_indicator.stop()
        self.loading_indicator.set_visible(False)

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

    def _on_sorting_changed(self, comboBox):
        self._browse_cfg["order_by"] = self.sorting_type_select.get_active_id()
        self._browse_cfg["order"] = self.sorting_direction_select.get_active_id()
        self._store_config()

        uri = self._euterpe.get_browse_uri(self._list_type,
            order_by=self.get_order_by(),
            order=self.get_order(),
            page=1)
        if uri is None:
            log.debug("the returned browse_url address was None, skipping creating widgets")
            return

        self.loading_indicator.start()
        self.loading_indicator.set_visible(True)
        self._remove_items()

        self._current_page = 1
        self._euterpe.make_request(uri, self._on_browse_result_callback)

    def _on_next_button(self, btn):
        if self._next_page is None:
            return

        self.loading_indicator.start()
        self.loading_indicator.set_visible(True)
        self._remove_items()

        self._set_page_by_url(self._next_page)
        self._euterpe.make_request(self._next_page, self._on_browse_result_callback)

    def _on_previous_button(self, btn):
        if self._previous_page is None:
            return

        self.loading_indicator.start()
        self.loading_indicator.set_visible(True)
        self._remove_items()

        self._set_page_by_url(self._previous_page)
        self._euterpe.make_request(self._previous_page, self._on_browse_result_callback)

    def _on_first_page_button(self, btn):
        self.loading_indicator.start()
        self.loading_indicator.set_visible(True)
        self._remove_items()

        uri = self._euterpe.get_browse_uri(self._list_type,
            order_by=self.get_order_by(),
            order=self.get_order(),
            page=1)
        if uri is None:
            log.debug("the returned URI address was None, stopped loading first page")
            return

        self._current_page = 1
        self._euterpe.make_request(uri, self._on_browse_result_callback)

    def _on_last_page_button(self, btn):
        if self._pages_count is None:
            return

        self.loading_indicator.start()
        self.loading_indicator.set_visible(True)
        self._remove_items()

        uri = self._euterpe.get_browse_uri(self._list_type,
            order_by=self.get_order_by(),
            order=self.get_order(),
            page=self._pages_count)
        if uri is None:
            log.debug("the returned URI address was None, stopped loading last page")
            return
        self._current_page = self._pages_count
        self._euterpe.make_request(uri, self._on_browse_result_callback)

    def _set_page_by_url(self, url):
        parsed = urllib.parse.urlparse(url)
        qparams =  urllib.parse.parse_qs(parsed.query)
        if 'page' not in qparams or len(qparams['page']) < 1:
            self._current_page = '<unknown>'
            return

        self._current_page = int(qparams['page'].pop())

    def _on_destroy(self, *args):
        self._removed = True
        self._remove_items()

    def _remove_items(self):
        for child in self.flow_container.get_children():
            child.destroy()
            while (Gtk.events_pending()):
                Gtk.main_iteration()

    def _show_error(self, text):
        log.warning(text)
        self.browse_error.set_description(text)

        for child in self.content.get_children():
            child.destroy()

        self.content.add(self.browse_error)

        self.loading_indicator.stop()
        self.loading_indicator.set_visible(False)

    def add(self, widget):
        self.flow_container.add(widget)

    def set_title(self, text):
        self.title.set_label(text)

order_by_list_type = {
    "song": ["name", "id", "year", "random", "frequency", "recency"],
    "album": ["name", "id", "year", "random", "frequency", "recency"],
    "artist": ["name", "id", "random"],
}

order_human_name = {
    "id": "Time Added",
    "name": "Name",
    "year": "Year",
    "random": "Random",
    "frequency": "Frequently Played",
    "recency": "Recently Played",
}
