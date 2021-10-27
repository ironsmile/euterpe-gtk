# http.py
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
import sys
gi.require_version('Soup', '2.4')
from gi.repository import Gio, Soup


_soup_session = None


class Request(object):
    '''
        Request is an utility for creating HTTP requests using the
        Soup framework. So that all the processing is done in the
        background and does not hog the main UI thread.
    '''

    def __init__(self, address, callback):
        global _soup_session
        if _soup_session is None:
            _soup_session = Soup.Session()
            _soup_session.props.user_agent = "Euterpe-GTK HTTP Client"

        self._session = _soup_session
        self._address = address
        self._callback = callback
        self._headers = {}
        self._args = []

    def set_header(self, name, value):
        self._headers[name] = value

    def get(self, *args):
        self._args = args
        req = Soup.Message.new("GET", self._address)
        self._do(req)

    def post(self, content_type, body, *args):
        self._args = args
        req = Soup.Message.new("POST", self._address)
        req.set_request(content_type, Soup.MemoryUse.STATIC, body)
        self._do(req)

    def _do(self, req):
        try:
            for k, v in self._headers.items():
                req.props.request_headers.append(k, v)
            self._session.queue_message(req, self._request_cb, None)
        except Exception:
            sys.excepthook(*sys.exc_info())
            self._callback(None, None)

    def _request_cb(self, session, message, data):
        status = message.props.status_code
        if status >= 200 and status <= 299:
            self._call_callback(
                status,
                message.props.response_body_data.get_data(),
            )
        else:
            self._call_callback(status, None)

    def _call_callback(self, status, data):
        try:
            print("self._args:", self._args)
            self._callback(status, data, *(self._args))
        except Exception:
            sys.excepthook(*sys.exc_info())
