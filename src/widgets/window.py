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
import keyring
import json
import time

from gi.repository import GObject, Gtk, Handy, Gst, Gdk, GLib
from euterpe_gtk.utils import emit_signal, config_file_name, state_file_name
from euterpe_gtk.widgets.login_form import EuterpeLoginForm, SIGNAL_LOGIN_SUCCESS
from euterpe_gtk.widgets.regenerate_token import (EuterpeTokenForm,
    SIGNAL_GENERATE_TOKEN_SUCCESS, SIGNAL_LOGOUT_REQUESTED)
from euterpe_gtk.widgets.browse_screen import EuterpeBrowseScreen
from euterpe_gtk.widgets.search_screen import EuterpeSearchScreen
from euterpe_gtk.widgets.home_screen import EuterpeHomeScreen
from euterpe_gtk.widgets.mini_player import EuterpeMiniPlayer
from euterpe_gtk.state_storage import StateStorage
from euterpe_gtk.service import SIGNAL_TOKEN_EXPIRED
from euterpe_gtk.widgets.player_ui import EuterpePlayerUI
import euterpe_gtk.log as log


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

    restore_failed_dialog = Gtk.Template.Child()
    token_expired_dialog = Gtk.Template.Child()

    about_gtk_version = Gtk.Template.Child()
    about_gstreamer_version = Gtk.Template.Child()
    about_python_version = Gtk.Template.Child()
    about_euterpe_version = Gtk.Template.Child()
    about_libhandy_version = Gtk.Template.Child()

    logged_in_screen = Gtk.Template.Child()
    login_scroll_view = Gtk.Template.Child()
    app_stack = Gtk.Template.Child()

    volume_adjustment = Gtk.Template.Child()
    main_volume_slider = Gtk.Template.Child()

    miniplayer_position = Gtk.Template.Child()

    def __init__(self, appVersion, **kwargs):
        super().__init__(**kwargs)

        self._appVersion = appVersion
        self._state_restored = False
        self._state_restore_failure = None
        self._logged_in = False

        app = self.get_application()

        self._euterpe = app.get_euterpe()
        self._player = app.get_player()
        self._search_widget = None

        self._current_width = None
        self._current_height = None
        self._is_maximized = None

        self.squeezer.set_visible(False)

        self._config_store = StateStorage(config_file_name(), "config")
        self._cache_store = StateStorage(state_file_name(), "app_state")
        log.debug("reading key-value files from disk...")
        self._config_store.load()
        self._cache_store.load()

        log.debug("restoring window state...")
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

        self.main_volume_slider.connect(
            "change-value",
            self._on_volume_changed
        )

        self.restore_failed_dialog.connect(
            "response",
            self._on_restore_failed_response
        )

        self.token_expired_dialog.connect(
            "response",
            self._on_token_expired_response
        )

        self.login_scroll_view.bind_property(
            'visible',
            self.back_button_position, 'visible',
            GObject.BindingFlags.INVERT_BOOLEAN
        )

        self.populate_about()

        browse_screen = EuterpeBrowseScreen(self)
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

        self._euterpe.connect(SIGNAL_TOKEN_EXPIRED, self._on_expired_token)

        log.debug("staring restore callback")
        GLib.idle_add(self.restore_state, None)

    def restore_state(self, *args):
        '''
            Restores the application state from the last time it was
            run.
        '''
        self._state_restore_failure = None

        try:
            log.debug("restoring service config...")
            self._restore_service_config()
            log.debug("restoring token...")
            self._restore_token()
            log.debug("restoring search state...")
            self._search_widget.restore_state(self._cache_store)
            log.debug("restoring playing state...")
            self._player.restore_state(self._cache_store)

            if self._logged_in:
                log.debug("restoring recently added...")
                self._home_widget.restore_state(self._cache_store)
        except Exception as err:
            log.message("Restoring state failed: {}", err)
            self._state_restore_failure = "Restoring state failed: {}".format(err)
        finally:
            self._state_restored = True
            emit_signal(self, SIGNAL_STATE_RESTORED)
        return False

    def cleanup_service_config(self):
        self._config_store.set_string("address", "")
        self._config_store.set_string("username", "")
        self._config_store.save()

    def _restore_service_config(self):
        address = self._config_store.get_string("address")
        if address != "":
            self._logged_in = True
            self._euterpe.set_address(address)

        username = self._config_store.get_string("username")
        if username != "":
            self._euterpe.set_username(username)

    def _restore_token(self):
        token = keyring.get_password("euterpe", "token")

        if token == "":
            log.debug("no token found in the keyring")
            return

        self._euterpe.set_token(token)

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
            * Search state
            * Player queue and currently playing state
        '''
        log.message("state restored")

        if self._state_restore_failure is not None:
            self.restore_failed_dialog.show_all()
            return

        screen = self.login_scroll_view
        if self._logged_in:
            screen = self.logged_in_screen
        else:
            self._attach_login_form()

        self.app_stack.set_visible_child(screen)
        self.set_back_button_to_visible_child(self.main_stack)

    def _on_restore_failed_response(self, dialog, response_id):
        if response_id == Gtk.ResponseType.DELETE_EVENT:
            self.close()
            return

        dialog.hide()

        if response_id == Gtk.ResponseType.ACCEPT:
            GLib.idle_add(self.restore_state, None)
            return

        if response_id == Gtk.ResponseType.REJECT:
            self.logout()

    def _on_token_expired_response(self, dialog, response_id):
        if response_id == Gtk.ResponseType.DELETE_EVENT:
            self.close()
            return

        dialog.hide()

        if response_id == Gtk.ResponseType.ACCEPT:
            addr = self._euterpe.get_address()
            user = self._euterpe.get_username()

            expire_form = self._attach_token_expired_form()
            expire_form.set_credentials(addr, user)

            self.app_stack.set_visible_child(
                self.login_scroll_view
            )
            return

        if response_id == Gtk.ResponseType.REJECT:
            self.logout()

    def on_main_stack_change(self, stack, event):
        self.set_back_button_to_visible_child(stack)

    def set_back_button_to_visible_child(self, stack):
        self.back_button_position.foreach(self.back_button_position.remove)
        visible_child = stack.get_visible_child()
        if not issubclass(type(visible_child), Gtk.Container):
            return

        grand_children = visible_child.get_children()
        if len(grand_children) != 1:
            return

        screen = grand_children[0]
        if not hasattr(screen, 'get_back_button'):
            return

        back_button = screen.get_back_button()
        self.back_button_position.add(back_button)

    def on_login_status_change(self, stack, event):
        login_visible = (self.logged_in_screen == stack.get_visible_child())
        self.squeezer.set_visible(login_visible)

    def _on_login_success(self, login_form):
        self._logged_in = True
        self._home_widget.restore_state(self._cache_store)

        self.app_stack.set_visible_child(
            self.logged_in_screen
        )

        login_form.destroy()

    def logout(self):
        keyring.set_password("euterpe", "token", "")
        self.cleanup_service_config()
        self._logged_in = False

        self._euterpe.set_address(None)
        self._euterpe.set_token(None)
        self._euterpe.set_username(None)

        if self._player is not None:
            self._player.stop()
            self._player.set_playlist([])

        if self._search_widget is not None:
            self._search_widget.factory_reset()

        if self._home_widget is not None:
            self._home_widget.factory_reset()

        self._cache_store.truncate()

        self._attach_login_form()

        self.app_stack.set_visible_child(
            self.login_scroll_view
        )

    def _attach_login_form(self):
        '''
        Creates a login form widget and attaches it to the login_scroll_view.

        Returns the created login_form widget.
        '''
        for child in self.login_scroll_view.get_children():
            child.destroy()

        login_form = EuterpeLoginForm(self._config_store)
        login_form.connect(SIGNAL_LOGIN_SUCCESS, self._on_login_success)
        login_form.show()
        self.login_scroll_view.add(login_form)
        return login_form

    def _attach_token_expired_form(self):
        '''
        Creates a token expired widget and attaches it to the login_scroll_view.

        Returns the created token_expire widget.
        '''
        for child in self.login_scroll_view.get_children():
            child.destroy()

        token_form = EuterpeTokenForm()
        token_form.connect(SIGNAL_GENERATE_TOKEN_SUCCESS, self._on_login_success)
        token_form.connect(SIGNAL_LOGOUT_REQUESTED, self._on_logout_requested)
        token_form.show()
        self.login_scroll_view.add(token_form)
        return token_form

    def on_headerbar_squeezer_notify(self, squeezer, event):
        child = squeezer.get_visible_child()
        self.bottom_switcher.set_reveal(child != self.headerbar_switcher)

    def open_search_screen(self, btn):
        self.main_stack.set_visible_child(self.search_screen)

    def _on_logout_requested(self, *args, **kwargs):
        self.logout()

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
        # self.back_button_position.set_visible(False)
        self.logged_in_screen.set_visible_child(self._player_ui)
        # self._player_ui.queue_resize()

    def _on_hide_big_player(self, *args):
        # self.back_button_position.set_visible(True)
        self.logged_in_screen.set_visible_child(self.browsing_ui)
        # self.browsing_ui.queue_resize()

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
            log.warning("Error storing window state: {}", err)

    def _restore_navigation_state(self):
        store = self._cache_store
        try:
            nav_visible = store.get_string(
                "main_stack_visible",
                namespace="navigation_state"
            )
        except Exception as err:
            log.warning("error restoring navigation state: {}", err)

        if nav_visible is None:
            return

        self.main_stack.set_visible_child_name(nav_visible)

    def _restore_window_state(self):
        store = self._cache_store

        try:
            width = store.get_integer("width", namespace="window_state")
            height = store.get_integer("height", namespace="window_state")
        except Exception as err:
            log.warning("error restoring window size: {}", err)
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
            log.warning("error restoring window maximized: {}", err)
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

    def _on_expired_token(self, *args):
        self.token_expired_dialog.show_all()
