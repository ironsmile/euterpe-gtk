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
import enum

from gi.repository import Soup

class Priority(enum.Enum):
    '''
    Defines the type of HTTP requests which could be made. The different priority
    requests will get their own queues.
    '''
    LOW = -1
    NORMAL = 0
    HIGH = 1

_sessions = {}

def Init():
    '''
    Init makes sure the HTTP library module is ready for use from anywhere.
    Currently this means creating Soup sessions for every type of priority.

    Make sure to call this before any other calls to libraries which would
    want to load LibSoup.
    '''
    init_session(Priority.LOW)
    init_session(Priority.NORMAL)
    init_session(Priority.HIGH)

def init_session(priority):
    global _sessions

    sess = _sessions.get(priority, None)
    if sess is not None:
        return sess

    sess = Soup.Session()
    sess.props.user_agent = "Euterpe-GTK HTTP Client"
    sess.props.max_conns = 6

    _sessions[priority] = sess
    return sess


class Request(object):
    '''
        Request is an utility for creating HTTP requests using the
        Soup framework. So that all the processing is done in the
        background and does not hog the main UI thread.

        Note that the request callback will be called once the whole
        response body has been received.
    '''

    def __init__(self, address, callback, priority=Priority.NORMAL):
        '''
        callback must be a function with the following arguments

            * status (int) - the HTTP response code
            * body (GLib.Bytes) - the HTTP response body
            * *args - the arguments passed to `get` or `post`
        '''

        self._session = init_session(priority)
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
        req.set_request(content_type, Soup.MemoryUse.COPY, body)
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
        resp_body = message.props.response_body_data.get_data()
        self._call_callback(status, resp_body)

    def _call_callback(self, status, data):
        try:
            self._callback(status, data, *(self._args))
        except Exception:
            sys.excepthook(*sys.exc_info())

class AsyncRequest(object):
    '''
        Request is an utility for creating HTTP requests using the
        Soup framework. So that all the processing is done in the
        background and does not hog the main UI thread.

        Note that the request callback will be called once the response
        headers have been received. At this stage the body hasn't been
        read yet.
    '''

    def __init__(self, address, cancellable, callback, priority=Priority.NORMAL):
        '''
        * address (string) - the HTTP address to which a request will be made
        * cancellable (Gio.Cancellable) - a way to cancel the request in flight
        * callback - a function with the following arguments:
            - status (int) - the HTTP response code
            - body (Gio.InputStream) - the HTTP response body
            - cancel (Gio.Cancellable) - a cancellable which cancels the request
            - *args - the arguments passed to `get`, `post` or `put`
        '''

        self._session = init_session(priority)
        self._address = address
        self._callback = callback
        self._headers = {}
        self._args = []
        self._cancellable = cancellable

    def set_header(self, name, value):
        self._headers[name] = value

    def get(self, *args):
        self._args = args
        req = Soup.Message.new("GET", self._address)
        self._do(req)

    def post(self, content_type, body, *args):
        self._args = args
        req = Soup.Message.new("POST", self._address)
        req.set_request(content_type, Soup.MemoryUse.COPY, body.get_data())
        self._do(req)

    def put(self, content_type, body, *args):
        self._args = args
        req = Soup.Message.new("PUT", self._address)
        req.set_request(content_type, Soup.MemoryUse.COPY, body.get_data())
        self._do(req)

    def _do(self, req):
        try:
            for k, v in self._headers.items():
                req.props.request_headers.append(k, v)
            self._session.send_async(req, self._cancellable, self._request_cb, req)
        except Exception:
            sys.excepthook(*sys.exc_info())
            self._callback(None, None, None, *(self._args))

    def _request_cb(self, session, res, message):
        try:
            body_stream = session.send_finish(res)
        except Exception:
            self._callback(None, None, None, *(self._args))
            return

        status = message.status_code
        self._call_callback(status, body_stream)

    def _call_callback(self, status, data_stream):
        try:
            self._callback(status, data_stream, self._cancellable, *(self._args))
        except Exception:
            sys.excepthook(*sys.exc_info())

