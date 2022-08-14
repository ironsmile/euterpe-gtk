# logging.py
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

import gi
from gi.repository import GLib

def debug(msg, *args):
    _log(GLib.LogLevelFlags.LEVEL_DEBUG, msg, *args)

def message(msg, *args):
    _log(GLib.LogLevelFlags.LEVEL_MESSAGE, msg, *args)

def warning(msg, *args):
    _log(GLib.LogLevelFlags.LEVEL_WARNING, msg, *args)

def error(msg, *args):
    _log(GLib.LogLevelFlags.LEVEL_ERROR, msg, *args)

def _log(level, msg, *args):
    v = GLib.Variant.new_string(msg.format(*args))

    vd = GLib.VariantDict.new()
    vd.insert_value("MESSAGE", v)

    GLib.log_variant("euterpe-gtk", level, vd.end())