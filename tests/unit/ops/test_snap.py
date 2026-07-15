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

"""Unit tests for the `snap` machine library."""

import subprocess
from unittest.mock import Mock

import pytest
from pytest_mock import MockerFixture

from charmed_hpc_libs.errors import SnapError
from charmed_hpc_libs.ops import (
    SnapConfigManager,
    SnapOpsManager,
    SnapServiceManager,
    snap,
)

# This input is modified. If the service name is the same as the snap name, then the
# service will be started as `snap start slurm` rather than `snap start slurm.slurm`.
# See https://snapcraft.io/prometheus for an example.
SNAP_INFO = """
name:      slurm
summary:   "Slurm: A Highly Scalable Workload Manager"
publisher: –
store-url: https://snapcraft.io/slurm
license:   Apache-2.0
description: |
    Slurm is an open source, fault-tolerant, and highly scalable cluster
    management and job scheduling system for large and small Linux clusters.
commands:
    - slurm.command1
    - slurm.command2
services:
    slurmctld:                       simple, disabled, inactive
    slurm.logrotate:                 oneshot, enabled, inactive
    slurm.slurm-prometheus-exporter: simple, disabled, inactive
    slurm.slurmctld:                 simple, disabled, active
    slurm.slurmd:                    simple, enabled, active
    slurm.slurmdbd:                  simple, disabled, active
    slurm.slurmrestd:                simple, disabled, active
channels:
    latest/stable:    –
    latest/candidate: 23.11.7 2024-06-26 (460) 114MB classic
    latest/beta:      ↑
    latest/edge:      23.11.7 2024-06-26 (459) 114MB classic
installed:          23.11.7             (x1) 114MB classic
"""

SNAP_INFO_NOT_INSTALLED = """
name:      slurm
summary:   "Slurm: A Highly Scalable Workload Manager"
publisher: –
store-url: https://snapcraft.io/slurm
license:   Apache-2.0
description: |
    Slurm is an open source, fault-tolerant, and highly scalable cluster
    management and job scheduling system for large and small Linux clusters.
channels:
    latest/stable:    –
    latest/candidate: 23.11.7 2024-06-26 (460) 114MB classic
    latest/beta:      ↑
    latest/edge:      23.11.7 2024-06-26 (459) 114MB classic
"""


@pytest.fixture(scope="function")
def mock_snap(mocker: MockerFixture) -> Mock:
    """Create a mocked `snap` function."""
    return mocker.patch("charmed_hpc_libs.ops.machine.snap.snap")


def test_snap(mocker: MockerFixture) -> None:
    """Test the `snap` function."""
    mock_run = mocker.patch.object(subprocess, "run")
    mock_run.side_effect = subprocess.CalledProcessError(
        cmd=["snap", "start", "slurm.slurmctld"],
        returncode=1,
        output="",
        stderr="failed to start slurmctld service",
    )

    # Test `snap` function with check set to `False`.
    stdout, exit_code = snap("start", "slurm.slurmctld", check=False)
    assert stdout is None
    assert exit_code == 1

    # Test `snap` function with check set to `True`.
    with pytest.raises(SnapError) as exec_info:
        snap("start", "slurm.slurmctld", check=True)

    assert exec_info.type == SnapError
    assert exec_info.value.message == (
        "snap command 'snap start slurm.slurmctld' failed with exit code 1. "
        + "reason: failed to start slurmctld service"
    )


class TestSnapConfigManager:
    """Test the `SnapConfigManager` class."""

    @pytest.fixture
    def config_manager(self) -> SnapConfigManager:
        """Create a `SnapConfigManager` object."""
        return SnapConfigManager("slurm")

    def test_get(self, config_manager, mock_snap) -> None:
        """Test the `get` method."""
        mock_snap.return_value = ('{"exporter.port": 9100}', 0)
        assert config_manager.get("exporter.port") == 9100
        mock_snap.assert_called_with("get", "-d", "slurm", "exporter.port")

        mock_snap.return_value = ('{"key": "value"}', 0)
        assert config_manager.get("key") == "value"

        mock_snap.return_value = ("not valid json", 0)
        with pytest.raises(SnapError) as exec_info:
            config_manager.get("exporter.port")
        assert exec_info.value.message == (
            "Failed to decode value of configuration option 'exporter.port' for snap 'slurm'"
        )

        mock_snap.side_effect = SnapError("snap command failed")
        with pytest.raises(SnapError):
            config_manager.get("exporter.port")

    def test_set(self, config_manager, mock_snap) -> None:
        """Test the `set` method."""
        config_manager.set({"port": "8817"})
        mock_snap.assert_called_with("set", "slurm", 'port="8817"')

    def test_unset(self, config_manager, mock_snap) -> None:
        """Test the `unset` method."""
        config_manager.unset("port")
        mock_snap.assert_called_with("unset", "slurm", "port")


class TestSnapOpsManager:
    """Test the `SnapOpsManager` class."""

    @pytest.fixture
    def ops_manager(self) -> SnapOpsManager:
        """Create a `SnapOpsManager` object."""
        return SnapOpsManager("slurm")

    def test_install(self, ops_manager, mock_snap) -> None:
        """Test the `install` method."""
        ops_manager.install()
        mock_snap.assert_called_with("install", "slurm")

    def test_remove(self, ops_manager, mock_snap) -> None:
        """Test the `remove` method."""
        ops_manager.remove()
        mock_snap.assert_called_with("remove", "slurm")

        ops_manager.remove(purge=True)
        mock_snap.assert_called_with("remove", "slurm", "--purge")

    def test_connect(self, ops_manager, mock_snap) -> None:
        """Test the `connect` method."""
        ops_manager.connect("network-observe")
        mock_snap.assert_called_with("connect", "slurm:network-observe")

        ops_manager.connect("network-observe", service="snapd", slot="network-observe")
        mock_snap.assert_called_with("connect", "slurm:network-observe", "snapd:network-observe")

        ops_manager.connect("network-observe", slot="system")
        mock_snap.assert_called_with("connect", "slurm:network-observe", ":system")

        ops_manager.connect("network-observe", service="snapd")
        mock_snap.assert_called_with("connect", "slurm:network-observe", "snapd")

    @pytest.mark.parametrize(
        "mock_return,expected",
        (
            pytest.param(("", 0), True, id="installed"),
            pytest.param(("", 1), False, id="not installed"),
        ),
    )
    def test_is_installed(self, ops_manager, mock_snap, mock_return, expected) -> None:
        """Test the `is_installed` method."""
        mock_snap.return_value = mock_return
        assert ops_manager.is_installed() is expected
        mock_snap.assert_called_with("list", "slurm", check=False)


@pytest.mark.parametrize(
    "service_name_is_snap_name",
    (
        pytest.param(True, id="service name = snap name"),
        pytest.param(False, id="service name != snap name"),
    ),
)
class TestSnapServiceManager:
    """Test the `SnapServiceManager` class."""

    @pytest.fixture
    def service_manager(self, service_name_is_snap_name) -> SnapServiceManager:
        """Create a `SnapServiceManager` object."""
        return SnapServiceManager(
            "slurmctld", snap="slurm" if not service_name_is_snap_name else None
        )

    def test_start(self, service_manager, mock_snap, service_name_is_snap_name) -> None:
        """Test the `start` method."""
        service_manager.start()
        if service_name_is_snap_name:
            mock_snap.assert_called_with("start", "slurmctld")
        else:
            mock_snap.assert_called_with("start", "slurm.slurmctld")

    def test_stop(self, service_manager, mock_snap, service_name_is_snap_name) -> None:
        """Test the `stop` method."""
        service_manager.stop()
        if service_name_is_snap_name:
            mock_snap.assert_called_with("stop", "slurmctld")
        else:
            mock_snap.assert_called_with("stop", "slurm.slurmctld")

    def test_enable(self, service_manager, mock_snap, service_name_is_snap_name) -> None:
        """Test the `enable` method."""
        service_manager.enable()
        if service_name_is_snap_name:
            mock_snap.assert_called_with("start", "--enable", "slurmctld")
        else:
            mock_snap.assert_called_with("start", "--enable", "slurm.slurmctld")

    def test_disable(self, service_manager, mock_snap, service_name_is_snap_name) -> None:
        """Test the `disable` method."""
        service_manager.disable()
        if service_name_is_snap_name:
            mock_snap.assert_called_with("stop", "--disable", "slurmctld")
        else:
            mock_snap.assert_called_with("stop", "--disable", "slurm.slurmctld")

    def test_restart(self, service_manager, mock_snap, service_name_is_snap_name) -> None:
        """Test the `restart` method."""
        service_manager.restart()
        if service_name_is_snap_name:
            mock_snap.assert_called_with("restart", "slurmctld")
        else:
            mock_snap.assert_called_with("restart", "slurm.slurmctld")

    def test_reload(self, service_manager, mock_snap, service_name_is_snap_name) -> None:
        """Test the `reload` method."""
        service_manager.reload()
        if service_name_is_snap_name:
            mock_snap.assert_called_with("restart", "--reload", "slurmctld")
        else:
            mock_snap.assert_called_with("restart", "--reload", "slurm.slurmctld")

    @pytest.mark.parametrize(
        "mock_result,installed",
        (
            pytest.param((SNAP_INFO, 0), True, id="installed"),
            pytest.param((SNAP_INFO_NOT_INSTALLED, 1), False, id="not installed"),
        ),
    )
    def test_is_active(
        self,
        service_manager,
        mock_snap,
        mock_result,
        installed,
        service_name_is_snap_name,
    ) -> None:
        """Test the `active` method."""
        mock_snap.return_value = mock_result
        if installed:
            status = service_manager.is_active()
            if service_name_is_snap_name:
                mock_snap.assert_called_with("info", "slurmctld")
                assert status is False
            else:
                mock_snap.assert_called_with("info", "slurm")
                assert status is True
        else:
            with pytest.raises(SnapError) as exec_info:
                service_manager.is_active()

            assert exec_info.type == SnapError
            if service_name_is_snap_name:
                assert exec_info.value.message == (
                    "cannot retrieve 'slurmctld' service info with 'snap info slurmctld'"
                )
            else:
                assert exec_info.value.message == (
                    "cannot retrieve 'slurm.slurmctld' service info with 'snap info slurm'"
                )
