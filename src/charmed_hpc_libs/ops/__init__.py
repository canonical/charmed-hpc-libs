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

"""Libraries for building HPC charms."""

__all__ = [
    # From `apt.py`
    "AptOpsManager",
    "apt",
    "dpkg_query",
    # From `conditions.py`
    "Condition",
    "ConditionEvaluation",
    "StopCharm",
    "block_unless",
    "integration_exists",
    "integration_not_exists",
    "leader",
    "refresh",
    "wait_unless",
    # From `core` module
    "call",
    "OpsManager",
    "ServiceManager",
    # From `env.py`
    "EnvManager",
    # From `exporters.py`
    "NodeExporterManager",
    # From `machine` module
    "DCGMManager",
    "SnapConfigManager",
    "SnapLifecycleManager",
    "SnapOpsManager",
    "SnapServiceManager",
    "SystemctlServiceManager",
    "is_container",
    "snap",
    "systemctl",
    # From `network.py`
    "get_ingress_address",
    # From `secrets.py`
    "load_secret",
    "update_secret",
]

from .conditions import (
    Condition,
    ConditionEvaluation,
    StopCharm,
    block_unless,
    integration_exists,
    integration_not_exists,
    leader,
    refresh,
    wait_unless,
)
from .core import OpsManager, ServiceManager, call
from .env import EnvManager
from .exporters import NodeExporterManager
from .machine import (
    AptOpsManager,
    DCGMManager,
    SnapConfigManager,
    SnapLifecycleManager,
    SnapOpsManager,
    SnapServiceManager,
    SystemctlServiceManager,
    apt,
    dpkg_query,
    is_container,
    snap,
    systemctl,
)
from .network import get_ingress_address
from .secrets import load_secret, update_secret
