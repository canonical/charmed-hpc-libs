# Copyright 2025 Canonical Ltd.
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

"""Base protocol for defining service managers."""

__all__ = ["ServiceManager"]

from abc import abstractmethod
from typing import Protocol


class ServiceManager(Protocol):  # pragma: no cover
    """Base protocol for defining service managers."""

    @abstractmethod
    def start(self) -> None:  # noqa D102
        raise NotImplementedError

    @abstractmethod
    def stop(self) -> None:  # noqa D102
        raise NotImplementedError

    @abstractmethod
    def enable(self) -> None:  # noqa D102
        raise NotImplementedError

    @abstractmethod
    def disable(self) -> None:  # noqa D102
        raise NotImplementedError

    @abstractmethod
    def restart(self) -> None:  # noqa D102
        raise NotImplementedError

    @abstractmethod
    def reload(self) -> None:  # noqa D102
        raise NotImplementedError

    @abstractmethod
    def is_active(self) -> bool:  # noqa D102
        raise NotImplementedError
