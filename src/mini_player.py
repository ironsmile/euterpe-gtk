from gi.repository import GObject, Gtk


@Gtk.Template(resource_path='/com/doycho/euterpe/gtk/ui/mini-player.ui')
class EuterpeMiniPlayer(Gtk.Viewport):
    __gtype_name__ = 'EuterpeMiniPlayer'

    __gsignals__ = {}

    play_pause_button = Gtk.Template.Child()
    track_name = Gtk.Template.Child()
    artist_name = Gtk.Template.Child()
    track_progess = Gtk.Template.Child()
    play_button_icon = Gtk.Template.Child()
    pause_button_icon = Gtk.Template.Child()

    def __init__(self, player, **kwargs):
        super().__init__(**kwargs)

        self._player = player

        self.play_pause_button.connect(
            "clicked",
            self.on_play_button_clicked
        )
        self._player.connect(
            "state-changed",
            self.on_player_state_changed
        )
        self._player.connect(
            "progress",
            self.on_track_progress_changed
        )
        self._player.connect(
            "track-changed",
            self.on_track_changed
        )

    def on_player_state_changed(self, player):
        if player is not self._player:
            return

        if player.is_active():
            self.show()

        if player.is_playing():
            self.play_pause_button.set_image(self.pause_button_icon)
        else:
            self.play_pause_button.set_image(self.play_button_icon)

        if player.has_ended():
            self.change_progress(0)

    def on_track_progress_changed(self, player, progress):
        self.change_progress(progress)

    def on_track_changed(self, player):
        track = player.get_track_info()
        if track is None:
            return

        self.track_name.set_label(track.get("title", "n/a"))
        self.artist_name.set_label(track.get("artist", "n/a"))

    def change_progress(self, prog):
        if prog < 0:
            prog = 0
        if prog > 1:
            prog = 1
        self.track_progess.set_fraction(prog)

    def on_play_button_clicked(self, btn):
        if self._player is None:
            return

        if self._player.is_playing():
            self._player.pause()
        else:
            self._player.play()
