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

"""Libraries for interfacing with machine resources."""

__all__ = [
    # From `apt.py`
    "AptLifecycleManager",
    "AptOpsManager",
    "apt",
    "dpkg_query",
    # From `nvidia.py`
    "DCGMManager",
    # From `snap.py`
    "SnapConfigManager",
    "SnapLifecycleManager",
    "SnapOpsManager",
    "SnapServiceManager",
    "snap",
    # From `systemd.py`
    "SystemctlServiceManager",
    "systemctl",
    "is_container",
]

from .apt import AptLifecycleManager, AptOpsManager, apt, dpkg_query
from .nvidia import DCGMManager
from .snap import SnapConfigManager, SnapLifecycleManager, SnapOpsManager, SnapServiceManager, snap
from .systemd import SystemctlServiceManager, is_container, systemctl
