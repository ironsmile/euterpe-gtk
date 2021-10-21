# player.py
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

from gi.repository import GObject, GLib, Gst
from threading import current_thread

class Player(GObject.Object):

    __gsignals__ = {
        "state-changed": (GObject.SignalFlags.RUN_FIRST, None, ()),
    }

    def __init__(self, play_uri, token):
        GObject.GObject.__init__(self)

        pipeline = Gst.Pipeline.new('mainpipeline')

        src = Gst.ElementFactory.make("curlhttpsrc", "source")
        src.set_property('location', play_uri)
        src.set_property('user-agent', "Euterpe GTK Gstreamer")
        src.set_property('timeout', 30)

        if token is not None:
            headers = Gst.Structure.new_empty('extra-headers')
            headers.set_value("Authorization", "Bearer " + token)
            src.set_property('extra-headers', headers)

        dec = Gst.ElementFactory.make("decodebin", "decoder")

        pipeline.add(src)
        pipeline.add(dec)
        src.link(dec)

        audio = Gst.Bin.new('audiobin')
        conv = Gst.ElementFactory.make("audioconvert", "aconv")
        audiopad = conv.get_static_pad("sink")
        sink = Gst.ElementFactory.make("autoaudiosink", "output")
        audio.add(conv)
        audio.add(sink)
        conv.link(sink)
        audio.add_pad(Gst.GhostPad.new('sink', audiopad))
        pipeline.add(audio)

        dec.connect("pad-added", self._on_newpad, audio)

        bus = pipeline.get_bus()
        bus.add_signal_watch()
        bus.connect("message::error", self._on_bus_error)
        bus.connect("message::eos", self._on_bus_eos)
        bus.connect("message::stream-start", self._on_stream_start)

        self.playbin = pipeline

    def _on_newpad(self, dec, pad, audiosink):
        print("newpad called")
        #TODO: check caps!
        audiopad = audiosink.get_static_pad("sink")
        pad.link(audiopad)

    def _on_bus_error(self, bus, message):
        (error, parsed) = message.parse_error()
        print("playbin error:", parsed)
        self.stop()

    def _on_bus_eos(self, bus, message):
        print("playbin message: EOS")
        self.stop()

    def _on_stream_start(self, bus, message):
        print("playbin stream_start", message)

    def get_progress(self):
        '''
            Returns the current playback progress in [0:1] range.
            May be None when progress could not be obtained.
        '''
        (ok, dur) = self.playbin.query_duration(Gst.Format.TIME)
        if not ok:
            print("could not query playbin duration in ns")
            return None

        (ok, ns) = self.playbin.query_position(Gst.Format.TIME)
        if not ok:
            print("could not query playbin position in ns")
            return None

        return ns/dur

    def seek(self, position):
        '''
            Seek to a new position in the playbin. position
            must be between 0 and 1. Values outside this range
            will be clamped.
        '''
        val = position
        if position > 1:
            val = 1
        if position < 0:
            val = 0

        (ok, dur) = self.playbin.query_duration(Gst.Format.TIME)
        if not ok:
            print("could not query playbin duration in ns")
            return

        seek_pos = int(dur * val)
        print("seeking to", val, seek_pos)

        seeked = self.playbin.seek_simple(Gst.Format.TIME,
                                      Gst.SeekFlags.FLUSH |
                                      Gst.SeekFlags.KEY_UNIT,
                                      seek_pos)
        if not seeked:
            print("seeking was not succesful")

    def stop(self):
        self.playbin.set_state(Gst.State.NULL)
        self.playbin = None
        emit_signal(self, "state-changed")

    def play(self):
        self.playbin.set_state(Gst.State.PLAYING)
        emit_signal(self, "state-changed")

    def pause(self):
        self.playbin.set_state(Gst.State.PAUSED)
        emit_signal(self, "state-changed")

    def is_playing(self):
        if self.playbin is None:
            return False

        ok, state, pending = self.playbin.get_state(Gst.CLOCK_TIME_NONE)
        if ok == Gst.StateChangeReturn.ASYNC:
            return pending == Gst.State.PLAYING
        elif ok == Gst.StateChangeReturn.SUCCESS:
            return state == Gst.State.PLAYING
        else:
            return False

    def has_ended(self):
        return self.playbin is None


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


