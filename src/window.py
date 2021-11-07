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
from .utils import emit_signal, config_file_name
from .track import EuterpeTrack
from .browse_screen import EuterpeBrowseScreen


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

    main_search_box = Gtk.Template.Child()

    pause_button_icon = Gtk.Template.Child()
    play_button_icon = Gtk.Template.Child()

    search_results_container = Gtk.Template.Child()
    search_result_viewport = Gtk.Template.Child()
    search_loading_indicator = Gtk.Template.Child()
    search_empty_content = Gtk.Template.Child()
    search_result_list = Gtk.Template.Child()
    play_all_search_results = Gtk.Template.Child()

    def __init__(self, appVersion, **kwargs):
        super().__init__(**kwargs)

        self._appVersion = appVersion
        self._token = None

        self._player = None
        self._euterpe = None
        self._remote_address = None

        self.squeezer.set_visible(False)

        self.connect("show", self.on_activate)
        self.connect(SIGNAL_STATE_RESTORED, self.on_state_restored)

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
        self.login_button.connect("clicked", self.on_login_button)
        self.logout_button.connect("clicked", self.on_logout_button)
        self.main_search_box.connect("activate", self.on_search_changed)
        self.play_all_search_results.connect(
            "clicked",
            self.on_play_all_search_results
        )

        self.service_password_show_toggle.bind_property(
            'active',
            self.service_password, 'visibility',
            GObject.BindingFlags.SYNC_CREATE
        )

        self.search_loading_indicator.bind_property(
            'active',
            self.search_results_container, 'visible',
            GObject.BindingFlags.INVERT_BOOLEAN
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

        self.browse_screen_obj = EuterpeBrowseScreen()
        self.browse_screen.add(self.browse_screen_obj)
        self.browse_screen_obj.connect(
            'search-button-clicked',
            self.open_search_screen
        )

        self._config_file = config_file_name()

        print("staring RestoreStateThread")
        t = threading.Thread(
            target=self.restore_state,
            name="RestoreStateThread"
        )
        t.daemon = True
        t.start()

    def connect_player_signals(self):
        self._player.connect("state-changed",
                             self.on_player_state_changed)
        self._player.connect("progress",
                             self.on_track_progress_changed)
        self._player.connect("track-changed",
                             self.on_track_changed)

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
            print("restoring address...")
            self._restore_address()
            print("restoring token...")
            self._restore_token()
            print("creating Euterpe instance...")
            self._euterpe = Euterpe(self._remote_address, self._token)
            print("creating player...")
            self._player = Player(self._euterpe)
            print("connecting signals...")
            self.connect_player_signals()
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

        print("showing screen {}".format(screen))
        self.app_stack.set_visible_child(screen)

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
        self.connect_player_signals()
        self.app_stack.set_visible_child(
            self.logged_in_screen
        )

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

    def on_track_set(self, trackObj):
        if self._player is None:
            print("trying to set track when there is no player active")
            return

        track = trackObj.get_track()

        self._player.set_playlist([track])
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
            self.play_button.set_image(self.pause_button_icon)
        else:
            self.play_button.set_label("Play")
            self.play_button.set_image(self.play_button_icon)

        if player.has_ended():
            self.change_progress(0)

    def on_search_changed(self, search_entry):
        search_term = search_entry.get_text()
        if search_term == "":
            self.search_result_viewport.foreach(
                self.search_result_viewport.remove
            )
            self.search_result_viewport.add(
                self.search_empty_content,
            )
            return

        print("searching for '{}'".format(
            search_term,
            type(search_term)
        ))

        self.search_for(search_term)

    def search_for(self, search_term):
        if search_term is None:
            print("received None instead of a search term, aborting")
            return

        self.search_loading_indicator.start()
        self.search_loading_indicator.set_visible(True)
        self._euterpe.search(search_term, self._on_search_result)

    def _on_search_result(self, status, body, query):
        self.search_loading_indicator.stop()
        self.search_loading_indicator.set_visible(False)

        self.search_result_viewport.foreach(self.search_result_viewport.remove)
        self.search_result_list.foreach(self.search_result_list.remove)

        if status != 200:
            label = Gtk.Label.new()
            label.set_text("Error searching. HTTP response code {}.".format(
                status
            ))
            self.search_result_viewport.add(label)
            label.show()
            return

        if len(body) == 0:
            label = Gtk.Label.new()
            label.set_text("Nothing found for '{}'.".format(query))
            self.search_result_viewport.add(label)
            label.show()
            return

        self._search_results = body
        self.search_result_list.add(self.play_all_search_results)

        for track in body:
            trObj = EuterpeTrack(track)
            self.search_result_list.add(trObj)
            trObj.connect("play-button-clicked", self.on_track_set)

        self.search_result_viewport.add(self.search_result_list)
        self.search_result_list.show()

    def on_play_all_search_results(self, btn):
        self._player.set_playlist(self._search_results)
        self._player.play()

    def open_search_screen(self, btn):
        self.main_stack.set_visible_child(self.search_screen)
