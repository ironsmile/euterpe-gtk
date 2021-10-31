from gi.repository import GObject, Gtk
from .utils import emit_signal


PLAY_BUTTON_CLICKED = "play-button-clicked"


@Gtk.Template(resource_path='/com/doycho/euterpe/gtk/ui/track.ui')
class EuterpeTrack(Gtk.Viewport):
    __gtype_name__ = 'EuterpeTrack'

    __gsignals__ = {
        PLAY_BUTTON_CLICKED: (GObject.SignalFlags.RUN_FIRST, None, ()),
    }

    track_name = Gtk.Template.Child()
    track_info = Gtk.Template.Child()
    track_play_button = Gtk.Template.Child()

    def __init__(self, track, **kwargs):
        super().__init__(**kwargs)

        self._track = track
        self.track_name.set_label(track.get("title", "<N/A>"))
        self.track_info.set_label(
            "{}, {}".format(
                track.get("artist", "<N/A>"),
                track.get("album", "<N/A>"),
            )
        )

        self.track_play_button.connect("clicked", self._on_play_button)

    def _on_play_button(self, pb):
        emit_signal(self, PLAY_BUTTON_CLICKED)

    def get_track(self):
        return self._track.copy()
