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
gi.require_version('GLib', '2.0')

from gi.repository import GLib, Gtk, Handy, Gst
from .player import Player

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
    track_progess = Gtk.Template.Child()

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

        self.track_progess.connect("change-value",
                                self.on_seek)

        Gst.init(None)

        self.track_progess.set_range(0, 1)

        self.play_uri = None
        self.token = None

        self.populate_about()
        self.player = None

    def change_progress(self, prog):
        if prog < 0:
            prog = 0
        if prog > 1:
            prog = 1
        self.track_progess.set_value(prog)

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

        if self.player is not None:
            self._toggle_playing_state(button)
            return

        self.player = Player(self.token, self.play_uri)
        self.player.connect("state-changed",
                              self.on_player_state_changed)
        self.player.play()

    def on_seek(self, slider, scroll, value):
        if scroll != Gtk.ScrollType.JUMP:
            return False

        if self.player is None:
            return

        self.player.seek(value)
        return False

    def _toggle_playing_state(self, button):
        print("executing on toggle playing state button")

        if self.player is None:
            # Nothing to do here, go away!
            return

        if self.player.is_playing():
            self.player.pause()
        else:
            self.player.play()

    def on_player_state_changed(self, player):
        if player is not self.player:
            return

        if player.is_playing():
            self.play_button.set_label("Pause")
            GLib.timeout_add(
                priority=GLib.PRIORITY_DEFAULT,
                function=self._query_progress,
                interval=1000
            )
        else:
            self.play_button.set_label("Play")

        if player.has_ended():
            self.player = None
            self.change_progress(0)

    def _query_progress(self):
        if self.player is None or not self.player.is_playing():
            print("stopping progress timeout callback")
            return False

        progress = self.player.get_progress()
        if progress is None:
            print("could not yet obtain progress")
            return True

        self.change_progress(progress)
        return True

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
