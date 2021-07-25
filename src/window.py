# window.py
#
# Copyright 2021 Doychin Atanasov
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

import sys
import gi
gi.require_version('Handy', '1')
gi.require_version('Gst', '1.0')

from gi.repository import Gtk, Handy, Gst


@Gtk.Template(resource_path='/com/doycho/euterpe/gtk/window.ui')
class EuterpeGtkWindow(Gtk.ApplicationWindow):
    __gtype_name__ = 'EuterpeGtkWindow'

    Handy.init()

    squeezer = Gtk.Template.Child()
    headerbar_switcher = Gtk.Template.Child()
    bottom_switcher = Gtk.Template.Child()

    about_gtk_version = Gtk.Template.Child()
    about_gstreamer_version = Gtk.Template.Child()
    about_python_version = Gtk.Template.Child()

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        self.squeezer.connect("notify::visible-child",self.on_headerbar_squeezer_notify)
        Gst.init(None)

        self.populate_about()


    def on_headerbar_squeezer_notify(self, squeezer, event):
	    child = squeezer.get_visible_child()
	    self.bottom_switcher.set_reveal(child != self.headerbar_switcher)


    def populate_about(self):
        self.about_python_version.set_label('{}.{}.{}'.format(
            sys.version_info.major,
            sys.version_info.minor,
            sys.version_info.micro,
        ))

        gstVer = Gst.version()
        self.about_gstreamer_version.set_label('{}.{}.{}'.format(
            gstVer.major,
            gstVer.minor,
            gstVer.micro
        ))

        self.about_gtk_version.set_label('{}.{}.{}'.format(
            Gtk.get_major_version(),
            Gtk.get_minor_version(),
            Gtk.get_micro_version()
        ))
