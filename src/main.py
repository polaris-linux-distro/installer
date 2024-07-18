from pathlib import Path
from typing import TYPE_CHECKING, Any, List

import json

import archinstall
from archinstall import info
from archinstall import Installer, ConfigurationOutput
from archinstall.default_profiles.minimal import MinimalProfile
from archinstall.lib.interactions import suggest_single_disk_layout, select_devices
from archinstall.lib.models import Bootloader, User
from archinstall.lib.profile import ProfileConfiguration, profile_handler
from archinstall.lib import disk

if TYPE_CHECKING:
	_: Any


info("Minimal only supports:")
info(" * Being installed to a single disk")

if archinstall.arguments.get('help', None):
	info("polo-strap <Root partition> <EFI partition/BIOSBoot> <Swap partition>")

def perform_installation(mountpoint: Path):
	config = json.loads(open("/tmp/polostrap.conf", "r"))

	disk_config: disk.DiskLayoutConfiguration = archinstall.arguments['disk_config']
	disk_encryption = disk.DiskEncryption(encryption_type=disk.EncryptionType.Luks, encryption_password=config["enc_password"], partitions=partitions)

	with Installer(
		mountpoint,
		disk_config,
		disk_encryption=disk_encryption,
		kernels=archinstall.arguments.get('kernels', ['linux-zen'])
	) as installation:
		# Strap in the base system, add a boot loader and configure
		# some other minor details as specified by this profile and user.
		if installation.minimal_installation():
			installation.set_hostname('minimal-arch')
			installation.add_bootloader(Bootloader.Limine)

			installation.copy_iso_network_config(enable_services=True)
			installation.add_additional_packages(['nano', 'wget', 'git'])
			
			profile_config = ProfileConfiguration(MinimalProfile())
			profile_handler.install_profile_config(installation, profile_config)
			users = list()
            for user in config["user"]:
                user
            installation.create_users(user)

	# Once this is done, we output some useful information to the user
	# And the installation is complete.
	info("- Installation completed. You may reboot now.")
	info("- Chroot into it for extra configuration by running: ")
	info("arch-chroot /mnt")
	
config_output = ConfigurationOutput(archinstall.arguments)
config_output.show()

perform_installation(archinstall.storage.get('MOUNT_POINT', Path('/mnt')))