# mpris.py
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

from gi.repository import Gio, GLib, Gtk
from euterpe_gtk.player import Repeat, Shuffle
import euterpe_gtk.log as log


class MPRIS:
    '''
    MPRIS is a class which deals with setting up the The Media Player
    Remote Interfacing Specification with D-Bus.
    '''

    MPRIS_DBUS_OWN_NAME = 'org.mpris.MediaPlayer2.Euterpe-Gtk'
    MPRIS_INTERFACE = 'org.mpris.MediaPlayer2'
    MPRIS_INTERFACE_PLAYER = 'org.mpris.MediaPlayer2.Player'
    MPRIS_PATH = '/org/mpris/MediaPlayer2'
    NO_TRACK_ID = '/org/mpris/MediaPlayer2/TrackList/NoTrack'

    def __init__(self, app):
        self._app = app
        self._player = app.get_player()

        self._method_outargs = {}
        self._method_inargs = {}

        self._bus = Gio.bus_get_sync(Gio.BusType.SESSION, None)
        Gio.bus_own_name_on_connection(
            self._bus,
            self.MPRIS_DBUS_OWN_NAME,
            Gio.BusNameOwnerFlags.NONE,
            None,
            None
        )
        self._xml = ''

        self._register_interfaces()
        self._track_info = self._get_empty_track()

        self._player.connect("track-changed", self._on_track_changed)
        self._player.connect("state-changed", self._on_state_changed)
        self._player.connect("repeat-changed", self._on_repeat_changed)
        self._player.connect("shuffle-changed", self._on_shuffle_changed)
        self._player.connect("volume-changed", self._on_volume_changed)
        self._player.connect("seeked", self._on_seeked)

    def Introspect(self):
        return self._xml

    def Set(self, interface, property_name, new_value):
        if property_name == "Shuffle":
            val = Shuffle.NONE
            if new_value:
                val = Shuffle.QUEUE
            self._player.set_shuffle(val)
        elif property_name == "LoopStatus":
            val = Repeat.NONE
            if new_value == "Playlist":
                val = Repeat.QUEUE
            elif new_value == "Track":
                val = Repeat.SONG
            self._player.set_repeat(val)
        elif property_name == "Volume":
            self._player.set_volume(new_value)
        else:
            log.debug("MPRIS: Setting {} to {}", property_name, new_value)

    def Get(self, interface, property_name):
        if property_name in [
            "CanQuit",
            "CanRaise",
            "CanControl",
        ]:
            return GLib.Variant("b", True)
        elif property_name in [
            "HasTrackList",
            "HasRatingsExtension",
            "CanEditTracks",
            "Fullscreen",
        ]:
            return GLib.Variant("b", False)
        elif property_name == "Shuffle":
            return GLib.Variant("b", self._get_player_shuffle_status())
        elif property_name in ["Rate", "MinimumRate", "MaximumRate"]:
            return GLib.Variant("d", 1.0)
        elif property_name == "Identity":
            return GLib.Variant("s", "Euterpe")
        elif property_name == "DesktopEntry":
            return GLib.Variant("s", "com.doycho.euterpe.gtk")
        elif property_name == "SupportedUriSchemes":
            return GLib.Variant("as", [])
        elif property_name == "SupportedMimeTypes":
            return GLib.Variant("as", [])
        elif property_name == "PlaybackStatus":
            return GLib.Variant("s", self._get_player_status())
        elif property_name == "LoopStatus":
            return GLib.Variant("s", self._get_player_loop_status())
        elif property_name == "Metadata":
            return GLib.Variant("a{sv}", self._track_info)
        elif property_name == "Volume":
            return GLib.Variant("d", self._player.get_volume())
        elif property_name == "Position":
            pos = 0
            ppos = self._player.get_position()
            if ppos is not None:
                pos = ppos * 1000

            return GLib.Variant("x", pos)
        elif property_name == "CanGoNext":
            return GLib.Variant("b", self._player.has_next())
        elif property_name == "CanGoPrevious":
            return GLib.Variant("b", self._player.has_previous())
        elif property_name in [
            "CanSeek",
            "CanPlay",
            "CanPause",
        ]:
            return GLib.Variant("b", self._player.is_active())

    def GetAll(self, interface):
        ret = {}
        if interface == self.MPRIS_INTERFACE:
            for property_name in ["CanQuit",
                                  "CanRaise",
                                  "HasTrackList",
                                  "Identity",
                                  "DesktopEntry",
                                  "SupportedUriSchemes",
                                  "SupportedMimeTypes",
                                  "Fullscreen"]:
                ret[property_name] = self.Get(interface, property_name)
        elif interface == self.MPRIS_INTERFACE_PLAYER:
            for property_name in ["PlaybackStatus",
                                  "LoopStatus",
                                  "Rate",
                                  "Shuffle",
                                  "Metadata",
                                  "Volume",
                                  "Position",
                                  "MinimumRate",
                                  "MaximumRate",
                                  "CanGoNext",
                                  "CanGoPrevious",
                                  "CanPlay",
                                  "CanPause",
                                  "CanSeek",
                                  "CanControl"]:
                ret[property_name] = self.Get(interface, property_name)
        return ret

    def Raise(self):
        self._app.window.present_with_time(Gtk.get_current_event_time())

    def Quit(self):
        self._app.on_quit()

    def Next(self):
        self._player.next()

    def Previous(self):
        self._player.previous()

    def Pause(self):
        self._player.pause()

    def PlayPause(self):
        if self._player.is_playing():
            self._player.pause()
        else:
            self._player.play()

    def Stop(self):
        self._player.stop()

    def Play(self):
        self._player.play()

    def Seek(self, offset):
        """
        Seeks forward in the current track by the specified number of
        microseconds.

        A negative value seeks back. If this would mean seeking back
        further than the start of the track, the position is set to 0.

        If the value passed in would mean seeking beyond the end of
        the track, acts like a call to Next.
        """
        offset_ms = offset / 1000
        self._player.seek_with(offset_ms)

    def PropertiesChanged(
        self,
        interface_name,
        changed_properties,
        invalidated_properties
    ):
        self._bus.emit_signal(
            None,
            self.MPRIS_PATH,
            "org.freedesktop.DBus.Properties",
            "PropertiesChanged",
            GLib.Variant.new_tuple(
                GLib.Variant("s", interface_name),
                GLib.Variant("a{sv}", changed_properties),
                GLib.Variant("as", invalidated_properties)
            )
        )

    def _get_empty_track(self):
        return {
            "mpris:trackid": GLib.Variant("o", self.NO_TRACK_ID),
        }

    def _register_interfaces(self):
        xml_file = Gio.resources_lookup_data(
            "/com/doycho/euterpe/gtk/assets/d-bus.xml",
            Gio.ResourceLookupFlags.NONE
        ).get_data()

        self._xml = str(xml_file, encoding='utf-8')

        method_outargs = {}
        method_inargs = {}
        for interface in Gio.DBusNodeInfo.new_for_xml(self._xml).interfaces:

            for method in interface.methods:
                method_outargs[method.name] = "(" + "".join(
                              [arg.signature for arg in method.out_args]) + ")"
                method_inargs[method.name] = tuple(
                    arg.signature for arg in method.in_args)

            self._bus.register_object(
                object_path=self.MPRIS_PATH,
                interface_info=interface,
                method_call_closure=self._on_method_call
            )

        self._method_inargs = method_inargs
        self._method_outargs = method_outargs

    def _on_method_call(
        self,
        connection,
        sender,
        object_path,
        interface_name,
        method_name,
        parameters,
        invocation
    ):
        args = list(parameters.unpack())
        for i, sig in enumerate(self._method_inargs[method_name]):
            if sig == "h":
                msg = invocation.get_message()
                fd_list = msg.get_unix_fd_list()
                args[i] = fd_list.get(args[i])

        try:
            result = getattr(self, method_name)(*args)

            # out_args is atleast (signature1).
            # We therefore always wrap the result as a tuple.
            # Refer to https://bugzilla.gnome.org/show_bug.cgi?id=765603
            result = (result,)

            out_args = self._method_outargs[method_name]
            if out_args != "()":
                variant = GLib.Variant(out_args, result)
                invocation.return_value(variant)
            else:
                invocation.return_value(None)
        except Exception as err:
            log.warning("MPRIS: Error invoking D-BUS {}: {}",
                method_name,
                err
            )

    def _on_track_changed(self, player):
        self._track_info = self._get_empty_track()
        track = self._player.get_track_info()
        if track is None:
            return

        self._track_info = {
            "mpris:trackid": GLib.Variant(
                "o",
                "/com/doycho/euterpe/gtk/track/{}/{}".format(
                    track["id"],
                    player.get_track_index()
                )
            ),
            "mpris:length": GLib.Variant("x", track.get("duration", 0) * 1000),
            "xesam:title": GLib.Variant(
                "s",
                track.get("title", "Unknown Title")
            ),
            "xesam:album": GLib.Variant(
                "s",
                track.get("album", "Unknown Album")
            ),
            "xesam:albumArtist": GLib.Variant(
                "as",
                [track.get("artist", "Unknown Artist")]
            ),
            "xesam:artist": GLib.Variant(
                "as",
                [track.get("artist", "Unknown Artist")]
            ),
            "xesam:trackNumber": GLib.Variant("x", track.get("track", 0)),
        }

        fmt = track.get("format", None)
        if fmt is not None:
            self._track_info["xesam:comment"] = GLib.Variant(
                "as",
                ["Format: {}".format(fmt)]
            )

    def _on_state_changed(self, player):
        if player.has_ended():
            self._track_info = self._get_empty_track()

        is_active = player.is_active()

        properties = {
            "Metadata": GLib.Variant("a{sv}", self._track_info),
            "CanPlay": GLib.Variant("b", is_active),
            "CanPause": GLib.Variant("b", is_active),
            "CanGoNext": GLib.Variant("b", player.has_next()),
            "CanGoPrevious": GLib.Variant("b", player.has_previous()),
            "PlaybackStatus": GLib.Variant("s", self._get_player_status()),
        }

        self.PropertiesChanged(self.MPRIS_INTERFACE_PLAYER, properties, [])

    def _on_repeat_changed(self, player):
        properties = {
            "CanGoNext": GLib.Variant("b", player.has_next()),
            "CanGoPrevious": GLib.Variant("b", player.has_previous()),
            "LoopStatus": GLib.Variant("s", self._get_player_loop_status()),
        }
        self.PropertiesChanged(self.MPRIS_INTERFACE_PLAYER, properties, [])

    def _on_shuffle_changed(self, player):
        properties = {
            "CanGoNext": GLib.Variant("b", player.has_next()),
            "CanGoPrevious": GLib.Variant("b", player.has_previous()),
            "Shuffle": GLib.Variant("b", self._get_player_shuffle_status()),
        }
        self.PropertiesChanged(self.MPRIS_INTERFACE_PLAYER, properties, [])

    def _on_volume_changed(self, player, vol):
        properties = {
            "Volume": GLib.Variant("d", player.get_volume()),
        }
        self.PropertiesChanged(self.MPRIS_INTERFACE_PLAYER, properties, [])

    def _on_seeked(self, player):
        pos = player.get_position()
        if pos is None:
            return

        pos_micro = int(pos * 1e3)
        self._bus.emit_signal(
            None,
            self.MPRIS_PATH,
            self.MPRIS_INTERFACE_PLAYER,
            "Seeked",
            GLib.Variant.new_tuple(
                GLib.Variant("x", pos_micro)
            )
        )

    def _get_player_status(self):
        status = "Stopped"
        if self._player.is_active():
            if self._player.is_playing():
                status = "Playing"
            else:
                status = "Paused"

        return status

    def _get_player_loop_status(self):
        repeat = self._player.get_repeat()
        if repeat == Repeat.SONG:
            return "Track"
        elif repeat == Repeat.QUEUE:
            return "Playlist"
        else:
            return "None"

    def _get_player_shuffle_status(self):
        if self._player.get_shuffle() == Shuffle.QUEUE:
            return True
        return False
