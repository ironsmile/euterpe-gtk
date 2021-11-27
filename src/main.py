# main.py
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

gi.require_version('Gtk', '3.0')

from gi.repository import Gtk, Gio
from .window import EuterpeGtkWindow


class Application(Gtk.Application):
    def __init__(self, version):
        super().__init__(application_id='com.doycho.euterpe.gtk',
                         flags=Gio.ApplicationFlags.FLAGS_NONE)
        self._version = version
        self._window = None

    def do_activate(self):
        win = self.props.active_window
        if win:
            win.present()
            return

        self._set_actions()

        self._window = EuterpeGtkWindow(self._version, application=self)
        self._window.present()

    def _set_actions(self):
        action = Gio.SimpleAction.new("quit", None)
        action.connect("activate", self.on_quit)
        self.add_action(action)

        self.set_accels_for_action("app.quit", ["<Control>Q"])

    def on_quit(self, *args):
        self.quit()


def main(version):
    app = Application(version)
    return app.run(sys.argv)
