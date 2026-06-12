# Arch/Manjaro Package

This folder contains the Arch/Manjaro packaging files for Manjaro Toolbox.

## Build And Install

From this folder:

```bash
makepkg -si
```

This installs:

- `/opt/manjaro-toolbox` app files
- `/usr/bin/manjaro-toolbox` launcher command
- `/usr/share/applications/manjaro-toolbox.desktop` menu entry
- `/usr/share/icons/hicolor/scalable/apps/manjaro-toolbox.svg` icon

## Run

```bash
manjaro-toolbox
```

Or open **Manjaro Toolbox** from the application menu.

## Stop Server

```bash
manjaro-toolbox --stop
```

## Uninstall

```bash
sudo pacman -Rns manjaro-toolbox
```

## Notes

The package depends on Python, sudo, xdg-utils and pacman. `yay` is optional and only needed for AUR package actions.
