pkgdatadir = join_paths(get_option('prefix'), get_option('datadir'), meson.project_name())
moduledir = join_paths(pkgdatadir, 'euterpe_gtk')
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
  'window.py',
  'player.py',
  'service.py',
  'utils.py',
  'http.py',
  'track.py',
  'browse_screen.py',
  'search_screen.py',
  'small_album.py',
  'small_artist.py',
  'album.py',
  'mini_player.py',
]

install_data(euterpe_gtk_sources, install_dir: moduledir)
