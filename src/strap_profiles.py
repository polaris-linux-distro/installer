from typing import Any, TYPE_CHECKING, List, Optional, Dict

from archinstall.lib.output import info
from archinstall.lib.profile.profiles_handler import profile_handler
from archinstall.default_profiles.profile import Profile, ProfileType, SelectResult, GreeterType

if TYPE_CHECKING:
	from archinstall.lib.installer import Installer
	_: Any

core_aur_list = [
    'aic94xx-firmware',
    'ast-firmware',
    'wd719x-firmware',
    'upd72020x-fw'
]


core_desktop_aur_list = [
    "ptyxis"
]

class BaseProfile(Profile):
	def __init__(self):
		super().__init__(
			'Core',
			ProfileType.Minimal,
            support_greeter=True,
            support_gfx_driver=True
		)

	@property
	def packages(self) -> List[str]:
		return [
			'wget',
            'nano',
            'openssh',
            'wireless_tools',
            'wpa_supplicant',
            'smartmontools',
            'git',
            'curl',
            'networkmanager',
            'packagekit',
            'pacman-contrib',
            'firewalld',
            'gcc',
            'python',
            'python-pip',
            'vim',
            'linux-firmware-qlogic',
            'linux-firmware-bnx2x',
            'linux-firmware-liquidio',
            'linux-firmware-mellanox',
            'linux-firmware-nfp',
            'tcmalloc',
            'mimalloc',
            'make',
            'nasm',
            'g++',
            'xorg-server',
            'xdg-utils',
            'htop',
            'pipewire',
            'pipewire-alsa',
            'pipewire-jack',
            'pipewire-pulse',
            'gst-plugin-pipewire',
            'libpulse',
            'wireplumber',
            'flatpak',
            'papirus-icon-theme',
            'gnu-free-fonts',
            'noto-fonts',
            'vlc',
            'thunderbird',
            'vala',
            'noto-color-emoji',
            'nerd-fonts',
            'noto-sans',
            'firefox',
            'touchegg',
            'imagemagick',
            'bluez',
            'gparted',
            'wayland-protocols',
            'icoutils'
		]

	def post_install(self, install_session: 'Installer'):
		for profile in self._current_selection:
			profile.post_install(install_session)

	def install(self, install_session: 'Installer'):
		# Install common packages for all desktop environments
		install_session.add_additional_packages(self.packages)

		for profile in self._current_selection:
			info(f'Installing profile {profile.name}...')

			install_session.add_additional_packages(profile.packages)
			install_session.enable_service(profile.services)

			profile.install(install_session)
	
class BudgieProfile(BaseProfile):
    def __init__(self):
        super().__init__(
			'BudgieDesktop',
			ProfileType.Minimal,
			support_greeter=True
		)

    @property
    def packages(self) -> List[str]:
        return [
            'materia-gtk-theme',
            'budgie',
            'nemo',
            'feh',
            'network-manager-applet',
            'mousepad'
        ]
	
class GnomeProfile(BaseProfile):
    def __init__(self):
        super().__init__(
			'GnomeDesktop',
			ProfileType.Minimal,
			support_greeter=True
		)

    @property
    def packages(self) -> List[str]:
        return [
            'gnome',
            'gnome-tweaks',
            'gnome-keyring'
        ]
	
class KDEProfile(BaseProfile):
    def __init__(self):
        super().__init__(
			'KDEDesktop',
			ProfileType.Minimal,
			support_greeter=True
		)

    @property
    def packages(self) -> List[str]:
        return [
            'plasma-meta',
			'kwrite',
			'dolphin',
			'ark',
			'plasma-workspace',
			'egl-wayland',
            'dolphin-plugins',
            'ffmpegthumbs',
            'kde-inotify-survey',
            'kdeconnect-kde',
            'kdegraphics-thumbnailers',
            'kdenetwork-filesharing',
            'kimageformats',
            'kio-admin',
            'kio-extras',
            'kio-fuse',
            'kio-gdrive',
            'libappindicator-gtk3',
            'phonon-vlc',
            'qt-imageformats',
            'xwaylandvideobridge',
            'power-profiles-daemon',
            'maliit-keyboard',
            'orca',
            'xsettingsd',
            'switcheroo-control',
            'iio-sensor-proxy'
        ]