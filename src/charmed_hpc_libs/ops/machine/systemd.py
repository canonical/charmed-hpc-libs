# Copyright 2025-2026 Canonical Ltd.
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

"""Control `systemd`/`systemctl` in HPC machine charms."""

__all__ = ["SystemctlServiceManager", "systemctl", "is_container"]

import shutil
from subprocess import CalledProcessError
from typing import Any

from ...errors import SystemdError, UnknownVirtualizationStateError
from ..core import ServiceManager, call


def is_container() -> bool:
    """Use `systemd` to detect if the machine is a container instance.

    Raises:
        UnknownVirtualizationStateError: Raised if `systemd-detect-virt` is not found on machine.
    """
    if shutil.which("systemd-detect-virt") is None:
        raise UnknownVirtualizationStateError(
            (
                "executable `systemd-detect-virt` not found. "
                + "cannot determine if machine is a container instance"
            )
        )

    result = call("systemd-detect-virt", "--container", check=False)
    return result.returncode == 0


def systemctl(*args: str, **kwargs: Any) -> tuple[str, int]:  # noqa D417
    """Control systemd units using `systemctl ...` commands.

    Keyword Args:
        stdin: Standard input to pipe to the `systemctl` command.
        check:
            If set to `True`, raise an error if the `systemctl` command
            exits with a non-zero exit code.

    Raises:
        SystemdError: Raised if a `systemctl` command fails and check is set to `True`.
    """
    try:
        result = call("systemctl", *args, **kwargs)
    except CalledProcessError as e:
        raise SystemdError(
            f"systemctl command '{' '.join(e.cmd)}' failed with exit code {e.returncode}. "
            + f"reason: {e.stderr}"
        )

    return result.stdout, result.returncode


class SystemctlServiceManager(ServiceManager):
    """Control a service using `systemctl`."""

    def __init__(self, service: str, /) -> None:
        self._service = service

    def start(self) -> None:
        """Start service."""
        systemctl("start", self._service)

    def stop(self) -> None:
        """Stop service."""
        systemctl("stop", self._service)

    def enable(self) -> None:
        """Enable service."""
        systemctl("enable", self._service)

    def disable(self) -> None:
        """Disable service."""
        systemctl("disable", self._service)

    def restart(self) -> None:
        """Restart service."""
        systemctl("restart", self._service)

    def reload(self) -> None:
        """Reload service."""
        systemctl("reload", self._service)

    def is_active(self) -> bool:
        """Check if service is active."""
        _, exit_code = systemctl("is-active", "--quiet", self._service, check=False)
        return exit_code == 0
