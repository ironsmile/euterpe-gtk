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
            print('Loading configuration file ({}) failed: {}'.format(
                self._config_file,
                err,
            ))

    def set_string(self, key, value):
        self._kf.set_string(self._namespace, key, value)
        self._store_kf_file()

    def get_string(self, key):
        return self._kf.get_string(self._namespace, key)

    def set_object(self, key, object):
        try:
            object_str = json.dumps(object)
        except ValueError as err:
            print("Storing object with key {} to storage failed: {}".format(
                key, err
            ))
            return
        self.set_string(key, object_str)

    def get_object(self, key):
        object_str = self.get_string(key)
        if object_str == "":
            return None

        try:
            return json.loads(object_str)
        except ValueError as err:
            print("Parsing object with key {} as JSON: {}".format(
                key, err
            ))

        return None

    def truncate(self):
        '''
        Truncate removes everything stored settings in the storage file.
        '''
        try:
            os.remove(self._config_file)
        except Exception as err:
            print("Truncating {} failed: {}".format(
                self._config_file,
                err
            ))

        self._kf = GLib.KeyFile.new()

    def _store_kf_file(self):
        try:
            self._kf.save_to_file(self._config_file)
        except GLib.Error as err:
            print('Saving configuration file failed: {}'.format(err))
