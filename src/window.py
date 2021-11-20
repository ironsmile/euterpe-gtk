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
import json

gi.require_version('Handy', '1')
gi.require_version('Gst', '1.0')
gi.require_version('GLib', '2.0')

from gi.repository import GObject, GLib, Gtk, Handy, Gst
from .player import Player
from .service import Euterpe
from .utils import emit_signal, config_file_name, state_file_name
from .browse_screen import EuterpeBrowseScreen
from .search_screen import EuterpeSearchScreen
from .mini_player import EuterpeMiniPlayer
from .state_storage import StateStorage


SIGNAL_STATE_RESTORED = "state-restored"


@Gtk.Template(resource_path='/com/doycho/euterpe/gtk/ui/window.ui')
class EuterpeGtkWindow(Handy.ApplicationWindow):
    __gtype_name__ = 'EuterpeGtkWindow'

    __gsignals__ = {
        SIGNAL_STATE_RESTORED: (GObject.SignalFlags.RUN_FIRST, None, ()),
    }

    Handy.init()

    squeezer = Gtk.Template.Child()
    headerbar_switcher = Gtk.Template.Child()
    bottom_switcher = Gtk.Template.Child()
    main_stack = Gtk.Template.Child()
    title_tab_bar = Gtk.Template.Child()

    search_screen = Gtk.Template.Child()
    browse_screen = Gtk.Template.Child()

    about_gtk_version = Gtk.Template.Child()
    about_gstreamer_version = Gtk.Template.Child()
    about_python_version = Gtk.Template.Child()
    about_euterpe_version = Gtk.Template.Child()
    about_libhandy_version = Gtk.Template.Child()

    home_track_name = Gtk.Template.Child()
    home_artist_name = Gtk.Template.Child()
    home_album_name = Gtk.Template.Child()

    play_button = Gtk.Template.Child()
    next_button = Gtk.Template.Child()
    prev_button = Gtk.Template.Child()
    track_progess = Gtk.Template.Child()

    logged_in_screen = Gtk.Template.Child()
    login_scroll_view = Gtk.Template.Child()
    app_stack = Gtk.Template.Child()
    login_button = Gtk.Template.Child()
    logout_button = Gtk.Template.Child()

    login_spinner = Gtk.Template.Child()
    login_failed_indicator = Gtk.Template.Child()
    server_url = Gtk.Template.Child()
    service_username = Gtk.Template.Child()
    service_password = Gtk.Template.Child()
    service_password_show_toggle = Gtk.Template.Child()

    pause_button_icon = Gtk.Template.Child()
    play_button_icon = Gtk.Template.Child()

    miniplayer_position = Gtk.Template.Child()

    def __init__(self, appVersion, **kwargs):
        super().__init__(**kwargs)

        self._appVersion = appVersion
        self._token = None

        self._player = None
        self._euterpe = None
        self._remote_address = None
        self._search_widget = None

        self.squeezer.set_visible(False)

        self.connect("show", self.on_activate)
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
        self.play_button.connect(
            "clicked",
            self.on_play_button_clicked
        )
        self.next_button.connect(
            "clicked",
            self.on_next_button_clicked
        )
        self.prev_button.connect(
            "clicked",
            self.on_prev_button_clicked
        )
        self.track_progess.connect(
            "change-value",
            self.on_seek
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
        self.logout_button.connect("clicked", self.on_logout_button)

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

        Gst.init(None)
        self.populate_about()

        self.track_progess.set_range(0, 1)

        browse_screen = EuterpeBrowseScreen()
        self.browse_screen.add(browse_screen)
        browse_screen.connect(
            'search-button-clicked',
            self.open_search_screen
        )

        self._search_widget = EuterpeSearchScreen(self)
        self.search_screen.add(self._search_widget)

        self._config_store = StateStorage(config_file_name(), "config")
        self._cache_store = StateStorage(state_file_name(), "app_state")

        self.connect("delete-event", self._on_program_exit)

        print("staring RestoreStateThread")
        t = threading.Thread(
            target=self.restore_state,
            name="RestoreStateThread"
        )
        t.daemon = True
        t.start()

    def _on_player_created(self):
        self._player.connect("state-changed",
                             self.on_player_state_changed)
        self._player.connect("progress",
                             self.on_track_progress_changed)
        self._player.connect("track-changed",
                             self.on_track_changed)

        mini_player = self.miniplayer_position.get_child()
        if mini_player is not None:
            mini_player.destroy()

        mini_player = EuterpeMiniPlayer(self._player)
        self.miniplayer_position.add(mini_player)

    def on_track_changed(self, player):
        track = player.get_track_info()
        if track is None:
            return

        self.home_track_name.set_label(track.get("title", "n/a"))
        self.home_album_name.set_label(track.get("album", "n/a"))
        self.home_artist_name.set_label(track.get("artist", "n/a"))

    def restore_state(self):
        '''
            Restores the application state from the last time it was
            run.
        '''
        try:
            print("reading key-value files from disk...")
            self._config_store.load()
            self._cache_store.load()
            print("restoring address...")
            self._restore_address()
            print("restoring token...")
            self._restore_token()
            print("creating Euterpe instance...")
            self._euterpe = Euterpe(self._remote_address, self._token)
            print("creating player...")
            self._player = Player(self._euterpe)
            print("connecting signals...")
            self._on_player_created()
            print("restoring search state...")
            self._search_widget.restore_state(self._cache_store)
            print("restoring playing state...")
            self._player.restore_state(self._cache_store)
        except Exception as err:
            print("Restoring state failed: {}".format(err))
        finally:
            emit_signal(self, SIGNAL_STATE_RESTORED)

    def store_remote_address(self, address):
        self._config_store.set_string("address", address)

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

    def on_track_progress_changed(self, player, progress):
        self.change_progress(progress)

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

    def on_main_stack_change(self, stack, event):
        self.title_tab_bar.foreach(self.title_tab_bar.remove)
        visible_child = stack.get_visible_child()
        if issubclass(type(visible_child), Gtk.Container):
            grand_children = visible_child.get_children()
            if len(grand_children) == 1:
                screen = grand_children[0]
                if hasattr(screen, 'get_back_button'):
                    back_button = screen.get_back_button()
                    self.title_tab_bar.add(back_button)

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
            print("Authentication unsuccessful. HTTP status code: {}".format(
                status
            ))
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

        self._euterpe = Euterpe(self._remote_address, self._token)
        self._player = Player(self._euterpe)
        self._on_player_created()
        self.app_stack.set_visible_child(
            self.logged_in_screen
        )

    def on_logout_button(self, button):
        self._token = None
        self._remote_address = None

        keyring.set_password("euterpe", "token", "")
        self.store_remote_address("")

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

    def on_play_button_clicked(self, button):
        print("play button clicked")

        if self._player is None:
            print("no player is set!")
            return

        self._toggle_playing_state(button)

    def on_next_button_clicked(self, button):
        if self._player is None:
            return
        self._player.next()

    def on_prev_button_clicked(self, button):
        if self._player is None:
            return
        self._player.previous()

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

        self.track_progess.set_sensitive(True)
        self.play_button.set_sensitive(True)
        self.next_button.set_sensitive(player.has_next())
        self.prev_button.set_sensitive(player.has_previous())

        if player.is_playing():
            self.play_button.set_label("Pause")
            self.play_button.set_image(self.pause_button_icon)
        else:
            self.play_button.set_label("Play")
            self.play_button.set_image(self.play_button_icon)

        if player.has_ended():
            self.change_progress(0)

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

    def _on_program_exit(self, *args):
        if self._search_widget is not None:
            self._search_widget.store_state(self._cache_store)

        if self._player is not None:
            self._player.store_state(self._cache_store)
