# Copyright 2026 Canonical Ltd.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Control ``apt-get`` and ``dpkg-query`` in HPC machine charms."""

__all__ = [
    "AptLifecycleManager",
    "AptOpsManager",
    "apt",
    "dpkg_query",
]

import os
from collections.abc import Iterable
from subprocess import CalledProcessError
from typing import Any

from ...errors import AptError
from ..core import OpsManager, call
from .systemd import SystemctlServiceManager


def apt(*args: str, **kwargs: Any) -> tuple[str, int]:  # noqa D417
    """Control Debian/Ubuntu packages using ``apt-get ...`` commands.

    Keyword Args:
        stdin: Standard input to pipe to the ``apt-get`` command.
        check:
            If set to `True`, raise an error if the ``apt-get`` command
            exits with a non-zero exit code.

    Raises:
        AptError: Raised if an ``apt-get`` command fails and check is set to ``True``.
    """
    env = {**os.environ, "DEBIAN_FRONTEND": "noninteractive"}
    try:
        result = call("apt-get", *args, env=env, **kwargs)
    except CalledProcessError as e:
        raise AptError(
            f"apt-get command '{' '.join(e.cmd)}' failed with exit code {e.returncode}. "
            + f"reason: {e.stderr}"
        )

    return result.stdout, result.returncode


def dpkg_query(*args: str, **kwargs: Any) -> tuple[str, int]:  # noqa D417
    """Query ``dpkg`` for package information using ``dpkg-query ...`` commands.

    Keyword Args:
        stdin: Standard input to pipe to the ``dpkg-query`` command.
        check:
            If set to `True`, raise an error if the ``dpkg-query`` command
            exits with a non-zero exit code.

    Raises:
        AptError: Raised if a ``dpkg-query`` command fails and check is set to ``True``.
    """
    try:
        result = call("dpkg-query", *args, **kwargs)
    except CalledProcessError as e:
        raise AptError(
            f"dpkg-query command '{' '.join(e.cmd)}' failed with exit code {e.returncode}. "
            + f"reason: {e.stderr}"
        )

    return result.stdout, result.returncode


class AptOpsManager(OpsManager):
    """Control the operations of an ``apt`` package."""

    def __init__(self, package: str, *, additional_packages: Iterable[str] | None = None) -> None:
        self._package = package
        self._additional_packages = list(additional_packages) if additional_packages else []

    def service_manager_for(self, service: str) -> SystemctlServiceManager:  # noqa D102
        """Create a service manager for the provided service name.

        Args:
            service: Name of the service to create a ``SystemctlServiceManager`` for.
        """
        return SystemctlServiceManager(service)

    def update(self) -> None:
        """Update the ``apt`` package cache."""
        apt("update")

    def install(self, *, update: bool = True) -> None:
        """Install packages.

        Args:
            update:
                If ``True``, update the ``apt`` cache by running ``apt-get update``
                before installing packages.
        """
        if update:
            self.update()

        apt("install", "-y", self._package, *self._additional_packages)

    def remove(self, *, purge: bool = False) -> None:
        """Remove packages.

        Args:
            purge:
                If ``True``, removed packages are also purged (configuration files are also deleted).
        """
        command = ["remove", "-y", self._package]
        if self._additional_packages:
            command.extend(self._additional_packages)
        if purge:
            command.append("--purge")

        apt(*command)

    def is_installed(self) -> bool:
        """Check if the ``apt`` package is installed."""
        _, exit_code = dpkg_query("-W", self._package, check=False)
        return exit_code == 0

    def version(self) -> str:
        """Get the version of primary ``apt`` package."""
        result, exit_code = dpkg_query(
            "-W", "-f=${source:Upstream-Version}", self._package, check=False
        )
        if exit_code != 0:
            raise AptError(
                f"unable to retrieve {self._package} version. "
                f"ensure {self._package} is correctly installed"
            )

        return result


class AptLifecycleManager:
    """Manage the full lifecycle operations of an ``apt`` package."""

    def __init__(
        self, package: str, /, *, additional_packages: Iterable[str] | None = None
    ) -> None:
        self._ops_manager = AptOpsManager(package, additional_packages=additional_packages)

        self.update = self._ops_manager.update
        self.install = self._ops_manager.install
        self.remove = self._ops_manager.remove
        self.is_installed = self._ops_manager.is_installed
        self.version = self._ops_manager.version
