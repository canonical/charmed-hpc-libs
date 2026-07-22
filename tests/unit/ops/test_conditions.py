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

"""Unit tests for the conditions pattern."""

import ops
import pytest
from ops import testing

from charmed_hpc_libs.ops import (
    ConditionEvaluation,
    StopCharm,
    block_unless,
    integration_exists,
    integration_not_exists,
    leader,
    refresh,
    wait_unless,
)


def service_is_active(_: ops.Object) -> ConditionEvaluation:
    return ConditionEvaluation(False, "Waiting for service to start")


def unit_is_leader(obj: ops.Object) -> ConditionEvaluation:
    is_leader = obj.model.unit.is_leader()
    return ConditionEvaluation(is_leader, "Unit is not leader" if not is_leader else "")


def post_handler_checks(charm: ops.CharmBase) -> ops.StatusBase:
    condition = integration_exists("database")(charm)
    if not condition.ok:
        return ops.BlockedStatus("Database integration is missing")

    condition = integration_not_exists("database-proxy")(charm)
    if not condition.ok:
        return ops.BlockedStatus("Database is connected. Proxy is unnecessary")

    condition = integration_not_exists("metrics-server")(charm)
    if condition.ok:
        return ops.BlockedStatus(condition.message)

    return ops.ActiveStatus()


class MockDatabaseObserver(ops.Object):
    """Mock ``integrations`` observer."""

    def __init__(self, charm: "MockCharm", integration_name: str) -> None:
        super().__init__(charm, f"{type(self).__name__}")

        self.charm = charm
        self.framework.observe(
            self.charm.on[integration_name].relation_created, self._on_database_relation_created
        )

    @refresh(hook=None)
    @wait_unless(service_is_active)
    def _on_database_relation_created(self, _: ops.RelationCreatedEvent) -> None: ...


class MockLifecycleObserver(ops.Object):
    """Mock ``operations`` observer."""

    def __init__(self, charm: "MockCharm") -> None:
        super().__init__(charm, f"{type(self).__name__}")
        self.charm = charm

        self.framework.observe(self.charm.on.install, self._on_install)
        self.framework.observe(self.charm.on.config_changed, self._on_config_changed)
        self.framework.observe(self.charm.on.update_status, self._on_update_status)

    @refresh(hook=None)
    @block_unless(unit_is_leader)
    def _on_install(self, _: ops.InstallEvent) -> None: ...

    @leader
    @block_unless(unit_is_leader)  # Ensure that `leader` is called before `block_unless`.
    def _on_config_changed(self, _: ops.ConfigChangedEvent) -> None:
        self.charm.unit.status = ops.MaintenanceStatus("Leader is updating settings")

    @refresh(hook=post_handler_checks)
    def _on_update_status(self, _: ops.UpdateStatusEvent) -> None: ...


class MockCharm(ops.CharmBase):
    """Mock charm for testing the conditions pattern."""

    def __init__(self, framework: ops.Framework) -> None:
        super().__init__(framework)

        self.lifecycle_observer = MockLifecycleObserver(self)
        self.database_observer = MockDatabaseObserver(self, "database")


@pytest.fixture(scope="function")
def mock_charm() -> testing.Context[MockCharm]:
    return testing.Context(
        MockCharm,
        meta={
            "name": "mock-conditions-charm",
            "requires": {
                "database": {"interface": "database"},
                "database-proxy": {"interface": "database-proxy"},
            },
        },
    )


@pytest.mark.parametrize("is_leader", (True, False))
def test_leader_condition(mock_charm, is_leader) -> None:
    """Test the `leader` condition."""
    state = mock_charm.run(mock_charm.on.config_changed(), state=testing.State(leader=is_leader))

    if is_leader:
        assert state.unit_status == ops.MaintenanceStatus("Leader is updating settings")
    else:
        assert state.unit_status == ops.UnknownStatus()


def test_block_unless_condition(mock_charm) -> None:
    """Test the `block_unless` condition."""
    state = mock_charm.run(mock_charm.on.install(), state=testing.State(leader=False))

    assert state.unit_status == ops.BlockedStatus("Unit is not leader")


def test_wait_unless_condition(mock_charm) -> None:
    """Test the `wait_unless` condition."""
    integration = testing.Relation(endpoint="database")

    state = mock_charm.run(
        mock_charm.on.relation_created(integration), state=testing.State(relations={integration})
    )

    assert state.unit_status == ops.WaitingStatus("Waiting for service to start")


def test_refresh(mock_charm) -> None:
    """Test the `refresh` decorator."""
    integration = testing.Relation(endpoint="database")

    state = mock_charm.run(
        mock_charm.on.update_status(), state=testing.State(relations={integration})
    )

    assert state.unit_status == ops.BlockedStatus("Waiting for integrations: [`metrics-server`]")


class MockAppStatusObserver(ops.Object):
    """Mock observer for testing that observers can set app statuses."""

    def __init__(self, charm: "MockAppStatusCharm") -> None:
        super().__init__(charm, f"{type(self).__name__}")

        self._charm = charm
        self.framework.observe(self._charm.on.install, self._on_install)
        self.framework.observe(self._charm.on.start, self._on_start)

    @refresh(hook=None)
    def _on_install(self, _: ops.InstallEvent) -> None:
        raise StopCharm(ops.BlockedStatus("blocked for app"), set_app_status=True)

    @refresh(hook=None)
    def _on_start(self, _: ops.StartEvent) -> None:
        raise StopCharm(ops.BlockedStatus("blocked for unit only"))


class MockAppStatusCharm(ops.CharmBase):
    """Mock charm for testing `StopCharm` app status propagation."""

    def __init__(self, framework: ops.Framework) -> None:
        super().__init__(framework)

        self.lifecycle_observer = MockAppStatusObserver(self)


@pytest.fixture(scope="function")
def app_status_charm() -> testing.Context[MockAppStatusCharm]:
    return testing.Context(MockAppStatusCharm, meta={"name": "app-status-charm"})


@pytest.mark.parametrize("is_leader", (True, False))
def test_refresh_app_status(app_status_charm, is_leader) -> None:
    """Test that `refresh` sets app status with `set_app_status=True` only when unit is leader."""
    state = app_status_charm.run(
        app_status_charm.on.install(), state=testing.State(leader=is_leader)
    )
    assert state.unit_status == ops.BlockedStatus("blocked for app")
    if is_leader:
        assert state.app_status == ops.BlockedStatus("blocked for app")
    else:
        assert state.app_status == ops.UnknownStatus()


def test_refresh_no_app_status_by_default(app_status_charm) -> None:
    """Test that `refresh` does not touch app status when `set_app_status` is `False` (default)."""
    state = app_status_charm.run(app_status_charm.on.start(), state=testing.State(leader=True))
    assert state.unit_status == ops.BlockedStatus("blocked for unit only")
    assert state.app_status == ops.UnknownStatus()
