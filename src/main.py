from pathlib import Path

import archinstall
from archinstall import debug
from archinstall.lib.installer import Installer
from archinstall.lib.configuration import ConfigurationOutput
from archinstall.lib import models
from archinstall.lib import disk
from archinstall.lib import locale
from archinstall.lib.profile.profiles_handler import ProfileHandler

from archinstall.lib.models import Bootloader, User
from archinstall.default_profiles.profile import GreeterType

import strap_profiles

class ProfileHandlerFix(ProfileHandler):
	def install_profile_config(self, install_session: Installer, profile_config: archinstall.profile.ProfileConfiguration):
		profile = profile_config.profile
		profile.install(install_session)
		self.install_gfx_driver(install_session, profile_config.gfx_driver)
		self.install_greeter(install_session, profile_config.greeter)

profile_handler = ProfileHandlerFix()

def ask_user_questions():
    global_menu = archinstall.GlobalMenu(data_store=archinstall.arguments)

    global_menu.enable('archinstall-language')
    global_menu.enable('timezone')

    global_menu.enable('mirror_config')

    global_menu.enable('disk_config', mandatory=True)
    global_menu.enable('disk_encryption')

    global_menu.enable('hostname', mandatory=True)
    #global_menu.enable('root_password', mandatory=True)
    #global_menu.enable('users')

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
        kernels=archinstall.arguments.get('kernels', ['linux-zen'])
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
        installation.setup_swap('zram')
        installation.activate_time_synchronization()
        
        # Ensure we provide the install session to the profile configuration
        profile_config = archinstall.profile.ProfileConfiguration(strap_profiles.BaseProfile, greeter=GreeterType.Sddm)
        profile_handler.install_profile_config(installation, profile_config)
        if timezone := archinstall.arguments.get('timezone', None):
                installation.set_timezone(timezone)
        if archinstall.accessibility_tools_in_use():
            installation.enable_espeakup()

        if (root_pw := archinstall.arguments.get('!root-password', None)) and len(root_pw):
            installation.user_set_pw('root', root_pw)

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