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

"""Control `snap`/`snapd` in HPC machine charms."""

__all__ = [
    "SnapConfigManager",
    "SnapLifecycleManager",
    "SnapOpsManager",
    "SnapServiceManager",
    "snap",
]

import json
from collections.abc import Mapping
from functools import cached_property
from subprocess import CalledProcessError
from typing import Any

import yaml

from ...errors import SnapError
from ..core import OpsManager, ServiceManager, call


def snap(*args: str, **kwargs: Any) -> tuple[str, int]:  # noqa D417
    """Control snaps using `snap ...` commands.

    Keyword Args:
        stdin: Standard input to pipe to the `snap` command.
        check:
            If set to `True`, raise an error if the `snap` command
            exits with a non-zero exit code.

    Raises:
        SnapError: Raised if a `snap` command fails and check is set to `True`.
    """
    try:
        result = call("snap", *args, **kwargs)
    except CalledProcessError as e:
        raise SnapError(
            f"snap command '{' '.join(e.cmd)}' failed with exit code {e.returncode}. "
            + f"reason: {e.stderr}"
        )

    return result.stdout, result.returncode


class SnapConfigManager:
    """Control the configuration of a snap package."""

    def __init__(self, snap: str) -> None:
        self._snap = snap

    def get(self, key: str) -> Any:
        """Get snap configuration.

        Args:
            key: Snap configuration key to get the value of.

        Examples:
            >>> package = SnapConfigManager("slurm")
            >>> package.get("exporter.port")
            >>> 9100
        """
        result = snap("get", "-d", self._snap, key)
        try:
            data = json.loads(result[0])
        except json.JSONDecodeError as e:
            raise SnapError(
                f"Failed to decode value of configuration option '{key}' for snap '{self._snap}'"
            ) from e

        return data[key]

    def set(self, config: Mapping[str, Any]) -> None:
        """Set snap configuration.

        Args:
            config: Snap configuration to set.

        Notes:
            - Keys can use dot notation.
        """
        snap("set", self._snap, *[f"{k}={json.dumps(v)}" for k, v in config.items()])

    def unset(self, *keys: str) -> None:
        """Unset snap configuration.

        Args:
            keys: Snap configuration keys to unset.
        """
        snap("unset", self._snap, *keys)


class SnapServiceManager(ServiceManager):
    """Control a service using `snap`.

    Args:
        service: Name of the service to control using `snap`
        snap: Name of the installed snap package that the service belongs.

    Notes:
        - Snap services names are typically represented as `<snap>.<service>` where `snap` is
          the name of the installed snap package, and `service` is the name of the service
          provided by the installed snap package. However, if the service name is the same as
          the installed package name, then the snap service name will be represented as just
          `service`. Because of this behavior, `snap` is an optional argument.
    """

    def __init__(self, service: str, /, snap: str | None = None) -> None:
        self._snap = snap if snap else service
        self._service = f"{snap}.{service}" if snap else service

    def start(self) -> None:
        """Start service."""
        snap("start", self._service)

    def stop(self) -> None:
        """Stop service."""
        snap("stop", self._service)

    def enable(self) -> None:
        """Enable service."""
        snap("start", "--enable", self._service)

    def disable(self) -> None:
        """Disable service."""
        snap("stop", "--disable", self._service)

    def restart(self) -> None:
        """Restart service."""
        snap("restart", self._service)

    def reload(self) -> None:
        """Reload service."""
        snap("restart", "--reload", self._service)

    def is_active(self) -> bool:
        """Check if service is active."""
        info = yaml.safe_load(snap("info", self._snap)[0])
        services = info.get("services")
        if services is None:
            raise SnapError(
                f"cannot retrieve '{self._service}' service info with 'snap info {self._snap}'"
            )

        # Do not check for "active" in the service's state because the
        # word "active" is also part of "inactive".
        return "inactive" not in services[self._service]


class SnapOpsManager(OpsManager):
    """Control the operations of a `snap` package."""

    def __init__(self, snap: str) -> None:
        self._snap = snap

    def service_manager_for(self, service: str) -> SnapServiceManager:
        """Create a service manager for the given service name.

        Args:
            service: Name of the service to create a `SnapServiceManager` for.
        """
        return SnapServiceManager(service, snap=self._snap if service != self._snap else None)

    def install(self) -> None:
        """Install package."""
        snap("install", self._snap)

    def remove(self, *, purge: bool = False) -> None:
        """Remove package.

        Args:
            purge: Remove the package without saving a snapshot of its data. Default: False.
        """
        command = ["remove", self._snap]
        if purge:
            command.append("--purge")

        snap(*command)

    def connect(self, plug: str, *, service: str | None = None, slot: str | None = None) -> None:
        """Connect a plug to a slot.

        Args:
            plug: The plug to connect.
            service: The snap service name to plug into.
            slot: The snap service slot to plug in to.
        """
        command = ["connect", f"{self._snap}:{plug}"]
        if service and slot:
            command.append(f"{service}:{slot}")
        elif service:
            command.append(service)
        elif slot:
            command.append(f":{slot}")

        snap(*command)


class SnapLifecycleManager:
    """Manage the full lifecycle operations of a snapped application."""

    def __init__(self, snap: str, /) -> None:
        self._snap = snap
        self._ops_manager = SnapOpsManager(snap)

        self.install = self._ops_manager.install
        self.remove = self._ops_manager.remove
        self.connect = self._ops_manager.connect

    @cached_property
    def config(self) -> SnapConfigManager:
        """Manage the snap configuration."""
        return SnapConfigManager(self._snap)
