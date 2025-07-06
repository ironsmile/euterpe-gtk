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

import gi
import platform
import random
import sys

gi.require_version('Gtk', '3.0')
gi.require_version('Gst', '1.0')
gi.require_version('Handy', '1')
gi.require_version('GLib', '2.0')
gi.require_version('Soup', '2.4')

from gi.repository import Gtk, Gio, Gst, Gdk, GLib
from euterpe_gtk.player import Player
from euterpe_gtk.service import Euterpe
from euterpe_gtk.widgets.window import EuterpeGtkWindow
from euterpe_gtk.utils import config_file_name, state_file_name
from euterpe_gtk.state_storage import StateStorage

import euterpe_gtk.http as http
import euterpe_gtk.log as log

HELP_URL = "https://listen-to-euterpe.eu/docs"

class Application(Gtk.Application):
    def __init__(self, version):
        super().__init__(application_id='com.doycho.euterpe.gtk',
                         flags=Gio.ApplicationFlags.FLAGS_NONE)
        Gst.init(None)
        http.Init()

        random.seed()
        self._version = version
        self._euterpe = Euterpe(version)
        self._player = Player(self._euterpe)
        self._mpris = None
        self._config_store = None
        self._cache_store = None

        if platform.system() == "Linux":
            self._set_up_mpris()

        self.props.register_session = True
        self.connect("shutdown", self._on_shutdown)
        self.connect("query-end", self._on_query_end)

        GLib.set_application_name("Euterpe")

    def do_activate(self):
        win = self.props.active_window
        if win:
            win.present()
            return

        self._set_actions()

        win = EuterpeGtkWindow(application=self)
        win.present()

    def _set_up_mpris(self):
        from euterpe_gtk.mpris import MPRIS

        try:
            self._mpris = MPRIS(self)
        except Exception:
            sys.excepthook(*sys.exc_info())
            log.warning("Setting up MPRIS interface failed but error is ignored")
        else:
            log.debug("MPRIS up and running")

    def _set_actions(self):
        actions = {
            "quit": self.on_quit,
            "logout": self.on_logout,
            "next_song": self.on_next_song,
            "previous_song": self.on_previous_song,
            "playpause": self.on_playpause,
            "toggle_repeat": self.on_toggle_repeat,
            "toggle_shuffle": self.on_toggle_shuffle,
            "reference": self.on_show_help,
            "about_dialog": self.on_about_dialog,
        }

        for action_name, handler in actions.items():
            action = Gio.SimpleAction.new(action_name, None)
            action.connect("activate", handler)
            self.add_action(action)

        self.set_accels_for_action("app.quit", ["<Control>Q"])
        self.set_accels_for_action("app.playpause", ["<Control>K"])
        self.set_accels_for_action("app.next_song", ["<Control>N"])
        self.set_accels_for_action("app.previous_song", ["<Control>B"])
        self.set_accels_for_action("app.toggle_repeat", ["<Control>R"])
        self.set_accels_for_action("app.toggle_shuffle", ["<Control>H"])
        self.set_accels_for_action("app.reference", ["F1"])

    def on_logout(self, *args):
        win = self.props.active_window
        if win and hasattr(win, "logout"):
            win.logout()

    def on_quit(self, *args):
        # Nothingi interesting to do. Everything is already hooked up with the
        # "shutdown" signal.
        self.quit()

    def on_next_song(self, *args):
        self._player.next()

    def on_previous_song(self, *args):
        self._player.previous()

    def on_playpause(self, *args):
        if self._player.is_playing():
            self._player.pause()
        else:
            self._player.play()

    def on_toggle_repeat(self, *args):
        self._player.toggle_repeat()

    def on_toggle_shuffle(self, *args):
        self._player.toggle_shuffle()

    def on_show_help(self, *args):
        parent_win = self.props.active_window
        Gtk.show_uri_on_window(parent_win, HELP_URL, Gdk.CURRENT_TIME)

    def on_about_dialog(self, *args):
        dialog = Gtk.AboutDialog(
            authors=[
                "Doychin Atanasov <ironsmile@gmail.com>",
                "dydyamotya <matderevenayv@yandex.ru>",
            ],
            artists=[
                "Iconnice",
            ],
            license_type=Gtk.License.GPL_3_0_ONLY,
            copyright="© 2021-2025 Doychin Atanasov",
            version=self._version,
            website="https://listen-to-euterpe.eu/",
            website_label="Vist the Euterpe website",
            comments="Desktop client for the\nEuterpe music streaming server.",
            logo_icon_name="com.doycho.euterpe.gtk",
        )
        dialog.show()

    def get_player(self):
        return self._player

    def get_euterpe(self):
        return self._euterpe

    def get_config_store(self):
        if self._config_store is None:
            self._config_store = StateStorage(config_file_name(), "config")
            log.debug("reading the config store from disk...")
            self._config_store.load()

        return self._config_store

    def get_cache_store(self):
        if self._cache_store is None:
            self._cache_store = StateStorage(state_file_name(), "app_state")
            log.debug("reading the cache store from disk...")
            self._cache_store.load()

        return self._cache_store

    def _store_app_state(self):
        win = self.props.active_window
        if win and hasattr(win, "store_state"):
            try:
                win.store_state()
            except Exception as err:
                log.error("Error storing window state: {}", err)

        if self._cache_store is not None:
            self._cache_store.save()
            log.message("state saved")

    def _on_shutdown(self, *args):
        self._store_app_state()

    def _on_query_end(self, *args):
        cookie = self.inhibit(
            self.props.active_window,
            Gtk.ApplicationInhibitFlags.LOGOUT,
            "saving app state"
        )
        try:
            self._store_app_state()
        except Exception as err:
            log.error("Error saving the state: {}", err)
        self.uninhibit(cookie)

def main(version):
    app = Application(version)
    return app.run(sys.argv)
