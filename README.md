# charmed-hpc-libs

[![hpc-libs tests](https://github.com/canonical/charmed-hpc-libs/actions/workflows/ci.yaml/badge.svg)](https://github.com/canonical/charmed-hpc-libs/actions/workflows/ci.yaml)
![GitHub License](https://img.shields.io/github/license/canonical/charmed-hpc-libs)
[![Matrix](https://img.shields.io/matrix/ubuntu-hpc%3Amatrix.org?logo=matrix&label=ubuntu-hpc)](https://matrix.to/#/#hpc:ubuntu.com)

A software development kit for authoring HPC charms 📖🖋️

The charmed-hpc-libs package is used within the [Juju charms](https://juju.is/charms-architecture) that compose
Charmed HPC. The current libraries shipped in charmed-hpc-libs include:

- `errors`: Common exceptions and errors raised in HPC charms.
- `interfaces`: Libraries for building HPC integration interface implementations.
- `ops`: Libraries for building HPC charms.

## ✨ Getting Started

Each module contains documentation and usage information in its module-level docstring.

## 🤔 What's next?

If you want to learn more about all the things you can do with the charmed-hpc-libs package,
or have any further questions on what you can do with the package, here are some
further resources for you to explore:

* [Open an issue](https://github.com/canonical/charmed-hpc-libs/issues/new?title=ISSUE+TITLE&body=*Please+describe+your+issue*)
* [Ask a question on Github](https://github.com/orgs/canonical/discussions/categories/q-a)

## 🛠️ Development

The project uses [just](https://github.com/casey/just) and [uv](https://github.com/astral-sh/uv) for
development, which provides some useful commands that will help you while hacking on charmed-hpc-libs:

```shell
just fmt            # Apply formatting standards to code.
just lint           # Check code against coding style standards.
just typecheck      # Run static type checks.
just unit           # Run unit tests.
```

If you're interested in contributing your work to charmed-hpc-libs,
take a look at our [contributing guidelines](./CONTRIBUTING.md) for further details.

## 🤝 Project and community

charmed-hpc-libs is a project of the [Ubuntu High-Performance Computing community](https://ubuntu.com/community/governance/teams/hpc).
Interested in contributing bug fixes, new editors, documentation, or feedback? Want to join the Ubuntu HPC community? You’ve come to the right place 🤩

Here’s some links to help you get started with joining the community:

* [Ubuntu Code of Conduct](https://ubuntu.com/community/ethos/code-of-conduct)
* [Contributing guidelines](./CONTRIBUTING.md)
* [Join the conversation on Matrix](https://matrix.to/#/#hpc:ubuntu.com)
* [Get the latest news on Discourse](https://discourse.ubuntu.com/c/hpc/151)
* [Ask and answer questions on GitHub](https://github.com/orgs/canonical/discussions/categories/q-a)

## 📋 License

The charmed-hpc-libs package is free software, distributed under the Apache Software License, version 2.0.
See the [Apache-2.0 LICENSE](./LICENSE) file for further details.
