# DNS operators

This repository provides a collection of operators required to deploy a fully
functional [DNS](https://en.wikipedia.org/wiki/Domain_Name_System) solution,
facilitating the integration of DNS services with other charms.

The goal is to provide an easy-to-use and reliable DNS deployment that offers
a simple integration for your existing charmed applications,
enabling them to request resource records and automate DNS processes.
For hosted user tutorials, operations, and reference documentation, see https://canonical.com/juju/docs/dns-charms.

The charms are designed for machine models and can be combined into a hidden-primary topology:
applications or `dns-integrator` request records, `bind` stores and serves authoritative zones,
optional `dns-policy` is a subordinate charm related to `bind` that adds an approval layer in front of
the DNS provider, `dns-secondary` receives zones from `bind`, and `dns-resolver` resolves client queries through the authoritative chain.

## Repository layout

```
bind-operator/               # Juju charm: primary authoritative BIND DNS server

charmed-bind/                # Snap workload used by the bind charm
charmed-dns-policy/          # Snap workload used by the dns-policy charm

dns-integrator-operator/     # Juju charm: creates DNS record requests from charm configuration
dns-policy-operator/         # Juju subordinate charm: approval/policy layer for DNS record requests
dns-resolver-operator/       # Juju charm: DNS resolver that consumes authority information
dns-secondary-operator/      # Juju charm: secondary DNS server for hidden-primary deployments

docs/                        # Source for the DNS operators documentation

lib/                         # Shared charm libraries and library tests

terraform/                   # Terraform module that deploys and integrates DNS charms

tests/                       # Shared integration and unit tests
```

## Components

This repository contains the code for the following DNS charms:

| Component | Path | Role |  |
| --- | --- | --- | --- |
| `bind` | [`bind-operator/`](bind-operator/README.md) | A machine charm managing a bind instance configured as a primary DNS server. |  |
| `dns-policy` | [`dns-policy-operator/`](dns-policy-operator/README.md) | A subordinate charm that adds a policy layer in front of the bind charm. |  |
| `dns-integrator` | [`dns-integrator-operator/`](dns-integrator-operator/README.md) | An integrator charm that allows the creation of record request through its configuration. |  |
| `dns-resolver` | [`dns-resolver-operator/`](dns-resolver-operator/README.md) | A resolver charm that provides a single point of configuration for all the requirers using the same DNS server. |  |
| `dns-secondary` | [`dns-secondary-operator/`](dns-secondary-operator/README.md) | A secondary charm that provides a hidden primary setup by serving the zones without leaking any IP address of the primary deployment. |  |

The repository also contains the snapped workload of some charms:

| Component | Path | Role | Related charm |
| --- | --- | --- | --- |
| `charmed-bind` | [`charmed-bind/`](charmed-bind/README.md) | A snapped bind specifically made for the bind charm. | Workload used by [`bind-operator/`](bind-operator/README.md). |
| `charmed-dns-policy` | [`charmed-dns-policy/`](charmed-dns-policy/README.md) | A snapped Django application specifically made for the dns-policy charm. | Workload used by [`dns-policy-operator/`](dns-policy-operator/README.md). |

### Charmhub and Snapcraft

| Name | Listing |
| --- | --- |
| `bind` | https://charmhub.io/bind |
| `dns-integrator` | https://charmhub.io/dns-integrator |
| `dns-policy` | https://charmhub.io/dns-policy |
| `dns-resolver` | https://charmhub.io/dns-resolver |
| `dns-secondary` | https://charmhub.io/dns-secondary |
| `charmed-bind` | https://snapcraft.io/charmed-bind |
| `charmed-dns-policy` | https://snapcraft.io/charmed-dns-policy |

## Get started

For a new DNS deployment, start with the in-repository tutorial index at [`docs/tutorial/index.md`](docs/tutorial/index.md). It links to:

- [`docs/tutorial/simple-deployment.md`](docs/tutorial/simple-deployment.md), which deploys `bind` and `dns-integrator`, integrates them, creates a test DNS record, and scales `bind`.
- [`docs/tutorial/secondary-and-resolver.md`](docs/tutorial/secondary-and-resolver.md), which extends the deployment with `dns-secondary` and `dns-resolver`.

For Terraform-based deployments, see [`terraform/README.md`](terraform/README.md).

## Documentation

Our documentation is stored in the `docs` directory and
can be viewed at https://canonical.com/juju/docs/dns-charms.
It is based on the Canonical Sphinx Stack and hosted on
[Read the Docs](https://about.readthedocs.com/). In structuring, the
documentation employs the [Diátaxis](https://diataxis.fr/) approach.

You may open a pull request with your documentation changes, or you can
[file a bug](https://github.com/canonical/dns-operators/issues) to
provide constructive feedback or suggestions.

To run the documentation locally before submitting your changes:

```bash
cd docs
make run
```

GitHub runs automatic checks on the documentation to verify spelling,
validate links and style guide compliance.

You can (and should) run the same checks locally:

```bash
make spelling
make linkcheck
make vale
make lint-md
```

## Project and community

The DNS operators project is a member of the Ubuntu family. It is an
open source project that warmly welcomes community projects, contributions,
suggestions, fixes and constructive feedback.

* [Code of conduct](https://ubuntu.com/community/code-of-conduct)
* [Get support](https://discourse.charmhub.io/)
* [Issues](https://github.com/canonical/dns-operators/issues)
* [Matrix](https://matrix.to/#/#charmhub-charmdev:ubuntu.com)
* [Contribute](https://github.com/canonical/dns-operators/blob/main/CONTRIBUTING.md)

## Licensing and trademark

See [`LICENSE`](LICENSE).
