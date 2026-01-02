# carousel_item.py
#
# Copyright 2026 Doychin Atanasov
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

from gi.repository import Gtk
import euterpe_gtk.log as log
from euterpe_gtk.async_artwork import AsyncArtwork

@Gtk.Template(resource_path='/com/doycho/euterpe/gtk/ui/carousel-item.ui')
class EuterpeCarouselItem(Gtk.Button):
    '''
    This is a widget which displays an album as a carousel item.
    '''
    __gtype_name__ = 'EuterpeCarouselItem'

    __gsignals__ = {}

    image = Gtk.Template.Child()
    title = Gtk.Template.Child()
    description = Gtk.Template.Child()

    def __init__(self, album=None, title=None, icon_name=None, desc=None, **kwargs):
        super().__init__(**kwargs)

        self._album = None
        self._artwork_loader = None
        if album is not None:
            self.set_album(album)
        elif title is not None:
            self.set_static(title, icon_name, desc)

        self.connect("destroy", self._on_destroy)

    def set_static(self, title, icon_name, description):
        self.title.set_label(title)
        if description is not None:
            self.description.set_label(description)
        if icon_name is not None:
            self.image.set_from_icon_name(icon_name, 128)

    def set_album(self, album):
        self._album = album

        self.title.set_label(album.get("album", "N/A"))
        desc = album.get("artist", "Unknown Artist")

        if "year" in album:
            desc += " ({})".format(album["year"])

        if "avg_bitrate" in album:
            desc += ", {:d} kbps".format(
                int(album["avg_bitrate"] / 1024)
            )

        self.description.set_label(desc)

        self._artwork_loader = None
        album_id = album.get("album_id", None)
        if album_id is not None:
            self._artwork_loader = AsyncArtwork(self.image, 128)
            self._artwork_loader.load_album_image(album_id)

    def get_album(self):
        return self._album

    def _on_destroy(self, *args):
        if self._artwork_loader is not None:
            self._artwork_loader.cancel()
