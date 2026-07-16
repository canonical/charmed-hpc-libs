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

"""Unit tests for the `Interface` base class."""

import json
from dataclasses import dataclass
from unittest.mock import MagicMock, PropertyMock

import ops
import pytest
from ops import Framework, testing

from charmed_hpc_libs.interfaces import Interface

INTEGRATION_NAME = "test-integration"
INTERFACE_NAME = "test-interface"


def make_integration(
    id: int = 1,
    remote_app_data: dict | None = None,
    remote_units_data: dict | None = None,
) -> testing.Relation:
    return testing.Relation(
        endpoint=INTEGRATION_NAME,
        interface=INTERFACE_NAME,
        id=id,
        remote_app_name="remote-app",
        remote_app_data=remote_app_data or {},
        remote_units_data=remote_units_data or {},
    )


class ExampleInterface(Interface):
    """Thin subclass exposing protected methods for testing."""

    def __init__(self, charm: ops.CharmBase, /, integration_name: str) -> None:
        super().__init__(
            charm,
            integration_name,
            required_app_data=["api-endpoint"],
            app_data_validator=lambda x: x["api-endpoint"].startswith("https://"),
        )

    def load(self, cls, **kwargs):
        return self._load_integration_data(cls, **kwargs)

    def save(self, data, target, **kwargs) -> None:
        self._save_integration_data(data, target, **kwargs)


class _Interface(Interface):
    """Thin subclass exposing protected methods for testing."""

    def load(self, cls, **kwargs):
        return self._load_integration_data(cls, **kwargs)

    def save(self, data, target, **kwargs) -> None:
        self._save_integration_data(data, target, **kwargs)


@dataclass
class ExampleData:
    """Sample data manipulated by the mock charms."""

    name: str = ""
    value: str = ""


class MockCharm(ops.CharmBase):
    """Mock charm for testing the `Interface` base class."""

    def __init__(self, framework: Framework) -> None:
        super().__init__(framework)

        self.interface = ExampleInterface(self, INTEGRATION_NAME)


@pytest.fixture(scope="function")
def mock_charm() -> testing.Context[MockCharm]:
    """Mock charm context for testing the `Interface` base class."""
    return testing.Context(
        MockCharm,
        meta={
            "name": "test-interface-charm",
            "requires": {INTEGRATION_NAME: {"interface": INTERFACE_NAME}},
        },
    )


@pytest.fixture(
    params=(
        pytest.param(True, id="active integration"),
        pytest.param(False, id="no active integration"),
    ),
)
def integration_exists(request) -> bool:
    return request.param


@pytest.fixture(
    params=(
        pytest.param(True, id="with integration ID"),
        pytest.param(False, id="without integration ID"),
    ),
)
def with_id(request) -> bool:
    return request.param


class TestInterface:
    """Test the ``Interface`` base class."""

    def test_integrations(self, mock_charm, integration_exists) -> None:
        """Test the ``integrations`` property."""
        with mock_charm(
            mock_charm.on.update_status(),
            state=testing.State(relations={make_integration()} if integration_exists else {}),
        ) as manager:
            manager.run()

        assert len(manager.charm.interface.integrations) == (1 if integration_exists else 0)

    def test_get_integration(self, mock_charm, integration_exists) -> None:
        """Test the ``get_integration`` method."""
        with mock_charm(
            mock_charm.on.update_status(),
            state=testing.State(relations={make_integration(id=1)} if integration_exists else {}),
        ) as manager:
            manager.run()

        if integration_exists:
            assert manager.charm.interface.get_integration().id == 1
        else:
            with pytest.raises(ops.RelationNotFoundError):
                manager.charm.interface.get_integration()

    def test_is_joined(self, mock_charm, integration_exists) -> None:
        """Test the ``is_joined`` method."""
        with mock_charm(
            mock_charm.on.update_status(),
            state=testing.State(relations={make_integration()} if integration_exists else {}),
        ) as manager:
            manager.run()

        assert manager.charm.interface.is_joined() == integration_exists

    @pytest.mark.parametrize(
        "data_is_available,expected",
        (
            pytest.param({"api-endpoint": "https://127.0.0.1:8000"}, True, id="data is ready"),
            pytest.param({"api-endpoint": "ftp://127.0.0.1:8000"}, False, id="data is invalid"),
            pytest.param({}, False, id="data is not ready"),
        ),
    )
    def test_is_ready(
        self, mock_charm, integration_exists, data_is_available, with_id, expected
    ) -> None:
        """Test the ``is_ready`` method."""
        with mock_charm(
            mock_charm.on.update_status(),
            state=testing.State(
                relations={make_integration(remote_app_data=data_is_available)}
                if integration_exists
                else {}
            ),
        ) as manager:
            manager.run()

        assert manager.charm.interface.is_ready(integration_id=1 if with_id else None) is (
            expected if integration_exists else False
        )

    @pytest.mark.parametrize(
        "target",
        (
            pytest.param("app", id="target app"),
            pytest.param("unit", id="target unit"),
        ),
    )
    def test_load_integration_data(self, mock_charm, with_id, target) -> None:
        """Test loading application data with the ``_load_integration_data`` method."""
        with mock_charm(
            mock_charm.on.update_status(),
            state=testing.State(
                relations={
                    make_integration(
                        id=1,
                        remote_app_data={"name": json.dumps("foo"), "value": json.dumps("bar")},
                        remote_units_data={
                            0: {"name": json.dumps("foo"), "value": json.dumps("bar")}
                        },
                    )
                }
            ),
        ) as manager:
            manager.run()

        data = manager.charm.interface.load(
            ExampleData, integration_id=1 if with_id else None, target=target
        )
        assert len(data) == 1
        assert data[0].name == "foo"
        assert data[0].value == "bar"

    def test_load_integration_data_invalid_target(self, mock_charm) -> None:
        """Test that ``_load_integration_data`` raises an error when given an invalid target."""
        with mock_charm(
            mock_charm.on.update_status(),
            state=testing.State(relations={make_integration()}),
        ) as manager:
            manager.run()

        with pytest.raises(ValueError):
            manager.charm.interface.load(ExampleData, target="model")

    def test_save_data(self, mock_charm, with_id) -> None:
        """Test the `_save_integration_data` method."""
        with mock_charm(
            mock_charm.on.update_status(),
            state=testing.State(leader=True, relations={make_integration(id=1)}),
        ) as manager:
            manager.charm.interface.save(
                ExampleData(name="foo", value="bar"),
                target=manager.charm.app,
                integration_id=1 if with_id else None,
            )
            state = manager.run()

        integration = state.get_relation(1)
        assert integration.local_app_data == {"name": '"foo"', "value": '"bar"'}

    def test_save_merge_preserves_unmodified_fields(self, mock_charm, with_id) -> None:
        """Test that ``merge=True`` only overwrites fields that differ from their defaults."""
        with mock_charm(
            mock_charm.on.update_status(),
            state=testing.State(leader=True, relations={make_integration(id=1)}),
        ) as manager:
            manager.charm.interface.save(
                ExampleData(name="foo", value="bar"),
                target=manager.charm.app,
            )
            manager.charm.interface.save(
                ExampleData(name="baz"),
                target=manager.charm.app,
                integration_id=1 if with_id else None,
                merge=True,
            )
            state = manager.run()

        integration = state.get_relation(1)
        assert integration.local_app_data == {"name": '"baz"', "value": '"bar"'}

    def test_save_merge_into_empty_databag(self, mock_charm) -> None:
        """Test that merging into an empty databag preserves unset fields at their defaults."""
        with mock_charm(
            mock_charm.on.update_status(),
            state=testing.State(leader=True, relations={make_integration(id=1)}),
        ) as manager:
            manager.charm.interface.save(
                ExampleData(name="foo"),
                target=manager.charm.app,
                merge=True,
            )
            state = manager.run()

        integration = state.get_relation(1)
        assert integration.local_app_data == {"name": '"foo"', "value": '""'}

    def test_save_merge_requires_dataclass(self, mock_charm) -> None:
        """Test that ``TypeError`` is raised if ``data`` isn't a dataclass and ``merge=True``."""
        with mock_charm(
            mock_charm.on.update_status(),
            state=testing.State(leader=True, relations={make_integration(id=1)}),
        ) as manager:
            with pytest.raises(TypeError):
                manager.charm.interface.save(
                    "not-a-dataclass",
                    target=manager.charm.app,
                    merge=True,
                )
            manager.run()

    def test_save_not_merge_overwrites_all_fields(self, mock_charm) -> None:
        """merge=False (default) overwrites all fields even those set to defaults."""
        with mock_charm(
            mock_charm.on.update_status(),
            state=testing.State(leader=True, relations={make_integration(id=1)}),
        ) as manager:
            manager.charm.interface.save(
                ExampleData(name="foo", value="bar"),
                target=manager.charm.app,
            )
            manager.charm.interface.save(
                ExampleData(name="baz"),
                target=manager.charm.app,
            )
            state = manager.run()

        integration = state.get_relation(1)
        assert integration.local_app_data == {"name": '"baz"', "value": '""'}

    def test_is_integration_active(self, mock_charm, integration_exists) -> None:
        """Test the `_is_integration_active` static method."""
        if integration_exists:
            integration = MagicMock(spec=ops.Relation)
            integration.data = {"some": "data"}
        else:
            integration = MagicMock(spec=ops.Relation)
            type(integration).data = PropertyMock(side_effect=RuntimeError("broken"))

        assert Interface._is_integration_active(integration) == integration_exists
