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

"""Call a command with logging enabled."""

import logging
import subprocess

_logger = logging.getLogger(__name__)


def call(
    root: str,
    /,
    *args: str,
    stdin: str | None = None,
    check: bool = True,
    env: dict[str, str] | None = None,
) -> subprocess.CompletedProcess:
    """Call a command with logging enabled.

    Args:
        root: The root command to call.
        args: Arguments to pass to the root command.
        stdin: Standard input to pipe into the root command.
        check: If set to `True`, raise an error if the command exits with a non-zero exit code.
        env: Environment variables to pass to the root command. If set to `None`, the
            current process's environment is used.

    Raises:
        subprocess.CalledProcessError:
            Raised if the called command fails and check is set to `True`.
    """
    cmd = [root, *args]
    try:
        _logger.debug("running command %s", cmd)
        result = subprocess.run(
            cmd, input=stdin, capture_output=True, text=True, check=True, env=env
        )
    except subprocess.CalledProcessError as e:
        _logger.error(
            "command '%s' failed with:\nexit code %s\nstderr: %s",
            " ".join(cmd),
            e.returncode,
            e.stderr,
        )
        if check:
            raise

        result = e

    _logger.debug(
        "command '%s' completed with:\nexit code: %s\nstdout: %s\nstderr: %s",
        " ".join(cmd),
        result.returncode,
        result.stdout,
        result.stderr,
    )
    return subprocess.CompletedProcess(
        args=result.args,
        stdout=result.stdout.strip() if result.stdout else None,
        stderr=result.stderr.strip() if result.stderr else None,
        returncode=result.returncode,
    )
