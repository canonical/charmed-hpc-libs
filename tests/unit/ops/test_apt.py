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

"""Unit tests for the `apt` machine library."""

import subprocess
from unittest.mock import Mock, call

import pytest
from pytest_mock import MockerFixture

from charmed_hpc_libs.errors import AptError
from charmed_hpc_libs.ops import AptOpsManager, apt, dpkg_query


def test_apt(mocker: MockerFixture) -> None:
    """Test the `apt` function."""
    mock_run = mocker.patch.object(subprocess, "run")
    mock_run.side_effect = subprocess.CalledProcessError(
        cmd=["apt-get", "install", "-y", "slurm"],
        returncode=1,
        output="",
        stderr="failed to install slurm",
    )

    stdout, exit_code = apt("install", "-y", "slurm", check=False)
    assert stdout is None
    assert exit_code == 1

    with pytest.raises(AptError) as exec_info:
        apt("install", "-y", "slurm", check=True)

    assert exec_info.type == AptError
    assert exec_info.value.message == (
        "apt-get command 'apt-get install -y slurm' failed with exit code 1. "
        + "reason: failed to install slurm"
    )


def test_dpkg_query(mocker: MockerFixture) -> None:
    """Test the `dpkg_query` function."""
    mock_run = mocker.patch.object(subprocess, "run")
    mock_run.return_value = subprocess.CompletedProcess(
        args=["dpkg-query", "-W", "slurm"],
        returncode=0,
        stdout="23.11.7",
    )

    stdout, exit_code = dpkg_query("-W", "slurm")
    assert stdout == "23.11.7"
    assert exit_code == 0

    mock_run.side_effect = subprocess.CalledProcessError(
        cmd=["dpkg-query", "-W", "slurm"],
        returncode=1,
        output="",
        stderr="package slurm is not installed",
    )

    with pytest.raises(AptError) as exec_info:
        dpkg_query("-W", "slurm")

    assert exec_info.type == AptError
    assert exec_info.value.message == (
        "dpkg-query command 'dpkg-query -W slurm' failed with exit code 1. "
        + "reason: package slurm is not installed"
    )


@pytest.fixture
def mock_apt(mocker: MockerFixture) -> Mock:
    """Create a mocked `apt` function."""
    return mocker.patch("charmed_hpc_libs.ops.machine.apt.apt")


@pytest.fixture
def mock_dpkg_query(mocker: MockerFixture) -> Mock:
    """Create a mocked `dpkg_query` function."""
    return mocker.patch("charmed_hpc_libs.ops.machine.apt.dpkg_query")


class TestAptOpsManager:
    """Test the `AptOpsManager` class."""

    @pytest.fixture
    def ops_manager(self) -> AptOpsManager:
        """Create an `AptOpsManager` object."""
        return AptOpsManager("slurm")

    @pytest.fixture
    def ops_manager_with_extras(self) -> AptOpsManager:
        """Create an `AptOpsManager` object with additional packages."""
        return AptOpsManager("slurmctld", additional_packages=["slurm-client", "libpmix-dev"])

    def test_install_with_update(self, ops_manager, mock_apt) -> None:
        """Test the `install` method with cache update."""
        ops_manager.install()
        mock_apt.assert_has_calls([call("update"), call("install", "-y", "slurm")])

    def test_install_without_update(self, ops_manager, mock_apt) -> None:
        """Test the `install` method without cache update."""
        ops_manager.install(update=False)
        mock_apt.assert_called_with("install", "-y", "slurm")

    def test_install_with_additional_packages(self, ops_manager_with_extras, mock_apt) -> None:
        """Test the `install` method with additional packages."""
        ops_manager_with_extras.install(update=False)
        mock_apt.assert_called_with("install", "-y", "slurmctld", "slurm-client", "libpmix-dev")

    def test_remove(self, ops_manager, mock_apt) -> None:
        """Test the `remove` method."""
        ops_manager.remove()
        mock_apt.assert_called_with("remove", "-y", "slurm")

    def test_remove_with_purge(self, ops_manager, mock_apt) -> None:
        """Test the `remove` method with purge."""
        ops_manager.remove(purge=True)
        mock_apt.assert_called_with("remove", "-y", "slurm", "--purge")

    def test_remove_with_additional_packages(self, ops_manager_with_extras, mock_apt) -> None:
        """Test the `remove` method with additional packages."""
        ops_manager_with_extras.remove()
        mock_apt.assert_called_with("remove", "-y", "slurmctld", "slurm-client", "libpmix-dev")

    @pytest.mark.parametrize(
        "mock_return,expected",
        (
            pytest.param(("", 0), True, id="installed"),
            pytest.param(("", 1), False, id="not installed"),
        ),
    )
    def test_is_installed(self, ops_manager, mock_dpkg_query, mock_return, expected) -> None:
        """Test the `is_installed` method."""
        mock_dpkg_query.return_value = mock_return
        assert ops_manager.is_installed() is expected
        mock_dpkg_query.assert_called_with("-W", "slurm", check=False)

    @pytest.mark.parametrize(
        "mock_result,expected",
        (
            pytest.param(("23.11.7", 0), "23.11.7", id="installed"),
            pytest.param(("", 1), None, id="not installed"),
        ),
    )
    def test_version(self, ops_manager, mock_dpkg_query, mock_result, expected) -> None:
        """Test the `version` method."""
        mock_dpkg_query.return_value = mock_result
        if expected is not None:
            assert ops_manager.version() == expected
            mock_dpkg_query.assert_called_with(
                "-W", "-f=${source:Upstream-Version}", "slurm", check=False
            )
        else:
            with pytest.raises(AptError) as exec_info:
                ops_manager.version()
            assert exec_info.value.message == (
                "unable to retrieve slurm version. ensure slurm is correctly installed"
            )

    def test_update(self, ops_manager, mock_apt) -> None:
        """Test the `update` method."""
        ops_manager.update()
        mock_apt.assert_called_with("update")
