# login_form.py
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
import keyring
import json

from gi.repository import GObject, Gtk, Gio
from euterpe_gtk.service import Euterpe
from euterpe_gtk.utils import emit_signal
import euterpe_gtk.log as log

SIGNAL_LOGIN_SUCCESS = "login-success"


@Gtk.Template(resource_path='/com/doycho/euterpe/gtk/ui/login-form.ui')
class EuterpeLoginForm(Gtk.Viewport):
    __gtype_name__ = 'EuterpeLoginForm'

    __gsignals__ = {
        SIGNAL_LOGIN_SUCCESS: (GObject.SignalFlags.RUN_FIRST, None, ()),
    }

    login_button = Gtk.Template.Child()
    login_spinner = Gtk.Template.Child()
    login_failed_indicator = Gtk.Template.Child()
    server_url = Gtk.Template.Child()
    service_username = Gtk.Template.Child()
    service_password = Gtk.Template.Child()
    service_password_show_toggle = Gtk.Template.Child()

    def __init__(self, config_store, **kwargs):
        super().__init__(**kwargs)

        app = Gio.Application.get_default()
        if app is None:
            raise Exception("There is no default application")

        self._euterpe = app.get_euterpe()
        self._config_store = config_store

        self.connect("realize", self.on_activate)

    def on_activate(self, *args):
        self.login_button.connect("clicked", self.on_login_button)
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

        for obj in [self.server_url, self.service_username, self.service_password]:
            obj.connect('activate', self._submit_form)


    def _submit_form(self, *args):
        self.login_button.activate()

    def on_login_button(self, *args):
        remote_url = self.server_url.get_text().strip()

        if remote_url == "":
            log.debug('Empty URL is not accepted')
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
            log.message(
                "Authentication unsuccessful. "
                "HTTP status code: {}. Body: {}",
                status, data
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
            log.message("Wrong JSON in response for authentication: {}".format(
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

        emit_signal(self, SIGNAL_LOGIN_SUCCESS)

    def show_login_loading(self):
        self.login_spinner.props.active = True

    def hide_login_loading(self):
        self.login_spinner.props.active = False

    def store_remote_address(self, address):
        self._config_store.set_string("address", address)
        self._config_store.save()
