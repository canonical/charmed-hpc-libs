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

"""Base interface for HPC integration interface implementations."""

__all__ = ["Interface"]

import dataclasses
from collections.abc import Callable, Iterable
from typing import Any, Literal

import ops


class Interface(ops.Object):
    """Base interface for HPC integration interfaces.

    Args:
        charm: Charm instance the integration belongs to.
        integration_name: Name of the integration.
        required_app_data: Required application data for the integration to be considered ready.
        app_data_validator: Function to validate application data if required keys are present.

    Notes:
        - This interface is not intended to be used directly. Child interfaces should inherit
          from this interface to provide common macros typically used within custom integration
          interface implementations.
        - An integration is considered "ready" once it is exporting the necessary data for
          a requirer/provider to successfully process a `RelationChangedEvent`.
    """

    # A workaround for: https://bugs.launchpad.net/juju/+bug/1979811
    #
    # `relation-broken` events do not have enough information to determine whether they have been
    # fired because the current unit is being removed, or because the integration itself is being
    # removed. In the case where only the current unit is being removed, relation data should not be
    # cleared nor secrets revoked.
    #
    # As a workaround, a StoredState flag is set in the `relation-departed` hook if the current unit
    # is being removed. The flag is then checked in the `relation-broken` event handler to determine
    # whether data should be cleared or not.
    #
    # StoredState is used rather than the unit databag to prevent extraneous `relation-changed`
    # events from firing as the unit is being removed.
    #
    # Inspired by:
    # https://github.com/canonical/postgresql-operator/blob/e13b871/src/relations/db.py#L193
    _stored = ops.StoredState()

    def __init__(
        self,
        charm: ops.CharmBase,
        /,
        integration_name: str,
        *,
        required_app_data: Iterable[str] | None = None,
        app_data_validator: Callable[[ops.RelationDataContent], bool] | None = None,
    ) -> None:
        super().__init__(charm, integration_name)
        self.charm = charm
        self.app = charm.app
        self.unit = charm.unit
        self._integration_name = integration_name
        self._required_app_data = required_app_data if required_app_data else set()
        self._app_data_validator = app_data_validator if app_data_validator else lambda _: True

        self._stored.set_default(unit_departing=False)
        self.framework.observe(
            self.charm.on[self._integration_name].relation_departed,
            self._on_relation_departed,
        )

    def _on_relation_departed(self, event: ops.RelationDepartedEvent) -> None:
        """Handle when a unit is departing from the relation."""
        if event.departing_unit == self.unit:
            self._stored.unit_departing = True

    @property
    def integrations(self) -> list[ops.Relation]:
        """Get list of integration instances associated with the configured integration name."""
        return [
            integration
            for integration in self.charm.model.relations[self._integration_name]
            if self._is_integration_active(integration)
        ]

    def get_integration(self, integration_id: int | None = None) -> ops.Relation:
        """Get integration instance.

        Args:
            integration_id:
                ID of integration instance to retrieve. Required if there are
                multiple integrations of the same name in Juju's database.
                For example, you must pass the integration ID if multiple
                `slurmd` partitions exist.

        Raises:
            ops.RelationNotFoundError:
                Raised if integration is not established. If `integration_id` is set,
                raised if integration instance is not established or found.
            ops.TooManyRelatedAppsError:
                Raised if `integration_id` is not passed as an argument,
                but multiple applications is are integrated on the same endpoint.
        """
        integration = self.charm.model.get_relation(self._integration_name, integration_id)
        if not integration:
            raise ops.RelationNotFoundError()

        return integration

    def is_ready(self, integration_id: int | None = None) -> bool:
        """Check if an integration is ready.

        Args:
            integration_id:
                Check if this specific integration instance is ready. If an
                integration ID is not provided, all existing integrations will
                be checked to determine if they are ready.

        Raises:
            ops.RelationNotFoundError: Raised if the provided integration ID does not exist.

        Notes:
            - This method can be used to check if a provider answered with the requested
              data outside an event callback.
            - An integration is "ready" once it is exporting the necessary data requested
              by a requirer to proceed.
        """
        if integration_id is None:
            return (
                all(self._is_integration_ready(integration) for integration in self.integrations)
                if self.integrations
                else False
            )

        if integration := self.get_integration(integration_id):
            return self._is_integration_ready(integration)
        else:
            raise ops.RelationNotFoundError()

    def is_joined(self) -> bool:
        """Check if the integration is joined.

        Warnings:
            - This method only checks if the integration is joined. It does not check if the
              necessary data is available in the integration application/unit databag.
        """
        return True if self.model.relations.get(self._integration_name) else False

    def _is_integration_ready(self, integration: ops.Relation) -> bool:
        """Check if an integration is ready."""
        if not integration.app:
            return False

        app_data = integration.data[integration.app]
        if not all(k in app_data for k in self._required_app_data):
            return False
        if not self._app_data_validator(app_data):
            return False

        return True

    def _load_integration_data[T](
        self,
        cls: type[T],
        /,
        integration: ops.Relation | None = None,
        integration_id: int | None = None,
        *,
        target: Literal["app", "unit"] = "app",
        decoder: Callable[[str], Any] | None = None,
    ) -> list[T]:
        """Load integration data.

        Args:
            cls: Dataclass that will wrap integration data.
            integration: Integration instance to pull data.
            integration_id: Integration ID to pull data from.
            target: Pull data from either the application or unit databag.
            decoder: Callable that will be used to decode each field.

        Raises:
            ValueError: Raised if an incorrect target is provided.

        Returns:
            A list containing integration data. If `target` is set to `"app"`, the
            returned list will only contain one object holding the application data.
        """
        if not integration:
            integration = self.get_integration(integration_id)

        match target:
            case "app":
                return [integration.load(cls, integration.app, decoder=decoder)]
            case "unit":
                return [integration.load(cls, unit, decoder=decoder) for unit in integration.units]
            case _:
                raise ValueError(
                    f"expected 'app' or 'unit' for `target`. received '{target}' instead"
                )

    def _save_integration_data(
        self,
        data: object,
        /,
        target: ops.Application | ops.Unit,
        integration_id: int | None = None,
        *,
        encoder: Callable[[Any], str] | None = None,
        merge: bool = False,
        decoder: Callable[[str], Any] | None = None,
    ) -> None:
        """Save integration data.

        Args:
            data: Dataclass object to save to the integration.
            target: Location to save object.
            integration_id: ID of integration to update.
            encoder: Callable that will be used to encode each field.
            merge:
                Whether to merge data into the integration databag rather than
                overwriting. When ``True``, only fields whose values differ from
                their dataclass defaults are written; existing values for unset
                fields are preserved.
            decoder:
                Callable used to decode existing databag data when merging.
                Only used when ``merge`` is True.
        """
        integrations = self.integrations
        if integration_id is not None:
            integrations = [self.get_integration(integration_id)]

        if not merge:
            for integration in integrations:
                integration.save(data, target, encoder=encoder)

            return

        cls = type(data)
        if not dataclasses.is_dataclass(cls):
            raise TypeError(f"`merge=True` requires a dataclass instance, got '{cls.__name__}'")

        set_fields = {
            f.name: getattr(data, f.name)
            for f in dataclasses.fields(cls)
            if not self._field_is_default(f, getattr(data, f.name))
        }

        for integration in integrations:
            existing = integration.load(cls, target, decoder=decoder)
            merged = dataclasses.replace(existing, **set_fields)
            integration.save(merged, target, encoder=encoder)

    @staticmethod
    def _field_is_default(field: dataclasses.Field, value: Any) -> bool:
        """Check if a field value is equal to its declared default."""
        if field.default is not dataclasses.MISSING:
            return value == field.default
        if field.default_factory is not dataclasses.MISSING:
            return value == field.default_factory()
        return False

    @staticmethod
    def _is_integration_active(integration: ops.Relation) -> bool:
        """Check if an integration is active by accessing contained data."""
        try:
            _ = repr(integration.data)
            return True
        except (RuntimeError, ops.ModelError):
            return False
