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
    'upd72020x-fw',
    'ptyxis',
    'zramd'
]

amd_drivers = [
    'vulkan-radeon',
	'xf86-video-ati',
	'mesa'
	'libva-mesa-driver',
	'xf86-video-amdgpu'
]

nvidia_drivers = [
    'dkms',
    'nvidia-dkms',
	'nvidia-utils'
]

intel_drivers = [
    'mesa',
	'intel-media-driver',
	'libva-intel-driver',
	'vulkan-intel'
]

vmware_drivers = [
	'xf86-video-vmware',
	'mesa',
	'open-vm-tools'
]


class BaseProfile(Profile):
	def __init__(self):
		super().__init__(
			'Polaris',
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
            'icoutils',
            'dosfstools',
            'jfsutils',
            'f2fs-tools',
            'btrfs-progs',
            'exfatprogs',
            'ntfs-3g',
            'reiserfsprogs',
            'udftools',
            'xfsprogs',
            'nilfs-utils',
            'polkit',
            'gpart',
            'mtools',
            'xorg-xhost',
            'dhcpcd',
			'materia-gtk-theme',
            'budgie',
            'nemo',
            'feh',
            'network-manager-applet',
            'mousepad',
			'limine'
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
	
