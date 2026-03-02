# DNS operators

This repository provides a collection of operators required to deploy a fully
functional [DNS](https://en.wikipedia.org/wiki/Domain_Name_System) solution,
facilitating the integration of DNS services with other charms.

The goal is to provide an easy-to-use and reliable DNS deployment that offers
a simple integration for your existing charmed applications,
enabling them to request resource records and automate DNS processes.

This repository contains the code for the following DNS charms:
1. `bind`: A machine charm managing a bind instance configured as a primary DNS server. See the [bind README](bind-operator/README.md) for more information.
2. `dns-policy`: A subordinate charm that adds a policy layer in front of the bind charm. See the [dns-policy README](dns-policy-operator/README.md) for more information.
3. `dns-integrator`: An integrator charm that allows the creation of record request through its configuration. See the [dns-integrator README](dns-integrator-operator/README.md) for more information.
4. `dns-resolver`: A resolver charm that provides a single point of configuration for all the requirers using the same DNS server. See the [dns-resolver README](dns-resolver-operator/README.md) for more information.
5. `dns-secondary`: A secondary charm that provides a hidden primary setup by serving the zones without leaking any IP address of the primary deployment. See the [dns-secondary README](dns-secondary-operator/README.md) for more information.

The repository also contains the snapped workload of some charms:
1. `charmed-bind`: A snapped bind specifically made for the bind charm. See the [charmed-bind README](charmed-bind/README.md) for more information.
2. `charmed-dns-policy`: A snapped Django application specifically made for the dns-policy charm. See the [charmed-dns-policy README](charmed-dns-policy/README.md) for more information.

## Documentation

Our documentation is stored in the `docs` directory.
It is based on the Canonical starter pack
and hosted on [Read the Docs](https://about.readthedocs.com/). In structuring,
the documentation employs the [Diátaxis](https://diataxis.fr/) approach.

You may open a pull request with your documentation changes, or you can
[file a bug](https://github.com/canonical/dns-operators/issues) to provide constructive feedback or suggestions.

To run the documentation locally before submitting your changes:

```bash
cd docs
make run
```

GitHub runs automatic checks on the documentation
to verify spelling, validate links and style guide compliance.

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
