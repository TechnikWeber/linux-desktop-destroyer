# Desktop Destroyer

<p>
  <img alt="Status: stable" src="https://img.shields.io/badge/status-stable-brightgreen">
  <img alt="Platform: Linux · X11 | Wayland" src="https://img.shields.io/badge/platform-Linux%20%C2%B7%20X11%20%7C%20Wayland-blue">
  <a href="LICENSE"><img alt="License: MIT" src="https://img.shields.io/badge/license-MIT-green"></a>
</p>

The 90s classic, now for Linux. Hammer, chain-saw, machine gun, flame-thrower,
colour-thrower, phaser, stamp, termites and washing gun, let loose on your real
desktop.

![Desktop Destroyer](docs/screenshot.png)

## How it works

On launch a still of your desktop is captured and shown back pixel-for-pixel as a
fullscreen window. What you tear apart is that image — your windows, your files and
your session are never touched. `Esc` quits, `R` repairs everything.

That is exactly why it behaves identically on **X11 and Wayland**: nothing is drawn
into other applications' windows and nothing is smuggled past the compositor.

Linux has no `.exe` — the click-to-start equivalent is a `.desktop` entry in the
application menu, and `./install.sh` creates it.

## Getting started

```bash
git clone https://github.com/TechnikWeber/linux-desktop-destroyer.git
cd linux-desktop-destroyer
./install.sh
```

Then look for **Desktop Destroyer** in your application menu and click it. From a
terminal, `desktop-destroyer` works from anywhere.

`install.sh` adds exactly three things: a menu entry, an icon and a command in
`~/.local/bin`. `./uninstall.sh` takes them away again. If PySide6 (Qt 6) is
missing, the script offers to build a local `.venv` — your distribution's package
is the tidier option:

| Distribution  | Package                            |
|---------------|------------------------------------|
| Fedora / RHEL | `sudo dnf install python3-pyside6` |
| Debian/Ubuntu | `sudo apt install python3-pyside6` |
| Arch          | `sudo pacman -S pyside6`           |

## Controls

| Key                    | Effect                                          |
|------------------------|-------------------------------------------------|
| `1` … `9`              | Pick a weapon                                   |
| Left mouse button      | Strike; hold for continuous fire                |
| Mouse wheel            | Next / previous weapon                          |
| `Tab` or right click   | Show or hide the toolbox                        |
| `R`                    | Repair the whole desktop                        |
| `S`                    | Save the wreckage as a PNG (`~/Pictures`)       |
| `M`                    | Sound on / off                                  |
| `Esc` or `Q`           | Quit                                            |

Drag the toolbox around by its title bar.

## The nine tools

| # | Tool           | What it does                                                       |
|---|----------------|--------------------------------------------------------------------|
| 1 | Hammer         | One dent per click: a crater with branching fractures, screen shakes |
| 2 | Chain-saw      | Dragging cuts one continuous ragged kerf; sawdust flies             |
| 3 | Machine gun    | Continuous fire with spread, bullet holes, muzzle flash and casings |
| 4 | Flame-thrower  | Chars the surface black, paint blisters, smoke drifts up            |
| 5 | Colour-thrower | Splatter in shifting colours, with paint running down               |
| 6 | Phaser         | Burns a glowing slit clean across the screen                        |
| 7 | Stamp          | Presses "DESTROYED", "VOID", "REJECTED" … on, askew and grainy      |
| 8 | Termites       | Releases termites that crawl about and chew tunnels                 |
| 9 | Washing gun    | The undo tool: washes the desktop clean again                       |

## Command line

```
desktop-destroyer [options]

  -w, --windowed       run in a normal window instead of fullscreen (handy for testing)
  -i, --image FILE     destroy an image file instead of the live desktop
  -m, --mute           start muted
  -d, --delay SECONDS  wait before grabbing the desktop
      --primary-only   only take over the primary screen
      --backend        print the detected screenshot backend and exit
```

## Screenshot backends

The still is grabbed with the first method that works on the system:

* **X11** — Qt grabs the root windows directly; otherwise `maim`, `scrot`, `import`
* **Wayland** — `grim` (wlroots: Sway, Hyprland, river, Wayfire), `spectacle` (KDE),
  `org.gnome.Shell.Screenshot`, `gnome-screenshot`
* **anywhere** — `org.freedesktop.portal.Screenshot` as the last resort
  (some compositors ask once before allowing it)

`desktop-destroyer --backend` shows which one was picked. If none of them work the
game still starts — with a painted stand-in desktop.

## Why no image or audio files?

There are none. Every tool icon is vector art in `icons.py`, and all the sounds are
synthesised on first launch in `sfx.py` and cached under `~/.cache/desktop-destroyer/`.
A `git clone` is all it takes.

## License

[MIT](LICENSE).
