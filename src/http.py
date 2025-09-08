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

_session = None

def Init():
    '''
    Init makes sure the HTTP library module is ready for use from anywhere.
    Currently this means creating Soup sessions for every type of priority.

    Make sure to call this before any other calls to libraries which would
    want to load LibSoup.
    '''
    init_session()

def init_session():
    global _session

    if _session is not None:
        return _session

    _session = Soup.Session(
        max_conns=6,
        user_agent="Euterpe-GTK HTTP Client",
    )

    return _session


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

        self._priority = to_soup_priority(priority)
        self._session = init_session()
        self._address = address
        self._callback = callback
        self._headers = {}

    def set_header(self, name, value):
        self._headers[name] = value

    def get(self, *args):
        req = Soup.Message.new("GET", self._address)
        self._do(req, args)

    def post(self, content_type, body, *args):
        req = Soup.Message.new("POST", self._address)
        req.set_request_body_from_bytes(content_type, body)
        self._do(req, args)

    def patch(self, content_type, body, *args):
        req = Soup.Message.new("PATCH", self._address)
        req.set_request_body_from_bytes(content_type, body)
        self._do(req, args)

    def put(self, content_type, body, *args):
        req = Soup.Message.new("PUT", self._address)
        req.set_request_body_from_bytes(content_type, body)
        self._do(req, args)

    def delete(self, *args):
        req = Soup.Message.new("DELETE", self._address)
        self._do(req, args)

    def _do(self, req, args):
        try:
            for k, v in self._headers.items():
                req.props.request_headers.append(k, v)
            self._session.send_and_read_async(
                req,
                self._priority,
                None,
                self._request_cb,
                args,
            )
        except Exception:
            sys.excepthook(*sys.exc_info())
            self._callback(None, None)

    def _request_cb(self, source, result, args):
        message = source.get_async_result_message(result)
        status = message.get_status()
        resp_body = source.send_and_read_finish(result).get_data()
        self._call_callback(status, resp_body, args)

    def _call_callback(self, status, body, args):
        try:
            self._callback(status, body, *(args))
        except Exception:
            sys.excepthook(*sys.exc_info())

class AsyncRequest(object):
    '''
        AsyncRequest is an utility for creating HTTP requests using the
        Soup framework. So that all the processing is done in the
        background and does not hog the main UI thread.

        Note that the request callback will be called once the response
        headers have been received. At this stage the body hasn't been
        read yet.

        AsyncRequests supports cancellation using its `cancellable` argument.
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

        self._priority = to_soup_priority(priority)
        self._session = init_session()
        self._address = address
        self._callback = callback
        self._headers = {}
        self._cancellable = cancellable

    def set_header(self, name, value):
        self._headers[name] = value

    def get(self, *args):
        req = Soup.Message.new("GET", self._address)
        self._do(req, args)

    def post(self, content_type, body, *args):
        req = Soup.Message.new("POST", self._address)
        req.set_request_body_from_bytes(content_type, body)
        self._do(req, args)

    def put(self, content_type, body, *args):
        req = Soup.Message.new("PUT", self._address)
        req.set_request_body_from_bytes(content_type, body)
        self._do(req, args)

    def patch(self, content_type, body, *args):
        req = Soup.Message.new("PATCH", self._address)
        req.set_request_body_from_bytes(content_type, body)
        self._do(req, args)

    def delete(self, *args):
        req = Soup.Message.new("DELETE", self._address)
        self._do(req, args)

    def _do(self, req, args):
        try:
            for k, v in self._headers.items():
                req.props.request_headers.append(k, v)
            self._session.send_async(
                req,
                self._priority,
                self._cancellable,
                self._request_cb,
                args,
            )
        except Exception:
            sys.excepthook(*sys.exc_info())
            self._callback(None, None, None, *(args))

    def _request_cb(self, source, result, args):
        message = source.get_async_result_message(result)
        status = message.get_status()
        try:
            body_stream = source.send_finish(result)
        except Exception:
            self._callback(None, None, None, *(args))
            return

        self._call_callback(status, body_stream, args)

    def _call_callback(self, status, data_stream, args):
        try:
            self._callback(status, data_stream, self._cancellable, *(args))
        except Exception:
            sys.excepthook(*sys.exc_info())


def to_soup_priority(priority):
    if priority == Priority.LOW:
        return Soup.MessagePriority.LOW
    elif priority == Priority.HIGH:
        return Soup.MessagePriority.HIGH
    else:
        return Soup.MessagePriority.NORMAL
