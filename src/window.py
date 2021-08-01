# window.py
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

import sys
import gi
gi.require_version('Handy', '1')
gi.require_version('Gst', '1.0')

from gi.repository import Gtk, Handy, Gst


@Gtk.Template(resource_path='/com/doycho/euterpe/gtk/window.ui')
class EuterpeGtkWindow(Gtk.ApplicationWindow):
    __gtype_name__ = 'EuterpeGtkWindow'

    Handy.init()

    squeezer = Gtk.Template.Child()
    headerbar_switcher = Gtk.Template.Child()
    bottom_switcher = Gtk.Template.Child()

    about_gtk_version = Gtk.Template.Child()
    about_gstreamer_version = Gtk.Template.Child()
    about_python_version = Gtk.Template.Child()

    input_token = Gtk.Template.Child()
    input_track_url = Gtk.Template.Child()
    play_button = Gtk.Template.Child()

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        self.squeezer.connect("notify::visible-child",
                              self.on_headerbar_squeezer_notify)
        self.play_button.connect("clicked",
                              self.on_play_button_clicked)
        self.input_token.connect("changed",
                              self.on_token_changed)
        self.input_track_url.connect("changed",
                              self.on_track_changed)

        Gst.init(None)

        self.play_uri = None
        self.token = None

        self.populate_about()
        self.playbin = None

    def on_token_changed(self, entry):
        text = entry.get_text()
        if len(text) > 0:
            self.token = text
        else:
            self.token = None

    def on_track_changed(self, entry):
        text = entry.get_text()
        if len(text) > 0:
            self.play_uri = text
        else:
            self.play_uri = None

    def on_headerbar_squeezer_notify(self, squeezer, event):
	    child = squeezer.get_visible_child()
	    self.bottom_switcher.set_reveal(child != self.headerbar_switcher)

    def on_play_button_clicked(self, button):
        print("play button clicked")

        if self.play_uri is None:
            print("no play URI!")
            return

        if self.token is None:
            print("no token!")
            return

        if self.playbin is not None:
            self.playbin.set_state(Gst.State.NULL)
            self.playbin = None

        pipeline = Gst.Pipeline.new('mainpipeline')

        src = Gst.ElementFactory.make("curlhttpsrc", "source");
        src.set_property('location', self.play_uri)

        headers = Gst.Structure.new_empty('extra-headers')
        headers.set_value("Authorization", "Bearer " + self.token)
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

        pipeline.set_state(Gst.State.PLAYING)
        self.playbin = pipeline

    def _on_newpad(self, dec, pad, audiosink):
        print("newpad called")
        #TODO: check caps!
        audiopad = audiosink.get_static_pad("sink")
        pad.link(audiopad)

    def _on_bus_eos(self, bus, message):
        print("playbin message: EOS")
        self.playbin.set_state(Gst.State.NULL)
        self.playbin = None

    def _on_stream_start(self, bus, message):
        print("playbin stream_start", message)

    def _on_bus_error(self, bus, message):
        (error, parsed) = message.parse_error()
        # App().notify.send("Lollypop", parsed)
        print("playbin error:", parsed)
        self.playbin.set_state(Gst.State.NULL)

    def populate_about(self):
        self.about_python_version.set_label('{}.{}.{}'.format(
            sys.version_info.major,
            sys.version_info.minor,
            sys.version_info.micro,
        ))

        gstVer = Gst.version()
        self.about_gstreamer_version.set_label('{}.{}.{}'.format(
            gstVer.major,
            gstVer.minor,
            gstVer.micro
        ))

        self.about_gtk_version.set_label('{}.{}.{}'.format(
            Gtk.get_major_version(),
            Gtk.get_minor_version(),
            Gtk.get_micro_version()
        ))
