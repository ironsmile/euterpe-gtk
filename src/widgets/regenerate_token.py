# regenerate_token.py
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

SIGNAL_GENERATE_TOKEN_SUCCESS = "generate-token-success"
SIGNAL_LOGOUT_REQUESTED = "logout-requested"


@Gtk.Template(resource_path='/com/doycho/euterpe/gtk/ui/regenerate-token.ui')
class EuterpeTokenForm(Gtk.Viewport):
    __gtype_name__ = 'EuterpeTokenForm'

    __gsignals__ = {
        SIGNAL_GENERATE_TOKEN_SUCCESS: (GObject.SignalFlags.RUN_FIRST, None, ()),
        SIGNAL_LOGOUT_REQUESTED: (GObject.SignalFlags.RUN_FIRST, None, ()),
    }

    generate_button = Gtk.Template.Child()
    logout_button = Gtk.Template.Child()
    login_spinner = Gtk.Template.Child()
    login_failed_indicator = Gtk.Template.Child()
    server_url = Gtk.Template.Child()
    service_username = Gtk.Template.Child()
    service_password = Gtk.Template.Child()
    service_password_show_toggle = Gtk.Template.Child()

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        app = Gio.Application.get_default()
        if app is None:
            raise Exception("There is no default application")

        self._euterpe = app.get_euterpe()
        self._remote_address = None
        self._username = None

        self.connect("realize", self._on_activate)

    def set_credentials(self, remote_address, username):
        self._remote_address = remote_address
        self._username = username

        self.server_url.set_text(remote_address)
        self.service_username.set_text(username)

    def _on_activate(self, *args):
        self.generate_button.connect("clicked", self._on_generate_button)
        self.logout_button.connect("clicked", self._on_logout_button)
        self.service_password_show_toggle.bind_property(
            'active',
            self.service_password, 'visibility',
            GObject.BindingFlags.SYNC_CREATE
        )
        for obj in [
            self.generate_button, self.service_password, self.service_password_show_toggle,
        ]:
            self.login_spinner.bind_property(
                'active',
                obj, 'sensitive',
                GObject.BindingFlags.INVERT_BOOLEAN
            )

        self.service_password.connect('activate', self._submit_form)

    def _submit_form(self, *args):
        self.generate_button.activate()

    def _on_logout_button(self, *args):
        emit_signal(self, SIGNAL_LOGOUT_REQUESTED)

    def _on_generate_button(self, *args):
        if self._remote_address is None or self._username is None:
            log.warning("login button clicked when no address or username are present")
            self.login_failed_indicator.show()
            return

        self._show_login_loading()

        remote_url = self._remote_address
        username = self._username
        password = self.service_password.get_text()

        Euterpe.check_login_credentials(
            remote_url,
            self._on_login_request_response,
            username,
            password,
            remote_url,
            username,
        )

    def _on_login_request_response(self, status, data, remote_url, username):
        self._hide_login_loading()

        if status != 200:
            self.login_failed_indicator.show()
            log.message(
                "Authentication unsuccessful. "
                "HTTP status code: {}. Body: {}",
                status, data
            )
            return

        try:
            response = json.loads(data)
        except Exception as err:
            log.message("Wrong JSON in response for authentication: {}".format(
                err
            ))
            self.login_failed_indicator.show()
            return

        if 'token' not in response:
            log.warning("There was no 'token' field in the server response even"
                "though the response was for successful login.")
            self.login_failed_indicator.show()
            return

        token = response['token']
        keyring.set_password("euterpe", "token", token)

        self._euterpe.set_token(token)

        emit_signal(self, SIGNAL_GENERATE_TOKEN_SUCCESS)

    def _show_login_loading(self):
        self.login_spinner.props.active = True

    def _hide_login_loading(self):
        self.login_spinner.props.active = False
