from pathlib import Path

import archinstall
from archinstall import debug
from archinstall.lib.installer import Installer
from archinstall.lib.configuration import ConfigurationOutput
from archinstall.lib import disk
from archinstall.lib import locale
from archinstall.lib.models import Bootloader, User
import os
import shutil
import gpuvendorutil
from git import Repo
import subprocess

SCRIPTDIR = os.path.dirname(os.path.realpath(__file__))

packages = [
	'wget',
	'nano',
	'openssh',
	'wireless_tools',
	'wpa_supplicant',
	'smartmontools',
	'git',
	'networkmanager',
	'packagekit',
	'pacman-contrib',
	'firewalld',
	'python',
	'python-pip',
	'vim',
	'linux-firmware-qlogic',
	'linux-firmware-bnx2x',
	'linux-firmware-liquidio',
	'linux-firmware-mellanox',
	'linux-firmware-nfp',
	'mimalloc',
	'nasm',
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
	'nerd-fonts',
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
	'sddm',
	'lzop',
	'xorg-xinit',
	'zsh',
	'earlyoom',
	'go',
	'util-linux',
	'cairo',
	'fribidi',
	'gtk4',
	'hicolor-icon-theme',
	'icu',
	'json-glib',
	'libadwaita',
	'libportal',
	'libportal-gtk4',
	'pango',
	'pcre4',
	'vte-common',
	'meson',
	'lha',
	'tpm2-tools',
	'plymouth',
	'xvkbd'
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

nvidia_newer_drivers = [
	'nvidia-open-dkms',
	'nvidia-open',
	'dkms',
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

aur_list = [
    'aic94xx-firmware',
    'ast-firmware',
    'wd719x-firmware',
    'upd72020x-fw',
    'ptyxis',
    'zramd',
	'qlipper'
]


def ask_user_questions():
	global_menu = archinstall.GlobalMenu(data_store=archinstall.arguments)

	global_menu.enable('archinstall-language', mandatory=True)
	global_menu.enable('timezone', mandatory=True)
	global_menu.enable('mirror_config', mandatory=True)
	global_menu.enable('disk_config', mandatory=True)
	global_menu.enable('disk_encryption')
	global_menu.enable('hostname', mandatory=True)
	global_menu.enable('!root-password', mandatory=True)
	global_menu.enable('!users', mandatory=True)
	global_menu.enable('__separator__')

	global_menu.enable('install')
	global_menu.enable('abort')

	global_menu.run()

def perform_installation(mountpoint: Path):
	"""
	Performs the installation steps on a block device.
	Only requirement is that the block devices are
	formatted and setup prior to entering this function.
	"""
	disk_config: disk.DiskLayoutConfiguration = archinstall.arguments['disk_config']
	disk_encryption: disk.DiskEncryption = archinstall.arguments.get('disk_encryption', None)
	locale_config: locale.LocaleConfiguration = archinstall.arguments['locale_config']

	with Installer(
		mountpoint,
		disk_config,
		disk_encryption=disk_encryption,
		kernels=['linux-zen']
	) as installation:
		installation.mount_ordered_layout()
		installation.sanity_check()
		installation.add_bootloader(Bootloader.Limine)
		installation.minimal_installation(
				multilib=True,
				hostname=archinstall.arguments.get('hostname', 'archlinux'),
				locale_config=locale_config
		)
		# to generate a fstab directory holder. Avoids an error on exit and at the same time checks the procedure
		target = Path(f"{mountpoint}/etc/fstab")
		if not target.parent.exists():
			target.parent.mkdir(parents=True)
		if mirror_config := archinstall.arguments.get('mirror_config', None):
			installation.set_mirrors(mirror_config)
		installation.activate_time_synchronization()

		gpu_vendor = gpuvendorutil.get_gpu_vendor()
		if gpu_vendor == "amd":
			installation.add_additional_packages(amd_drivers)
		if gpu_vendor == "intel":
			installation.add_additional_packages(intel_drivers)
		if gpu_vendor == "nvidia_beforeturing":
			installation.add_additional_packages(nvidia_drivers)
		if gpu_vendor == "nvidia_turingplus":
			installation.add_additional_packages(nvidia_newer_drivers)
		if gpu_vendor == "vmware":
			installation.add_additional_packages(vmware_drivers)
				
		installation.add_additional_packages(packages)

		if timezone := archinstall.arguments.get('timezone', None):
			installation.set_timezone(timezone)
		if archinstall.accessibility_tools_in_use():
			installation.enable_espeakup()

		if (root_pw := archinstall.arguments.get('!root-password', None)) and len(root_pw):
			installation.user_set_pw('root', root_pw)
			
		os.mkdir("/mnt/archinstall/etc/polaris_installer")
		os.mkdir("/mnt/archinstall/etc/polaris_installer/pkg")
		for pkg in aur_list:
			Repo.clone_from(f"https://aur.archlinux.org/{pkg}.git", f"/mnt/archinstall/etc/polaris_installer/pkg/{pkg}")
			installation.run_command(f"cd /etc/polaris_installer/pkg/{pkg}/makepkg -si --noconfirm")
		
		# i feel like such an idiot knowing this needed only one function to fix it. ughhhhh
		os.mkdir("/mnt/archinstall/etc/dconf/db/local.d")
		shutil.copy(f"{SCRIPTDIR}/00_defaults", "/mnt/archinstall/etc/dconf/db/local.d/00_defaults")
		with open("/mnt/archinstall/etc/dconf/profile/user", "w+") as f:
			f.write("""user-db:user
system-db:local""")
			installation.run_command("chown -R root:root /etc/dconf/db")
			installation.run_command("chmod -R 755 /etc/dconf/db")
			installation.run_command("dconf update")

		installation.enable_service("sddm")
		installation.enable_service("NetworkManager")
		installation.enable_service("bluetooth")
		installation.genfstab()

ask_user_questions()

fs_handler = disk.FilesystemHandler(
	archinstall.arguments['disk_config'],
	archinstall.arguments.get('disk_encryption', None)
)

fs_handler.perform_filesystem_operations()

perform_installation(archinstall.storage.get('MOUNT_POINT', Path('/mnt')))