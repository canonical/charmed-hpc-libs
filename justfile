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

uv := require("uv")

project_dir := justfile_directory()
tests_dir := project_dir / "tests"

export PY_COLORS := "1"
export PYTHONBREAKPOINT := "pdb.set_trace"

uv_run := "uv run --frozen --extra dev"

[private]
default:
    @just help

# Regenerate uv.lock
lock:
    uv lock

# Create a development environment
env: lock
    uv sync --extra dev

# Upgrade uv.lock with the latest dependencies
upgrade:
    uv lock --upgrade

# Apply coding style standards to code
fmt: lock
    {{uv_run}} ruff format
    {{uv_run}} ruff check --fix

# Check code against coding style standards
lint fix="": lock
    #!/usr/bin/env bash
    set -o errexit

    if [ '{{fix}}' = "--fix" ]; then fix="true"; else fix=""; fi

    {{uv_run}} codespell --skip uv.lock ${fix:+-w}
    {{uv_run}} ruff check ${fix:+--fix}

# Run static type checker on code
typecheck: lock
    {{uv_run}} pyright

# Run unit tests
unit *args: lock
    {{uv_run}} coverage run -m pytest --tb native -v -s {{args}} {{tests_dir / "unit"}}
    {{uv_run}} coverage report
    {{uv_run}} coverage xml -o {{project_dir / "cover" / "coverage.xml"}}

# Show available recipes
help:
    @just --list --unsorted
