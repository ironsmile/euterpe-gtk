# Euterpe GTK

This is a convergent desktop and mobile client for [Euterpe](https://listen-to-euterpe.eu).
It is developed with mobile Linux environments in mind. Such as
[Phosh](https://developer.puri.sm/Librem5/Software_Reference/Environments/Phosh.html) and
[Plasma Mobile](https://www.plasma-mobile.org/). But it is completely usable as a normal
desktop application as well.

[![Screenshot](repo/alpha-screenshots.png)](repo/alpha-screenshots.png)

<a href="https://flathub.org/apps/details/com.doycho.euterpe.gtk"><img height="50" alt="Download on Flathub" src="https://flathub.org/assets/badges/flathub-badge-en.png"/></a>

## Project Status

The program is at the stage where it _could_ be used for your day-to-day Euterpe player.
But this comes with the huge disclaimer that there is quite a lot more to be done before
one could consider it "complete".

## Building From Source

You will need [libhandy 1.2+ dev files](https://gnome.pages.gitlab.gnome.org/libhandy/) and
the Python's [keyring](https://pypi.org/project/keyring/) lib before building.

On Alpine they could be installed via `apk`:

```
sudo apk add libhandy1-dev py3-keyring
```

After that install as normal GTK3 app:

```
meson . _build --prefix=/usr
ninja -C _build
sudo ninja -C _build install
```

## Development

One would want to set the environment variable `G_MESSAGES_DEBUG=euterpe-gtk` to get
the debug messages from the program. They do help during development a lot!
