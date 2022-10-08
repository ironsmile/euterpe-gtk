pkgdatadir = join_paths(get_option('prefix'), get_option('datadir'), meson.project_name())
moduledir = join_paths(pkgdatadir, 'euterpe_gtk')
widgetsdir = join_paths(pkgdatadir, 'euterpe_gtk', 'widgets')
logdir = join_paths(pkgdatadir, 'euterpe_gtk', 'log')
gnome = import('gnome')

gnome.compile_resources('euterpe-gtk',
  'euterpe_gtk.gresource.xml',
  gresource_bundle: true,
  install: true,
  install_dir: pkgdatadir,
)

python = import('python')

conf = configuration_data()
conf.set('PYTHON', python.find_installation('python3').path())
conf.set('VERSION', meson.project_version())
conf.set('localedir', join_paths(get_option('prefix'), get_option('localedir')))
conf.set('pkgdatadir', pkgdatadir)

configure_file(
  input: 'euterpe-gtk.in',
  output: 'euterpe-gtk',
  configuration: conf,
  install: true,
  install_dir: get_option('bindir')
)

euterpe_gtk_sources = [
  '__init__.py',
  'main.py',
  'player.py',
  'service.py',
  'utils.py',
  'http.py',
  'navigator.py',
  'state_storage.py',
  'mpris.py',
  'async_artwork.py',
]

install_data(euterpe_gtk_sources, install_dir: moduledir)

euterpe_gtk_widgets_package = [
  'widgets/__init__.py',
  'widgets/album.py',
  'widgets/artist.py',
  'widgets/track.py',
  'widgets/window.py',
  'widgets/box_album.py',
  'widgets/box_artist.py',
  'widgets/browse_screen.py',
  'widgets/search_screen.py',
  'widgets/home_screen.py',
  'widgets/small_album.py',
  'widgets/small_artist.py',
  'widgets/mini_player.py',
  'widgets/player_ui.py',
  'widgets/paginated_box_list.py',
  'widgets/entry.py',
  'widgets/entry_list.py',
  'widgets/simple_list.py',
  'widgets/login_form.py',
  'widgets/regenerate_token.py',
]

install_data(euterpe_gtk_widgets_package, install_dir: widgetsdir)

euterpe_gtk_log_package = [
  'log/__init__.py',
  'log/log.py',
]

install_data(euterpe_gtk_log_package, install_dir: logdir)
