import os

from threading import current_thread
from gi.repository import GLib


def emit_signal(obj, signal, *args):
    """
        Emit signal
        @param obj as GObject.Object
        @param signal as str
        @thread safe
    """
    if current_thread().getName() == "MainThread":
        obj.emit(signal, *args)
    else:
        GLib.idle_add(obj.emit, signal, *args)


def config_file_name():
    config_dir = GLib.get_user_config_dir()
    return os.path.join(config_dir, 'euterpe.config')
