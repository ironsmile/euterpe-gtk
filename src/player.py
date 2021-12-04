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
from .utils import emit_signal
from functools import partial

SIGNAL_PROGRESS = "progress"
SIGNAL_STATE_CHANGED = "state-changed"
SIGNAL_TRACK_CHANGED = "track-changed"
SIGNAL_PLAYLIST_CHANGED = "playlist-changed"


class Player(GObject.Object):
    '''
        Player is the class responsible for dealing with the media playback. It
        holds the playlist and deals with Gstreamer stuff. It provides higher
        level methods such as play/pause/set_playlist and such.
    '''

    __gsignals__ = {
        SIGNAL_STATE_CHANGED: (GObject.SignalFlags.RUN_FIRST, None, ()),
        SIGNAL_TRACK_CHANGED: (GObject.SignalFlags.RUN_FIRST, None, ()),
        SIGNAL_PLAYLIST_CHANGED: (GObject.SignalFlags.RUN_FIRST, None, ()),
        SIGNAL_PROGRESS: (GObject.SignalFlags.RUN_FIRST, None, (float, )),
    }

    def __init__(self, euterpeService):
        GObject.GObject.__init__(self)
        self._playlist = []
        self._current_playlist_index = None
        self._playbin = None
        self._progress_id = 0
        self._service = euterpeService
        self._seek_to = None

    def set_playlist(self, playlist):
        self.stop()
        self._playlist = playlist
        if len(playlist) > 0:
            self._current_playlist_index = 0
        else:
            self._current_playlist_index = None
        emit_signal(self, SIGNAL_PLAYLIST_CHANGED)
        emit_signal(self, SIGNAL_STATE_CHANGED)

    def append_to_playlist(self, tracks):
        if len(tracks) == 0:
            return

        self._playlist.extend(tracks)
        if self._current_playlist_index is None:
            self._current_playlist_index = 0
        emit_signal(self, SIGNAL_PLAYLIST_CHANGED)
        emit_signal(self, SIGNAL_STATE_CHANGED)

    def _load_from_current_index(self):
        '''
            Moves forward the current index if there is one. Stops the
            currently playing track if any and then creates a new playbin.
        '''
        pl_len = len(self._playlist)

        if pl_len == 0:
            return

        if self._current_playlist_index >= pl_len:
            self._current_playlist_index = 0

        track = self._playlist[self._current_playlist_index]
        track_url = self._service.get_track_url(track["id"])
        token = self._service.get_token()

        self._setup_new_playbin(track_url, token)

    def _setup_new_playbin(self, play_uri, token):
        self.stop()

        pipeline = Gst.Pipeline.new('mainpipeline')

        src = Gst.ElementFactory.make("souphttpsrc", "source")
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

        self._playbin = pipeline
        self._seek_to = None
        emit_signal(self, SIGNAL_TRACK_CHANGED)

    def _on_newpad(self, dec, pad, audiosink):
        # TODO: check caps!
        audiopad = audiosink.get_static_pad("sink")
        pad.link(audiopad)

    def _on_bus_error(self, bus, message):
        (error, parsed) = message.parse_error()
        print("playbin error:", parsed)
        self.stop()

    def _on_bus_eos(self, bus, message):
        if message.type != Gst.MessageType.EOS:
            print("unexpected eos message type: {}".format(message.type))
        print("end-of-stream bus message received")

        if self.has_next():
            self.next()
        else:
            self.stop()

    def _on_stream_start(self, bus, message):
        if self._seek_to is None:
            return

        seek_to = self._seek_to
        self._seek_to = None

        seeked = self._playbin.seek_simple(
            Gst.Format.TIME,
            Gst.SeekFlags.FLUSH | Gst.SeekFlags.KEY_UNIT,
            seek_to
        )
        if not seeked:
            print("seeking after state restore failed")

    def _get_progress(self, playbin):
        '''
            Returns the current playback progress in [0:1] range.
            May be None when progress could not be obtained.
        '''
        if playbin is None:
            print("trying to get progress self._playbin which is None")
            return None

        (ok, dur) = playbin.query_duration(Gst.Format.TIME)
        if not ok:
            print("could not query playbin duration in ns")
            return None

        (ok, ns) = playbin.query_position(Gst.Format.TIME)
        if not ok:
            print("could not query playbin position in ns")
            return None

        return ns / dur

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

        (ok, dur) = self._playbin.query_duration(Gst.Format.TIME)
        if not ok:
            print("could not query playbin duration in ns")
            return

        seek_pos = int(dur * val)

        seeked = self._playbin.seek_simple(
            Gst.Format.TIME,
            Gst.SeekFlags.FLUSH | Gst.SeekFlags.KEY_UNIT,
            seek_pos
        )
        if not seeked:
            print("seeking was not succesful")

    def stop(self):
        if self._playbin is None:
            return

        self._playbin.set_state(Gst.State.NULL)
        self._playbin = None
        emit_signal(self, SIGNAL_STATE_CHANGED)

    def play(self):
        if self._playbin is None:
            self._load_from_current_index()

        if self._playbin is None:
            print("trying to play when there are not racks in the playlist")
            return

        self._playbin.set_state(Gst.State.PLAYING)
        emit_signal(self, SIGNAL_STATE_CHANGED)

        self._progress_id += 1

        GLib.timeout_add(
            priority=GLib.PRIORITY_DEFAULT,
            function=partial(self._query_progress, self._progress_id),
            interval=1000
        )

    def _query_progress(self, progress_id):
        playbin = self._playbin

        if playbin is None or not self.is_playing():
            print("no track playing, stopping progress timeout callback")
            return False

        if self._progress_id != progress_id:
            print("progress ID changed, stopping progress timeout callback")
            return False

        progress = self._get_progress(playbin)
        if progress is None:
            print("could not yet obtain progress")
            return True

        emit_signal(self, SIGNAL_PROGRESS, progress)
        return True

    def pause(self):
        if self._playbin is None:
            print("trying to pause when there is no _playbin created")
            return

        self._playbin.set_state(Gst.State.PAUSED)
        emit_signal(self, SIGNAL_STATE_CHANGED)

    def next(self):
        ind = self._current_playlist_index
        ind += 1
        if ind >= len(self._playlist):
            print("trying to play track beyond the playlist length")
            return

        self._current_playlist_index = ind
        self._load_from_current_index()
        self.play()

    def has_next(self):
        if self._current_playlist_index is None:
            return False
        if self._current_playlist_index + 1 >= len(self._playlist):
            return False
        return True

    def has_previous(self):
        if self._current_playlist_index is None:
            return False
        if self._current_playlist_index - 1 < 0:
            return False
        return True

    def previous(self):
        if len(self._playlist) == 0:
            return

        ind = self._current_playlist_index
        ind -= 1
        if ind < 0:
            print("trying to play track before the start of playlist")
            return

        self._current_playlist_index = ind
        self._load_from_current_index()
        self.play()

    def is_playing(self):
        if self._playbin is None:
            return False

        ok, state, pending = self._playbin.get_state(Gst.CLOCK_TIME_NONE)
        if ok == Gst.StateChangeReturn.ASYNC:
            return pending == Gst.State.PLAYING
        elif ok == Gst.StateChangeReturn.SUCCESS:
            return state == Gst.State.PLAYING
        else:
            return False

    def has_ended(self):
        return self._playbin is None

    def get_track_info(self):
        if self._current_playlist_index >= len(self._playlist):
            return None

        return self._playlist[self._current_playlist_index].copy()

    def get_track_index(self):
        '''
        Returns the index of the current track in the playlist.
        '''
        return self._current_playlist_index

    def play_index(self, index):
        if index < 0 or index >= len(self._playlist):
            print("trying to play track outside of the playlist")
            return

        self._current_playlist_index = index
        self._load_from_current_index()
        self.play()

    def is_active(self):
        '''
        Returns true when the player is in state where playback is
        possible. This means it has current index and a playlist.
        '''
        ind = self._current_playlist_index
        pl_len = len(self._playlist)

        return pl_len > 0 and ind is not None

    def get_playlist(self):
        return self._playlist[:]

    def restore_state(self, store):
        state = store.get_object("player_state")
        if state is None:
            return

        if 'playlist' not in state or len(state['playlist']) == 0:
            return

        self._playlist = state['playlist']

        if 'index' in state:
            self._current_playlist_index = state['index']

        if self._current_playlist_index is None:
            return

        self._load_from_current_index()
        emit_signal(self, SIGNAL_PLAYLIST_CHANGED)
        emit_signal(self, SIGNAL_STATE_CHANGED)

        if 'progress' not in state or state['progress'] is None:
            return

        emit_signal(self, SIGNAL_PROGRESS, state['progress'])

        if 'position' in state and state['position'] is not None:
            self._seek_to = state['position']

    def store_state(self, store):
        progress = None
        position = None
        if self._playbin is not None:
            (durOK, dur) = self._playbin.query_duration(Gst.Format.TIME)
            (posOK, pos) = self._playbin.query_position(Gst.Format.TIME)
            if durOK and posOK:
                position = pos
                progress = pos / dur

        state = {
            "index": self._current_playlist_index,
            "playlist": self._playlist,
            "progress": progress,
            "position": position,
        }

        store.set_object("player_state", state)
