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
import threading
import keyring
import json

from gi.repository import GObject, Gtk, Handy, Gst, Gdk
from .service import Euterpe
from .utils import emit_signal, config_file_name, state_file_name
from .browse_screen import EuterpeBrowseScreen
from .search_screen import EuterpeSearchScreen
from .home_screen import EuterpeHomeScreen
from .mini_player import EuterpeMiniPlayer
from .state_storage import StateStorage
from .player_ui import EuterpePlayerUI


SIGNAL_STATE_RESTORED = "state-restored"


@Gtk.Template(resource_path='/com/doycho/euterpe/gtk/ui/window.ui')
class EuterpeGtkWindow(Handy.ApplicationWindow):
    __gtype_name__ = 'EuterpeGtkWindow'

    __gsignals__ = {
        SIGNAL_STATE_RESTORED: (GObject.SignalFlags.RUN_FIRST, None, ()),
    }

    Handy.init()

    browsing_ui = Gtk.Template.Child()
    main_leaflet_separator = Gtk.Template.Child()
    squeezer = Gtk.Template.Child()
    headerbar_switcher = Gtk.Template.Child()
    bottom_switcher = Gtk.Template.Child()
    main_stack = Gtk.Template.Child()
    title_tab_bar = Gtk.Template.Child()
    back_button_position = Gtk.Template.Child()

    search_screen = Gtk.Template.Child()
    browse_screen = Gtk.Template.Child()
    home_screen = Gtk.Template.Child()

    about_gtk_version = Gtk.Template.Child()
    about_gstreamer_version = Gtk.Template.Child()
    about_python_version = Gtk.Template.Child()
    about_euterpe_version = Gtk.Template.Child()
    about_libhandy_version = Gtk.Template.Child()

    logged_in_screen = Gtk.Template.Child()
    login_scroll_view = Gtk.Template.Child()
    app_stack = Gtk.Template.Child()
    login_button = Gtk.Template.Child()

    volume_adjustment = Gtk.Template.Child()
    main_volume_slider = Gtk.Template.Child()

    login_spinner = Gtk.Template.Child()
    login_failed_indicator = Gtk.Template.Child()
    server_url = Gtk.Template.Child()
    service_username = Gtk.Template.Child()
    service_password = Gtk.Template.Child()
    service_password_show_toggle = Gtk.Template.Child()

    miniplayer_position = Gtk.Template.Child()

    def __init__(self, appVersion, **kwargs):
        super().__init__(**kwargs)

        self._appVersion = appVersion
        self._token = None
        self._state_restored = False

        app = self.get_application()

        self._euterpe = app.get_euterpe()
        self._player = app.get_player()
        self._remote_address = None
        self._search_widget = None

        self._current_width = None
        self._current_height = None
        self._is_maximized = None

        self.squeezer.set_visible(False)

        self._config_store = StateStorage(config_file_name(), "config")
        self._cache_store = StateStorage(state_file_name(), "app_state")
        print("reading key-value files from disk...")
        self._config_store.load()
        self._cache_store.load()

        print("restoring window state...")
        self._restore_window_state()
        self._restore_navigation_state()

        self.connect("show", self.on_activate)
        self.connect("size-allocate", self._on_size_allocate)
        self.connect("window-state-event", self._on_window_state_event)
        self.connect(SIGNAL_STATE_RESTORED, self.on_state_restored)

    def get_player(self):
        return self._player

    def get_euterpe(self):
        return self._euterpe

    def on_activate(self, *args):
        self.squeezer.connect(
            "notify::visible-child",
            self.on_headerbar_squeezer_notify
        )
        self.app_stack.connect(
            "notify::visible-child",
            self.on_login_status_change
        )
        self.main_stack.connect(
            "notify::visible-child",
            self.on_main_stack_change
        )
        self.login_button.connect("clicked", self.on_login_button)

        self.main_volume_slider.connect(
            "change-value",
            self._on_volume_changed
        )

        self.service_password_show_toggle.bind_property(
            'active',
            self.service_password, 'visibility',
            GObject.BindingFlags.SYNC_CREATE
        )

        for obj in [
            self.server_url, self.login_button, self.service_username,
            self.service_password, self.service_password_show_toggle,
        ]:
            self.login_spinner.bind_property(
                'active',
                obj, 'sensitive',
                GObject.BindingFlags.INVERT_BOOLEAN
            )

        self.populate_about()

        browse_screen = EuterpeBrowseScreen()
        self.browse_screen.add(browse_screen)
        browse_screen.connect(
            'search-button-clicked',
            self.open_search_screen
        )

        self._search_widget = EuterpeSearchScreen(self)
        self.search_screen.add(self._search_widget)

        self._player_ui = EuterpePlayerUI()
        self.logged_in_screen.add(self._player_ui)
        self.logged_in_screen.child_set(self._player_ui, name="player_ui")

        pan_down_btn = self._player_ui.get_pan_down_button()

        self._home_widget = EuterpeHomeScreen(self)
        self.home_screen.add(self._home_widget)

        mini_player = EuterpeMiniPlayer(self._player)
        mini_player.connect(
            "pan-up",
            self._on_show_big_player
        )
        self.miniplayer_position.add(mini_player)
        self._player_ui.set_player(self._player)

        self.logged_in_screen.bind_property(
            'folded',
            self.miniplayer_position, 'visible',
            GObject.BindingFlags.SYNC_CREATE
        )

        self.logged_in_screen.bind_property(
            'folded',
            pan_down_btn, 'visible',
            GObject.BindingFlags.SYNC_CREATE
        )

        self.logged_in_screen.bind_property(
            'folded',
            self.main_leaflet_separator, 'visible',
            GObject.BindingFlags.INVERT_BOOLEAN
        )

        self._player_ui.connect(
            "pan-down",
            self._on_hide_big_player
        )

        self.connect("delete-event", self._on_program_exit)

        self._player.connect("volume-changed", self._on_player_volume_changed)

        print("staring RestoreStateThread")
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
            print("restoring address...")
            self._restore_address()
            print("restoring token...")
            self._restore_token()
            print("setting up Euterpe instance...")
            self._euterpe.set_address(self._remote_address)
            self._euterpe.set_token(self._token)
            print("restoring search state...")
            self._search_widget.restore_state(self._cache_store)
            print("restoring playing state...")
            self._player.restore_state(self._cache_store)

            if self._remote_address is not None:
                print("restoring recently added...")
                self._home_widget.restore_state(self._cache_store)
        except Exception as err:
            print("Restoring state failed: {}".format(err))
        finally:
            self._state_restored = True
            emit_signal(self, SIGNAL_STATE_RESTORED)

    def store_remote_address(self, address):
        self._config_store.set_string("address", address)
        self._config_store.save()

    def _restore_address(self):
        address = self._config_store.get_string("address")

        if address == "":
            return

        self._remote_address = address

    def _restore_token(self):
        token = keyring.get_password("euterpe", "token")

        if token == "":
            print("no token found in the keyring")
            return

        self._token = token

    def show_login_loading(self):
        self.login_spinner.props.active = True

    def hide_login_loading(self):
        self.login_spinner.props.active = False

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

        self.about_libhandy_version.set_label("unknown")

        self.about_euterpe_version.set_label(self._appVersion)

    def on_state_restored(self, _):
        '''
            At this point the state of the application has been restored.
            Remove the loading spinner and show the appropriate screen.

            At the moment the supported restore state is:

            * Remote Euterpe address from GSettings
            * Euterpe token from the OS keyring
        '''
        print("state restored")

        screen = self.login_scroll_view
        if self._remote_address is not None:
            screen = self.logged_in_screen

        self.app_stack.set_visible_child(screen)
        self.set_back_button_to_visible_child(self.main_stack)

    def on_main_stack_change(self, stack, event):
        self.set_back_button_to_visible_child(stack)

    def set_back_button_to_visible_child(self, stack):
        self.back_button_position.foreach(self.back_button_position.remove)
        visible_child = stack.get_visible_child()
        if issubclass(type(visible_child), Gtk.Container):
            grand_children = visible_child.get_children()
            if len(grand_children) == 1:
                screen = grand_children[0]
                if hasattr(screen, 'get_back_button'):
                    back_button = screen.get_back_button()
                    self.back_button_position.add(back_button)

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

        Euterpe.check_login_credentials(
            remote_url,
            self._on_login_request_response,
            username,
            password,
            remote_url,
        )

    def _on_login_request_response(self, status, data, remote_url):
        self.hide_login_loading()

        if status != 200:
            self.login_failed_indicator.show()
            print(
                "Authentication unsuccessful. "
                "HTTP status code: {}. Body: {}".format(
                    status, data
                )
            )
            return

        self.store_remote_address(remote_url)
        keyring.set_password("euterpe", "token", "")
        self._remote_address = remote_url

        # Clean-up the username and password!
        self.service_password.set_text("")
        self.service_username.set_text("")

        try:
            response = json.loads(data)
        except Exception as err:
            print("Wrong JSON in response for authentication: {}".format(
                err
            ))
            self.login_failed_indicator.show()
            return

        if 'token' in response:
            token = response['token']
            self._token = token
            keyring.set_password("euterpe", "token", token)

        self._euterpe.set_address(self._remote_address)
        self._euterpe.set_token(self._token)

        self._home_widget.restore_state(self._cache_store)

        self.app_stack.set_visible_child(
            self.logged_in_screen
        )

    def logout(self):
        self._token = None
        self._remote_address = None

        keyring.set_password("euterpe", "token", "")
        self.store_remote_address("")

        self._euterpe.set_address(None)
        self._euterpe.set_token(None)

        if self._player is not None:
            self._player.stop()
            self._player.set_playlist([])

        if self._search_widget is not None:
            self._search_widget.factory_reset()

        self._cache_store.truncate()

        self.app_stack.set_visible_child(
            self.login_scroll_view
        )

    def on_headerbar_squeezer_notify(self, squeezer, event):
        child = squeezer.get_visible_child()
        self.bottom_switcher.set_reveal(child != self.headerbar_switcher)

    def open_search_screen(self, btn):
        self.main_stack.set_visible_child(self.search_screen)

    def _on_header_changed(self, obj, showMainHeader):
        if showMainHeader:
            self._show_navigation()
        else:
            self._hide_navigation()

    def _hide_navigation(self):
        self.title_tab_bar.hide()
        self.bottom_switcher.set_reveal(False)

    def _show_navigation(self):
        self.title_tab_bar.show()
        child = self.squeezer.get_visible_child()
        self.bottom_switcher.set_reveal(child != self.headerbar_switcher)

    def _on_show_big_player(self, *args):
        self.logged_in_screen.set_visible_child(self._player_ui)

    def _on_hide_big_player(self, *args):
        self.logged_in_screen.set_visible_child(self.browsing_ui)

    def _on_program_exit(self, *args):
        self.store_state()
        return False

    def store_state(self):
        if not self._state_restored:
            # The program is exiting before it had the time to
            # fully restore its state. So in order to prevent
            # storing partial state we are not storing anything here.
            return

        self._search_widget.store_state(self._cache_store)
        self._player.store_state(self._cache_store)
        self._home_widget.store_state(self._cache_store)
        self._store_window_state()
        self._store_navigation_state()
        self._cache_store.save()

    def _on_size_allocate(self, __win, allocation):
        if self.is_maximized():
            return

        (w, h) = self.get_size()
        self._current_width = w
        self._current_height = h

    def _on_window_state_event(self, __win, event):
        self._is_maximized = (
            event.new_window_state & Gdk.WindowState.MAXIMIZED
        ) != 0

    def _store_navigation_state(self):
        nav_visible = self.main_stack.get_visible_child_name()
        self._cache_store.set_string(
            "main_stack_visible",
            nav_visible,
            namespace="navigation_state"
        )

    def _store_window_state(self):
        try:
            self._cache_store.set_many(
                {
                    "width": self._current_width,
                    "height": self._current_height,
                    "maximized": self._is_maximized,
                },
                namespace="window_state"
            )
        except Exception as err:
            print("Error storing window state: {}".format(err))

    def _restore_navigation_state(self):
        store = self._cache_store
        try:
            nav_visible = store.get_string(
                "main_stack_visible",
                namespace="navigation_state"
            )
        except Exception as err:
            print("error restoring navigation state: {}".format(err))

        if nav_visible is None:
            return

        self.main_stack.set_visible_child_name(nav_visible)

    def _restore_window_state(self):
        store = self._cache_store

        try:
            width = store.get_integer("width", namespace="window_state")
            height = store.get_integer("height", namespace="window_state")
        except Exception as err:
            print("error restoring window size: {}".format(err))
            return

        if width != 0 and height != 0:
            self._current_width = width
            self._current_height = height
            self.set_default_size(width, height)

        try:
            maximized = store.get_boolean(
                "maximized",
                namespace="window_state"
            )
        except Exception as err:
            print("error restoring window maximized: {}".format(err))
            return

        self._is_maximized = maximized
        if maximized:
            self.maximize()

    def _on_volume_changed(self, slider, scroll, value):
        if self._player is None:
            return

        self._player.set_volume(value)
        return False

    def _on_player_volume_changed(self, player, vol):
        self.volume_adjustment.set_value(vol)
