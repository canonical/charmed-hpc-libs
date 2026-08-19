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

"""Base observers for HPC charm observer implementations."""

__all__ = ["ConfigObserver", "Observer"]

import logging
from typing import Any

import ops
from pydantic import ValidationError

from .conditions import StopCharm

type _CharmType[T: ops.CharmBase] = T
_logger = logging.getLogger(__name__)


class Observer(ops.Object):
    """Base observer for HPC observer implementations."""

    def __init__(self, charm: _CharmType) -> None:
        super().__init__(charm, f"{type(charm).__name__}")
        self._charm = charm

    @property
    def charm(self) -> _CharmType:
        """The charm object being observed."""
        return self._charm


class ConfigObserver[T](Observer):
    """Observe charm application configuration data set with ``juju config``.

    Args:
        config_cls:
            The configuration class that will accept the charm application's
            configuration option values.
        args: Positional arguments to passthrough to ``config_cls`` when it is loaded.
        kwargs: Keyword arguments to passthrough to ``config_cls`` when it is loaded.
    """

    def __init__(self, charm: _CharmType, config_cls: type[T], *args: Any, **kwargs: Any) -> None:
        super().__init__(charm)
        self._config_cls = config_cls
        self._passthrough_args = args or []
        self._passthrough_kwargs = kwargs or {}

    def load(self) -> T:
        """Load charm application configuration data.

        Raises:
            StopCharm: Raised if the charm's application configuration fails validation.
        """
        try:
            return self._charm.load_config(
                self._config_cls,
                *self._passthrough_args,
                **self._passthrough_kwargs,
            )
        except ValidationError as e:
            failed_options = sorted({error["loc"][0] for error in e.errors() if error.get("loc")})
            message = (
                "configuration option(s) "
                + ", ".join(f"'{str(o).replace('_', '-')}'" for o in failed_options)
                + " failed validation"
            )
            _logger.exception(message)

            raise StopCharm(
                ops.BlockedStatus(f"{message.capitalize()}. See `juju debug-log` for details")
            ) from None
        except ValueError:
            # Handle if `_config_cls` is a native dataclass and not a pydantic object.
            message = "configuration option(s) failed validation"
            _logger.exception(message)

            raise StopCharm(
                ops.BlockedStatus(f"{message.capitalize()}. See `juju debug-log` for details")
            ) from None
