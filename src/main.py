from pathlib import Path
from typing import TYPE_CHECKING, Any

import archinstall
from archinstall.lib.installer import Installer
from archinstall.lib import disk
from archinstall.lib import locale
from archinstall.lib.models import Bootloader
from archinstall.lib import menu
import os
import shutil
import gpuvendorutil
import subprocess
import zipfile

SCRIPTDIR = os.path.dirname(os.path.realpath(__file__))
if TYPE_CHECKING:
	_: Any

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
	'dhcpcd',
	'materia-gtk-theme',
	'budgie',
	'nemo',
	'feh',
	'network-manager-applet',
	'mousepad',
	'lzop',
	'xorg',
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
	'vte-common',
	'meson',
	'lha',
	'tpm2-tools',
	'plymouth',
	'libnm',
	'fastfetch',
	'wireless-regdb',
	'galculator',
	'xaw3d',
	'libxp',
	'gnome-console',
	'file-roller',
	'ed',
	'qt6-5compat',
	'qt5-declarative',
	'sddm',
	'gspell'
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

type_arg = str()

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
				locale_config=locale_config,
				mkinitcpio=False
		)
		# to generate a fstab directory holder. Avoids an error on exit and at the same time checks the procedure
		target = Path(f"{mountpoint}/etc/fstab")
		if not target.parent.exists():
			target.parent.mkdir(parents=True)
		if mirror_config := archinstall.arguments.get('mirror_config', None):
			installation.set_mirrors(mirror_config)
		installation.activate_time_synchronization()
		installation.setup_swap("zram")

		# this aur is so chaotic omg
		print("Installing Chaotic AUR")
		installation.run_command("pacman-key --init")
		installation.run_command("pacman-key --recv-key 3056513887B78AEB")
		installation.run_command("pacman-key --lsign-key 3056513887B78AEB")
		installation.run_command("pacman -U 'https://cdn-mirror.chaotic.cx/chaotic-aur/chaotic-keyring.pkg.tar.zst' --noconfirm")
		installation.run_command("pacman -U 'https://cdn-mirror.chaotic.cx/chaotic-aur/chaotic-mirrorlist.pkg.tar.zst' --noconfirm")
		
		with open("/mnt/archinstall/etc/pacman.conf", 'r') as file:
			lines = file.readlines()
		repo_entry = "\n[polaris]\nServer = https://polaris-linux-distro.github.io/pacman-repo/repo\nSigLevel = Optional TrustAll\n"
		repo_entry2 = "\n[chaotic-aur]\nInclude = /etc/pacman.d/chaotic-mirrorlist\n"
		lines.append(repo_entry)
		lines.append(repo_entry2)
		with open("/mnt/archinstall/etc/pacman.conf", 'w') as file:
			file.writelines(lines)

		installation.run_command("pacman -Syyu zsh --noconfirm")
		installation.run_command("pacman -Sy polo aic94xx-firmware ast-firmware wd719x-firmware upd72020x-fw xvkbd --noconfirm")
		gpu_vendor = gpuvendorutil.get_gpu_vendor()
		if gpu_vendor == "amd":
			installation.add_additional_packages(amd_drivers)
		elif gpu_vendor == "intel":
			installation.add_additional_packages(intel_drivers)
		elif gpu_vendor == "nvidia_beforeturing":
			installation.add_additional_packages(nvidia_drivers)
		elif gpu_vendor == "nvidia_turingplus":
			installation.add_additional_packages(nvidia_newer_drivers)
		elif gpu_vendor == "vmware":
			installation.add_additional_packages(vmware_drivers)
		
		installation.add_additional_packages(packages)
		shutil.copy(f"{SCRIPTDIR}/useradd", "/mnt/archinstall/etc/default/useradd")

		if timezone := archinstall.arguments.get('timezone', None):
			installation.set_timezone(timezone)
		if archinstall.accessibility_tools_in_use():
			installation.enable_espeakup()
		installation.activate_time_synchronization()

		if (root_pw := archinstall.arguments.get('!root-password', None)) and len(root_pw):
			installation.user_set_pw('root', root_pw)
		if users := archinstall.arguments.get('!users', None):
			installation.create_users(users)

		# i feel like such an idiot knowing this needed only one function to fix it. ughhhhh
		os.mkdir("/mnt/archinstall/etc/dconf/db/local.d")
		shutil.copy(f"{SCRIPTDIR}/00_defaults", "/mnt/archinstall/etc/dconf/db/local.d/00_defaults")
		with open("/mnt/archinstall/etc/dconf/profile/user", "w+") as f:
			f.write("""user-db:user
system-db:local""")
			
		with open("/mnt/archinstall/etc/sudoers", 'r') as file:
			lines = file.readlines()
		entry = "\n%wheel ALL=(ALL:ALL) ALL"
		lines.append(entry)
		with open("/mnt/archinstall/etc/sudoers", 'w') as file:
			file.writelines(lines)

		# Download the zip file
		url = 'https://gitlab.com/api/v4/projects/37107648/packages/generic/sddm-eucalyptus-drop/2.0.0/sddm-eucalyptus-drop-v2.0.0.zip'
		subprocess.run(['wget', url])

		# Unzip the file
		with zipfile.ZipFile('sddm-eucalyptus-drop-v2.0.0.zip', 'r') as zip_ref:
			zip_ref.extractall('/mnt/archinstall/usr/share/sddm/themes')

		# Remove the zip file
		os.remove('sddm-eucalyptus-drop-v2.0.0.zip')
		shutil.copy(f"{SCRIPTDIR}/sddm.conf", "/mnt/archinstall/etc/sddm.conf")
		shutil.copy(f"{SCRIPTDIR}/mkinitcpio.conf", "/mnt/archinstall/etc/mkinitcpio.conf")
		shutil.copy(f"{SCRIPTDIR}/os-release", "/mnt/archinstall/etc/os-release")
		
		installation.run_command("chown -R root:root /etc/dconf/db")
		installation.run_command("chmod -R 755 /etc/dconf/db")
		installation.run_command("dconf update")
		installation.run_command("plymouth-set-default-theme polaris")

		installation.enable_service("sddm")
		installation.enable_service("touchegg")
		installation.enable_service("NetworkManager")
		installation.enable_service("bluetooth")
		installation.genfstab()
		installation.run_command("mkinitcpio -P")

ask_user_questions()

fs_handler = disk.FilesystemHandler(
	archinstall.arguments['disk_config'],
	archinstall.arguments.get('disk_encryption', None)
)

fs_handler.perform_filesystem_operations()

perform_installation(archinstall.storage.get('MOUNT_POINT', Path('/mnt')))