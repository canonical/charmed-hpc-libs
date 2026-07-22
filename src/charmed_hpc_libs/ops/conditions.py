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

"""The conditions pattern.

Use conditions to control when event handlers and charm helper methods are called.
"""

__all__ = [
    "Condition",
    "ConditionEvaluation",
    "StopCharm",
    "refresh",
    "leader",
    "integration_exists",
    "integration_not_exists",
    "block_unless",
    "wait_unless",
]

import logging
from collections.abc import Callable
from functools import partial, wraps
from typing import Any, NamedTuple

import ops

_logger = logging.getLogger(__name__)


class ConditionEvaluation(NamedTuple):  # noqa D101
    ok: bool
    message: str = ""


type Condition[T: ops.Object] = Callable[[T], ConditionEvaluation]


class StopCharm(Exception):  # noqa N818
    """Exception raised to set high-priority status message.

    Args:
        status: The status to set on the unit (and optionally the application).
        app_status: If ``True``, also set the application status to the unit
            status when the unit is the leader.
    """

    def __init__(self, status: ops.StatusBase, *, set_app_status: bool = False) -> None:
        super().__init__(status)  # only return the `status` message when using `str(e)`
        self.status = status
        self.set_app_status = set_app_status

    def __repr__(self) -> str:  # noqa D105
        return f"StopCharm({self.status!r}, set_app_status={self.set_app_status!r})"


def refresh[T: ops.Object](hook: Callable[[T], ops.StatusBase] | None = None) -> Callable:
    """Refresh a charm's status after running an event handler.

    Args:
        hook: State check hook to call after event handler completes.
    """

    def decorator(func: Callable[..., None]) -> Callable:
        @wraps(func)
        def wrapper(obj: T, *args: ops.EventBase, **kwargs: Any) -> None:
            event, *_ = args

            try:
                func(obj, *args, **kwargs)
            except StopCharm as e:
                _logger.debug(
                    (
                        "`StopCharm` exception raised while running `%s` event handler `%s.%s` ",
                        "on unit '%s'. setting unit status to `%s`",
                    ),
                    event.__class__.__name__,
                    obj.__class__.__name__,
                    func.__name__,
                    obj.model.unit.name,
                    e.status,
                )
                obj.model.unit.status = e.status
                if e.set_app_status:
                    try:
                        obj.model.app.status = e.status
                        _logger.debug(
                            "setting app status to `%s`",
                            e.status,
                        )
                    except RuntimeError:
                        pass
                return

            if hook is not None:
                _logger.debug(
                    "running status check function `%s` to determine new status for unit '%s'",
                    hook.__name__,
                    obj.model.unit.name,
                )
                status = hook(obj)
                _logger.debug(
                    "new status for unit '%s' determined to be `%s`",
                    obj.model.unit.name,
                    status,
                )
                obj.model.unit.status = status

        return wrapper

    return decorator


def leader(func: Callable[..., Any]) -> Callable[..., Any]:
    """Only run method if the unit is the application leader, otherwise skip."""

    @wraps(func)
    def wrapper(obj: ops.Object, *args: Any, **kwargs: Any) -> Any:
        if not obj.model.unit.is_leader():
            _logger.debug(
                (
                    "unit '%s' is not the leader of the '%s' application, ",
                    "skipping run of method `%s.%s`",
                ),
                obj.model.unit.name,
                obj.model.app.name,
                obj.__class__.__name__,
                func.__name__,
            )
            return None

        _logger.debug(
            "unit '%s' is the leader of the '%s' application, running method `%s.%s`",
            obj.model.unit.name,
            obj.model.app.name,
            obj.__class__.__name__,
            func.__name__,
        )
        return func(obj, *args, **kwargs)

    return wrapper


def integration_exists(name: str) -> Condition:
    """Check if an integration exists.

    Args:
        name: Name of integration to check existence of.
    """

    def wrapper(obj: ops.Object) -> ConditionEvaluation:
        return ConditionEvaluation(bool(obj.model.relations.get(name)), "")

    return wrapper


def integration_not_exists(name: str) -> Condition:
    """Check if an integration does not exist.

    Args:
        name: Name of integration to check existence of.
    """

    def wrapper(obj: ops.Object) -> ConditionEvaluation:
        not_exists = not bool(obj.model.relations.get(name))
        return ConditionEvaluation(
            not_exists, f"Waiting for integrations: [`{name}`]" if not_exists else ""
        )

    return wrapper


def _status_unless(*conditions: Condition, status: type[ops.StatusBase]) -> Callable[..., Any]:
    """Evaluate conditions.

    If a condition is `False`, set a new status message.

    Args:
        *conditions: Conditions to evaluate.
        status: Status type to set if a condition is evaluated to be `False`.
    """

    def decorator(func: Callable[..., Any]):
        @wraps(func)
        def wrapper(obj: ops.Object, *args: ops.EventBase, **kwargs: Any) -> Any:
            event, *_ = args
            _logger.debug("handling event `%s` on %s", event, obj.model.unit.name)

            for condition in conditions:
                ok, message = condition(obj)
                if not ok:
                    _logger.debug(
                        (
                            "condition '%s' evaluated to be `False`. deferring event `%s` and "
                            + "updating status of unit %s to `%s` with message '%s'"
                        ),
                        condition.__name__,
                        event,
                        obj.model.unit.name,
                        status.__name__,
                        message,
                    )
                    event.defer()
                    raise StopCharm(status(message))

            return func(obj, *args, **kwargs)

        return wrapper

    return decorator


block_unless = partial(_status_unless, status=ops.BlockedStatus)
wait_unless = partial(_status_unless, status=ops.WaitingStatus)
