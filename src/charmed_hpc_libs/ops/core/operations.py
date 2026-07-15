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

"""Base protocol for defining operations managers."""

__all__ = ["OpsManager"]

from abc import abstractmethod
from typing import Protocol

from .service import ServiceManager


class OpsManager(Protocol):  # pragma: no cover
    """Base protocol for defining operation managers."""

    @abstractmethod
    def service_manager_for(self, service: str) -> ServiceManager:  # noqa D102
        raise NotImplementedError

    @abstractmethod
    def install(self) -> None:  # noqa D102
        raise NotImplementedError

    @abstractmethod
    def remove(self) -> None:  # noqa D102
        raise NotImplementedError

    @abstractmethod
    def is_installed(self) -> bool:  # noqa D102
        raise NotImplementedError
