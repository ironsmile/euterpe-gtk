project('euterpe-gtk',
          version: '0.8.0',
    meson_version: '>= 0.50.0',
  default_options: [ 'warning_level=2',
                   ],
)
dependency('libhandy-1', version: '>= 1.8.3')

i18n = import('i18n')



subdir('data')
subdir('src')
subdir('po')

meson.add_install_script('build-aux/meson/postinstall.py')
