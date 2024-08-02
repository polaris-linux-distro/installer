from pathlib import Path
from typing import Any, Optional, TYPE_CHECKING, Dict
import archinstall
from archinstall.lib.installer import Installer
from archinstall.lib import disk, exceptions
from archinstall.lib.disk import disk_menu
from archinstall.lib.output import log, error, info, warn, debug
from archinstall.lib import locale
from archinstall.lib.models import Bootloader
from archinstall.lib.hardware import SysInfo
from archinstall.lib.general import SysCommand
from archinstall.lib.menu import (
	Selector
)
from archinstall.lib.interactions import select_disk_config
import os
import shutil
import gpuvendorutil
import subprocess
import zipfile

SCRIPTDIR = os.path.dirname(os.path.realpath(__file__))
if TYPE_CHECKING:
	_: Any

class InstallerHack(Installer):
	def _add_limine_bootloader(
		self,
		boot_partition: disk.PartitionModification,
		efi_partition: Optional[disk.PartitionModification],
		root: disk.PartitionModification | disk.LvmVolume
	):
		debug('Installing limine bootloader')

		self.pacman.strap('limine')

		info(f"Limine boot partition: {boot_partition.dev_path}")

		limine_path = self.target / 'usr' / 'share' / 'limine'
		hook_command = None

		if SysInfo.has_uefi():
			if not efi_partition:
				raise ValueError('Could not detect efi partition')
			elif not efi_partition.mountpoint:
				raise ValueError('EFI partition is not mounted')

			info(f"Limine EFI partition: {efi_partition.dev_path}")

			try:
				efi_dir_path = self.target / efi_partition.mountpoint.relative_to('/') / 'EFI' / 'BOOT'
				efi_dir_path.mkdir(parents=True, exist_ok=True)

				for file in ('BOOTIA32.EFI', 'BOOTX64.EFI'):
					shutil.copy(limine_path / file, efi_dir_path)
			except Exception as err:
				raise exceptions.DiskError(f'Failed to install Limine in {self.target}{efi_partition.mountpoint}: {err}')

			hook_command = f'/usr/bin/cp /usr/share/limine/BOOTIA32.EFI {efi_partition.mountpoint}/EFI/BOOT/' \
				f' && /usr/bin/cp /usr/share/limine/BOOTX64.EFI {efi_partition.mountpoint}/EFI/BOOT/'
		else:
			parent_dev_path = disk.device_handler.get_parent_device_path(boot_partition.safe_dev_path)

			if unique_path := disk.device_handler.get_unique_path_for_device(parent_dev_path):
				parent_dev_path = unique_path

			try:
				# The `limine-bios.sys` file contains stage 3 code.
				shutil.copy(limine_path / 'limine-bios.sys', self.target / 'boot')

				# `limine bios-install` deploys the stage 1 and 2 to the disk.
				SysCommand(f'/usr/bin/arch-chroot {self.target} limine bios-install {parent_dev_path}', peek_output=True)
			except Exception as err:
				raise exceptions.DiskError(f'Failed to install Limine on {parent_dev_path}: {err}')

			hook_command = f'/usr/bin/limine bios-install {parent_dev_path}' \
				f' && /usr/bin/cp /usr/share/limine/limine-bios.sys /boot/'

		hook_contents = f'''[Trigger]
Operation = Install
Operation = Upgrade
Type = Package
Target = limine

[Action]
Description = Deploying Limine after upgrade...
When = PostTransaction
Exec = /usr/bin/python /usr/share/polaris/polo-adm.py rebuild-boot
'''

		hooks_dir = self.target / 'etc' / 'pacman.d' / 'hooks'
		hooks_dir.mkdir(parents=True, exist_ok=True)

		etc = self.target / 'etc'

		limine_rebuild = etc / 'limine_upgrade_command'
		limine_rebuild.write_text(hook_command)

		hook_path = hooks_dir / '99-limine.hook'
		hook_path.write_text(hook_contents)

		kernel_params = ' '.join(self._get_kernel_params(root))
		config_contents = 'TIMEOUT=5\n'
		entry_normal = [
			f'PROTOCOL=linux',
			f'KERNEL_PATH=boot:///vmlinuz-linux-zen',
			f'MODULE_PATH=boot:///initramfs-linux-zen.img',
			f'CMDLINE={kernel_params} quiet splash',
		]
		entry_verbose = [
			f'PROTOCOL=linux',
			f'KERNEL_PATH=boot:///vmlinuz-linux-zen',
			f'MODULE_PATH=boot:///initramfs-linux-zen.img',
			f'CMDLINE={kernel_params} loglevel=7 debug earlyprintk=vga plymouth.enable=0 systemd.log_level=debug systemd.log_target=console',
		]
		entry_rescue = [
			f'PROTOCOL=linux',
			f'KERNEL_PATH=boot:///vmlinuz-linux-zen',
			f'MODULE_PATH=boot:///initramfs-linux-zen-fallback.img',
			f'CMDLINE={kernel_params} systemd.unit=emergency.target loglevel=7 debug nomodeset earlyprintk=vga single plymouth.enable=0 systemd.log_level=debug systemd.log_target=console',
		]

		config_contents += f'\n:Polaris Linux\n'
		config_contents += '\n'.join([f'    {it}' for it in entry_normal]) + '\n'
		config_contents += f'\n:Polaris Linux (Verbose mode)\n'
		config_contents += '\n'.join([f'    {it}' for it in entry_verbose]) + '\n'
		config_contents += f'\n:Polaris Linux (Emergency mode)\n'
		config_contents += '\n'.join([f'    {it}' for it in entry_rescue]) + '\n'

		config_path = self.target / 'boot' / 'limine.cfg'
		config_path.write_text(config_contents)

		self.helper_flags['bootloader'] = "limine"

class DiskMenuHack(disk_menu.DiskLayoutConfigurationMenu):
	def setup_selection_menu_options(self):
		self._menu_options['disk_config'] = \
			Selector(
				_('Partitioning'),
				lambda x: self._select_disk_layout_config(x),
				display_func=lambda x: self._display_disk_layout(x),
				preview_func=self._prev_disk_layouts,
				default=self._disk_layout_config,
				enabled=True
			)
	def _select_disk_layout_config(
		self,
		preset: Optional[disk_menu.DiskLayoutConfiguration]
	) -> Optional[disk_menu.DiskLayoutConfiguration]:
		disk_config = select_disk_config(preset, advanced_option=self._advanced)

		return disk_config

class GlobalMenuHack(archinstall.GlobalMenu):
	def _select_disk_config(
		self,
		preset: Optional[disk.DiskLayoutConfiguration] = None
	) -> Optional[disk.DiskLayoutConfiguration]:
		data_store: Dict[str, Any] = {}
		disk_config = DiskMenuHack(preset, data_store).run()

		if disk_config != preset:
			self._menu_options['disk_encryption'].set_current_selection(None)

		return disk_config

packages = [
	'timeshift',
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
	'budgie-control-center',
	'budgie-desktop',
	'budgie-screensaver',
	'budgie-session',
	'budgie-desktop-view',
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
	'gspell',
	'glxinfo',
	'libreoffice-fresh',
	'terminus-font'
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

def ask_user_questions():
	global_menu = GlobalMenuHack(data_store=archinstall.arguments)

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

	with InstallerHack(
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
		with open("/mnt/archinstall/etc/skel/.zshrc", 'w') as file:
			file.writelines("# hmm")

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

		with open("/mnt/archinstall/etc/zsh/zshrc", 'w') as file:
			file.writelines("""HISTFILE=~/.histfile
HISTSIZE=1000
SAVEHIST=1000
bindkey -e
zstyle :compinstall filename '$HOME/.zshrc'
autoload -Uz compinit
compinit
precmd() {print -rP '(%F{blue}%n%f @ %F{blue}%m%f - %F{blue}%~%f)'}
PROMPT='%F{green}>>%f '""")
			
		with open("/mnt/archinstall/etc/vconsole.conf", 'r') as file:
			lines = file.readlines()
		entry = "\nFONT=ter-v18b"
		lines.append(entry)
		with open("/mnt/archinstall/etc/vconsole.conf", 'w') as file:
			file.writelines(lines)

		url = 'https://gitlab.com/api/v4/projects/37107648/packages/generic/sddm-eucalyptus-drop/2.0.0/sddm-eucalyptus-drop-v2.0.0.zip'
		subprocess.run(['wget', url])
		with zipfile.ZipFile('sddm-eucalyptus-drop-v2.0.0.zip', 'r') as zip_ref:
			zip_ref.extractall('/mnt/archinstall/usr/share/sddm/themes')
		os.remove('sddm-eucalyptus-drop-v2.0.0.zip')
		# Wood fired pizza, hows pizza get a job now?
		os.mkdir("/mnt/archinstall/usr/share/gnome-background-properties")
		shutil.copy(f"{SCRIPTDIR}/sddm.conf", "/mnt/archinstall/etc/sddm.conf")
		shutil.copy(f"{SCRIPTDIR}/mkinitcpio.conf", "/mnt/archinstall/etc/mkinitcpio.conf")
		shutil.copy(f"{SCRIPTDIR}/os-release", "/mnt/archinstall/etc/os-release")
		shutil.copy(f"{SCRIPTDIR}/lsb-release", "/mnt/archinstall/etc/lsb-release")
		shutil.copy(f"{SCRIPTDIR}/polaris-backgrounds.xml", "/mnt/archinstall/usr/share/gnome-background-properties/polaris-backgrounds.xml")

		os.mkdir("/mnt/archinstall/usr/share/backgrounds/polaris")
		for item in os.listdir(f"{SCRIPTDIR}/backgrounds"):
			source_item = os.path.join(f"{SCRIPTDIR}/backgrounds", item)
			destination_item = os.path.join("/mnt/archinstall/usr/share/backgrounds/polaris", item)
			if os.path.isfile(source_item):
				shutil.copy(source_item, destination_item)
		
		installation.run_command("rm -rf /usr/share/backgrounds/budgie")
		
		installation.run_command("chown -R root:root /etc/dconf/db")
		installation.run_command("chmod -R 755 /etc/dconf/db")
		installation.run_command("dconf update")
		installation.run_command("plymouth-set-default-theme polaris")

		installation.enable_service("sddm")
		installation.enable_service("touchegg")
		installation.enable_service("NetworkManager")
		installation.enable_service("bluetooth")
		# FUCK OFF CRONIES
		installation.enable_service("cronie")
		# END FUCK OFF CRONIES
		installation.enable_service("firewalld")
		installation.enable_service("dhcpcd")
		installation.enable_service("systemd-vconsole-setup")
		installation.genfstab()
		installation.run_command("mkinitcpio -P")

ask_user_questions()

fs_handler = disk.FilesystemHandler(
	archinstall.arguments['disk_config'],
	archinstall.arguments.get('disk_encryption', None)
)

fs_handler.perform_filesystem_operations()

perform_installation(archinstall.storage.get('MOUNT_POINT', Path('/mnt')))