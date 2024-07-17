from typing import Any, TYPE_CHECKING, List, Optional, Dict

from archinstall.lib.output import info
from archinstall.lib.profile.profiles_handler import profile_handler
from archinstall.default_profiles.profile import Profile, ProfileType, SelectResult, GreeterType

if TYPE_CHECKING:
	from archinstall.lib.installer import Installer
	_: Any

class BaseProfile(Profile):
	def __init__(self):
		super().__init__(
			'Core',
			ProfileType.Minimal
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
            'g++'
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
			
from typing import Any, TYPE_CHECKING, List, Optional, Dict

from archinstall.lib.output import info
from archinstall.lib.profile.profiles_handler import profile_handler
from archinstall.default_profiles.profile import Profile, ProfileType, SelectResult, GreeterType

if TYPE_CHECKING:
	from archinstall.lib.installer import Installer
	_: Any

class ServerProfile(Profile):
	def __init__(self):
		super().__init__(
			'Server',
			ProfileType.Minimal
		)

	@property
	def packages(self) -> List[str]:
		return [
			'packagekit',
            'cockpit',
            'udisks2'
		]