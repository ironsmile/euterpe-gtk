# state_storage.py
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

import json
import os
from gi.repository import GLib
from euterpe_gtk.player import Repeat, Shuffle
import euterpe_gtk.log as log


class EuterpeEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, Repeat) or isinstance(obj, Shuffle):
            return obj.name
        return super().default(obj)


class StateStorage:

    def __init__(self, config_file, namespace):
        self._config_file = config_file
        self._namespace = namespace
        self._kf = GLib.KeyFile.new()

    def load(self):
        '''
        load reds the storage file from disk and loads into self.
        '''
        try:
            self._kf.load_from_file(self._config_file, GLib.KeyFileFlags.NONE)
        except GLib.Error as err:
            log.warning('Loading configuration file ({}) failed: {}',
                self._config_file,
                err,
            )

    def save(self):
        '''
        save stores the current data in the storage to its file on disk.
        '''
        self._store_kf_file()

    def set_string(self, key, value, namespace=None):
        self._kf.set_string(self._get_namespace(namespace), key, value)

    def set_many(self, kvs, namespace=None):
        namespace = self._get_namespace(namespace)
        for k, v in kvs.items():
            if isinstance(v, int):
                self._kf.set_integer(namespace, k, v)
            elif isinstance(v, str):
                self._kf.set_string(namespace, k, v)
            elif isinstance(v, bool):
                self._kf.set_boolean(namespace, k, v)
            elif isinstance(v, float):
                self._kf.set_double(namespace, k, v)
            else:
                raise ValueError(
                    "cannot set item of type {} it set_many for key {}".format(
                        type(v),
                        k
                    )
                )

    def set_boolean(self, key, value, namespace=None):
        self._kf.set_boolean(self._get_namespace(namespace), key, value)

    def set_integer(self, key, value, namespace=None):
        self._kf.set_integer(self._get_namespace(namespace), key, value)

    def get_string(self, key, namespace=None):
        try:
            return self._kf.get_string(self._get_namespace(namespace), key)
        except Exception:
            return ""

    def get_integer(self, key, namespace=None):
        try:
            return self._kf.get_integer(self._get_namespace(namespace), key)
        except Exception:
            return 0

    def get_boolean(self, key, namespace=None):
        try:
            return self._kf.get_boolean(self._get_namespace(namespace), key)
        except Exception:
            return False

    def set_object(self, key, object, namespace=None):
        try:
            object_str = json.dumps(object, cls=EuterpeEncoder)
        except ValueError as err:
            log.warning("Storing object with key {} to storage failed: {}",
                key, err
            )
            return
        self.set_string(key, object_str, namespace=namespace)

    def get_object(self, key, namespace=None):
        object_str = self.get_string(key, namespace=namespace)
        if object_str == "":
            return None

        try:
            return json.loads(object_str)
        except ValueError as err:
            log.warning("Parsing object with key {} as JSON: {}",
                key, err
            )

        return None

    def truncate(self):
        '''
        Truncate removes everything stored settings in the storage file.
        '''
        try:
            os.remove(self._config_file)
        except Exception as err:
            log.warning("Truncating {} failed: {}",
                self._config_file,
                err
            )

        self._kf = GLib.KeyFile.new()

    def _get_namespace(self, namespace):
        if namespace is None:
            return self._namespace

        return namespace

    def _store_kf_file(self):
        try:
            self._kf.save_to_file(self._config_file)
        except GLib.Error as err:
            log.warning('Saving configuration file failed: {}', err)
