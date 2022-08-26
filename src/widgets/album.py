# album.py
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

from gi.repository import GObject, Gtk
from euterpe_gtk.widgets.track import EuterpeTrack
from euterpe_gtk.async_artwork import AsyncArtwork
import euterpe_gtk.log as log


@Gtk.Template(resource_path='/com/doycho/euterpe/gtk/ui/album.ui')
class EuterpeAlbum(Gtk.Viewport):
    __gtype_name__ = 'EuterpeAlbum'

    __gsignals__ = {}

    play_button = Gtk.Template.Child()
    album_name = Gtk.Template.Child()
    artist_info = Gtk.Template.Child()
    more_button = Gtk.Template.Child()
    track_list = Gtk.Template.Child()
    loading_spinner = Gtk.Template.Child()
    append_to_queue = Gtk.Template.Child()
    image = Gtk.Template.Child()

    def __init__(self, album, win, **kwargs):
        super().__init__(**kwargs)

        self._win = win
        self._album = album
        self._album_tracks = []

        album_name = album.get("album", "Unknown")

        self.album_name.set_label(album.get("album", "Unknown"))
        self.artist_info.set_label("ALBUM BY {}".format(
            album.get("artist", "Unknown").upper()
        ))

        win.get_euterpe().search(album_name, self._on_search_result)
        self.play_button.connect(
            "clicked",
            self._on_play_button
        )
        self.append_to_queue.connect(
            "clicked",
            self._on_append_button
        )

        for obj in [self.play_button, self.more_button]:
            self.loading_spinner.bind_property(
                'active',
                obj, 'sensitive',
                GObject.BindingFlags.INVERT_BOOLEAN
            )

        self.connect("unrealize", self._on_unrealize)
        self._init_artwork(album)
        self.connect("destroy", self._on_destroy)

    def _init_artwork(self, album):
        album_id = album.get("album_id", None)
        if album_id is None:
            log.warning("EuterpeAlbum: no album ID found for {}", album)
            return

        self._artwork_loader = AsyncArtwork(self.image, 330)
        self._artwork_loader.load_album_image(album_id)

    def _on_destroy(self, *args):
        self._artwork_loader.cancel()

    def _on_play_button(self, pb):
        player = self._win.get_player()
        player.set_playlist(self._album_tracks)
        player.play()

    def _on_append_button(self, ab):
        player = self._win.get_player()
        player.append_to_playlist(self._album_tracks)

    def _on_search_result(self, status, body, query):
        self.track_list.foreach(self.track_list.remove)

        if status != 200:
            label = Gtk.Label.new()
            label.set_text(
                "Error getting album. HTTP response code {}.".format(
                    status
                )
            )
            self.track_list.add(label)
            label.show()
            return

        album_tracks = []
        for track in body:
            if track["album_id"] != self._album["album_id"]:
                continue
            album_tracks.append(track)

        if len(album_tracks) == 0:
            label = Gtk.Label.new()
            label.set_text("No tracks found.")
            self.track_list.add(label)
            label.show()
            return

        self._album_tracks = sorted(
            album_tracks,
            key=lambda t: t["track"],
        )

        for track in self._album_tracks:
            tr_obj = EuterpeTrack(track)
            self.track_list.add(tr_obj)
            tr_obj.connect("play-button-clicked", self.on_track_play_clicked)
            while (Gtk.events_pending()):
                Gtk.main_iteration()

    def on_track_play_clicked(self, track_widget):
        track = track_widget.get_track()
        player = self._win.get_player()
        player.set_playlist([track])
        player.play()

    def _on_unrealize(self, *args):
        for child in self.track_list.get_children():
            child.destroy()
