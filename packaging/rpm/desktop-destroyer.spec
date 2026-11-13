Name:           desktop-destroyer
Version:        1.0.0
Release:        1%{?dist}
Summary:        Smash, burn and saw your desktop to pieces
License:        MIT
URL:            https://github.com/TechnikWeber/linux-desktop-destroyer
Source0:        %{url}/archive/v%{version}/%{name}-%{version}.tar.gz
BuildArch:      noarch

BuildRequires:  python3-devel
BuildRequires:  desktop-file-utils
Requires:       python3-pyside6
# screenshot on KDE Plasma / wlroots; the XDG portal covers the rest
Suggests:       spectacle
Suggests:       grim

%description
The 90s Desktop Destroyer classic for Linux: hammer, chain-saw, machine gun,
flame-thrower, colour-thrower, phaser, stamp, termites and washing gun, let
loose on a still of your real desktop. Your windows and files are never
touched. Works on X11 and Wayland.

%prep
%autosetup -n %{name}-%{version}

%build
# pure Python, nothing to build

%install
install -d %{buildroot}%{python3_sitelib}/desktop_destroyer
install -m644 desktop_destroyer/*.py %{buildroot}%{python3_sitelib}/desktop_destroyer/
install -Dm755 /dev/stdin %{buildroot}%{_bindir}/desktop-destroyer <<'SH'
#!/usr/bin/python3 -s
from desktop_destroyer.app import main
raise SystemExit(main())
SH
desktop-file-install --dir=%{buildroot}%{_datadir}/applications share/desktop-destroyer.desktop
install -Dm644 share/desktop-destroyer.png %{buildroot}%{_datadir}/icons/hicolor/256x256/apps/desktop-destroyer.png
for size in 128 64 48; do
    install -Dm644 share/desktop-destroyer-$size.png \
        %{buildroot}%{_datadir}/icons/hicolor/${size}x${size}/apps/desktop-destroyer.png
done
install -Dm644 share/io.github.technikweber.desktop-destroyer.metainfo.xml \
    %{buildroot}%{_metainfodir}/io.github.technikweber.desktop-destroyer.metainfo.xml

%files
%license LICENSE
%doc README.md CHANGELOG.md
%{_bindir}/desktop-destroyer
%{python3_sitelib}/desktop_destroyer/
%{_datadir}/applications/desktop-destroyer.desktop
%{_datadir}/icons/hicolor/*/apps/desktop-destroyer.png
%{_metainfodir}/io.github.technikweber.desktop-destroyer.metainfo.xml

%changelog
* Fri Nov 13 2026 Philipp Weber - 1.0.0-1
- First release: AppImage and RPM
