# image_card.py
#
# Copyright 2026 Doychin Atanasov
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

from gi.repository import Gtk
import euterpe_gtk.log as log


@Gtk.Template(resource_path='/com/doycho/euterpe/gtk/ui/image-card.ui')
class EuterpeImageCard(Gtk.Button):
    __gtype_name__ = 'EuterpeImageCard'

    __gsignals__ = {}

    image = Gtk.Template.Child()
    title = Gtk.Template.Child()

    def __init__(self, title, icon, on_click=None, action=None, **kwargs):
        super().__init__(**kwargs)

        self.title.set_label(title)
        self.image.set_from_icon_name(icon, Gtk.IconSize.LARGE_TOOLBAR)

        if on_click is not None:
            self.connect("clicked", on_click)

        if action is not None:
            self.set_action_name(action)
