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
import threading
import keyring

gi.require_version('Handy', '1')
gi.require_version('Gst', '1.0')
gi.require_version('GLib', '2.0')

from gi.repository import GObject, GLib, Gtk, Handy, Gst
from .player import Player
from .service import Euterpe
from .utils import emit_signal, config_file_name



SIGNAL_STATE_RESTORED = "state-restored"


@Gtk.Template(resource_path='/com/doycho/euterpe/gtk/window.ui')
class EuterpeGtkWindow(Gtk.ApplicationWindow):
    __gtype_name__ = 'EuterpeGtkWindow'

    __gsignals__ = {
        SIGNAL_STATE_RESTORED: (GObject.SignalFlags.RUN_FIRST, None, ()),
    }

    Handy.init()

    squeezer = Gtk.Template.Child()
    headerbar_switcher = Gtk.Template.Child()
    bottom_switcher = Gtk.Template.Child()

    about_gtk_version = Gtk.Template.Child()
    about_gstreamer_version = Gtk.Template.Child()
    about_python_version = Gtk.Template.Child()

    input_track_url = Gtk.Template.Child()
    play_button = Gtk.Template.Child()
    track_progess = Gtk.Template.Child()

    logged_in_screen = Gtk.Template.Child()
    login_scroll_view = Gtk.Template.Child()
    app_stack = Gtk.Template.Child()
    login_button = Gtk.Template.Child()
    logout_button = Gtk.Template.Child()

    login_spinner = Gtk.Template.Child()
    server_url = Gtk.Template.Child()
    service_username = Gtk.Template.Child()
    service_password = Gtk.Template.Child()
    service_password_show_toggle = Gtk.Template.Child()

    main_search_box = Gtk.Template.Child()

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        self._play_uri = None
        self._token = None

        self._player = None
        self._euterpe = None
        self._remote_address = None

        self.squeezer.set_visible(False)

        self.connect("show", self.on_activate)
        self.connect("state-restored", self.on_state_restored)

    def on_activate(self, *args):
        self.squeezer.connect(
            "notify::visible-child",
            self.on_headerbar_squeezer_notify
        )
        self.play_button.connect(
            "clicked",
            self.on_play_button_clicked
        )
        self.input_track_url.connect(
            "changed",
            self.on_track_changed
        )
        self.track_progess.connect(
            "change-value",
            self.on_seek
        )
        self.app_stack.connect(
            "notify::visible-child",
            self.on_login_status_change
        )
        self.login_button.connect("clicked", self.on_login_button)
        self.logout_button.connect("clicked", self.on_logout_button)
        self.main_search_box.connect("search-changed", self.on_search)

        self.service_password_show_toggle.bind_property(
            'active',
            self.service_password, 'visibility',
            GObject.BindingFlags.SYNC_CREATE
        )

        Gst.init(None)
        self.populate_about()

        self.track_progess.set_range(0, 1)

        self._config_file = config_file_name()

        t = threading.Thread(
            target=self.restore_state,
            name="RestoreStateThread"
        )
        t.daemon = True
        t.start()

    def restore_state(self):
        '''
            Restores the application state from the last time it was
            run.
        '''
        try:
            self._restore_address()
            self._restore_token()
        except Exception as err:
            print("Restoring state failed: {}".format(err))
        finally:
            emit_signal(self, SIGNAL_STATE_RESTORED)

    def store_remote_address(self, address):
        kf = GLib.KeyFile.new()
        kf.set_string("config", "address", address)

        try:
            kf.save_to_file(self._config_file)
        except GLib.Error as err:
            print('Saving config file failed: {}'.format(err))

    def _restore_address(self):
        kf = GLib.KeyFile.new()
        try:
            kf.load_from_file(self._config_file, GLib.KeyFileFlags.NONE)
        except GLib.Error as err:
            print('Loading config file ({}) failed: {}'.format(
                self._config_file,
                err,
            ))
            return

        address = kf.get_string("config", "address")
        if address == "":
            return

        self._remote_address = address

    def _restore_token(self):
        token = keyring.get_password("euterpe", "token")

        if token == "":
            print("no token found in the keyring")
            return

        self._token = token

    def change_progress(self, prog):
        if prog < 0:
            prog = 0
        if prog > 1:
            prog = 1
        self.track_progess.set_value(prog)

    def show_login_loading(self):
        self.login_spinner.props.active = True

    def hide_login_loading(self):
        self.login_spinner.props.active = False

    def _toggle_playing_state(self, button):
        print("executing on toggle playing state button")

        if self._player is None:
            # Nothing to do here, go away!
            return

        if self._player.is_playing():
            self._player.pause()
        else:
            self._player.play()

    def _query_progress(self):
        if self._player is None or not self._player.is_playing():
            print("stopping progress timeout callback")
            return False

        progress = self._player.get_progress()
        if progress is None:
            print("could not yet obtain progress")
            return True

        self.change_progress(progress)
        return True

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

    def on_state_restored(self, _):
        '''
            At this point the state of the application has been restored.
            Remove the loading spinner and show the appropriate screen.

            At the moment the supported restore state is:

            * Remote Euterpe address from GSettings
            * Euterpe token from the OS keyring
        '''

        screen = self.login_scroll_view
        if self._remote_address is not None:
            screen = self.logged_in_screen

        self.app_stack.set_visible_child(screen)

    def on_track_changed(self, entry):
        text = entry.get_text()
        if len(text) > 0:
            self._play_uri = text
        else:
            self._play_uri = None

    def on_login_status_change(self, stack, event):
        show_squeezer = (self.logged_in_screen == stack.get_visible_child())
        self.squeezer.set_visible(show_squeezer)

    def on_login_button(self, buttn):
        remote_url = self.server_url.get_text().strip()

        if remote_url == "":
            print('Empty URL is not accepted')
            return

        if not remote_url.startswith("http://") and \
                not remote_url.startswith("https://"):
            remote_url = 'https://{}'.format(remote_url)

        self.show_login_loading()

        username = self.service_username.get_text().strip()
        password = self.service_password.get_text()

        if len(username) == 0:
            username = None
            password = None

        try:
            token = Euterpe.check_login_credentials(
                remote_url,
                username,
                password,
            )
        except Exception as err:
            print("error loggin in: {}".format(err))
        else:
            self._token = token
            self._remote_address = remote_url

            if token is not None:
                keyring.set_password("euterpe", "token", token)
            else:
                keyring.set_password("euterpe", "token", "")

            self.store_remote_address(remote_url)

            # Clean-up the username and password!
            self.service_password.set_text("")
            self.service_username.set_text("")

            self.app_stack.set_visible_child(
                self.logged_in_screen
            )
        finally:
            self.hide_login_loading()

    def on_logout_button(self, button):
        self._token = None
        self._remote_address = None

        keyring.set_password("euterpe", "token", "")
        self.store_remote_address("")

        self.app_stack.set_visible_child(
            self.login_scroll_view
        )

    def on_headerbar_squeezer_notify(self, squeezer, event):
        child = squeezer.get_visible_child()
        self.bottom_switcher.set_reveal(child != self.headerbar_switcher)

    def on_play_button_clicked(self, button):
        print("play button clicked")

        if self._play_uri is None:
            print("no play URI!")
            return

        if self._player is not None:
            self._toggle_playing_state(button)
            return

        self._player = Player(self._play_uri, self._token)
        self._player.connect("state-changed",
                             self.on_player_state_changed)
        self._player.play()

    def on_seek(self, slider, scroll, value):
        if scroll != Gtk.ScrollType.JUMP:
            return False

        if self._player is None:
            return

        self._player.seek(value)
        return False

    def on_player_state_changed(self, player):
        if player is not self._player:
            return

        if player.is_playing():
            self.play_button.set_label("Pause")
            GLib.timeout_add(
                priority=GLib.PRIORITY_DEFAULT,
                function=self._query_progress,
                interval=1000
            )
        else:
            self.play_button.set_label("Play")

        if player.has_ended():
            self._player = None
            self.change_progress(0)

    def on_search(self, search_entry):
        search_term = search_entry.get_text()
        if search_term == "":
            return

        print("searching for stuff: {}".format(search_term))
