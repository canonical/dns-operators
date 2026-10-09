[![CharmHub Badge](https://charmhub.io/dns-aggregator/badge.svg)](https://charmhub.io/dns-aggregator)
[![Publish to edge](https://github.com/canonical/dns-operators/actions/workflows/publish-dns-aggregator-operator-edge.yaml/badge.svg)](https://github.com/canonical/dns-operators/actions/workflows/publish-dns-aggregator-operator-edge.yaml)
[![Discourse Status](https://img.shields.io/discourse/status?server=https%3A%2F%2Fdiscourse.charmhub.io&style=flat&label=CharmHub%20Discourse)](https://discourse.charmhub.io)

# DNS aggregator operator

A [Juju](https://juju.is/) [charm](https://documentation.ubuntu.com/juju/3.6/reference/charm/)
aggregating the DNS record requests of several requirers into a single integration with a
DNS provider.

The charm sits between the requirers of the `dns_record` interface and the provider
serving them. It combines the record requests of its downstream integrations, forwards
them upstream as a single request set, and dispatches the responses of the provider back
to the requirer they belong to.

## Get started

The charm can be deployed to any machine model by pulling it from [Charmhub](https://charmhub.io/dns-aggregator):
```
juju deploy dns-aggregator --channel=latest/edge
```

It is then integrated with the DNS provider serving the requests, and with the requirers
whose requests are aggregated:
```
juju integrate dns-aggregator:dns-record-requirer bind
juju integrate dns-aggregator:dns-record-provider my-application
juju integrate dns-aggregator:dns-record-provider-mixin another-application
```

## Learn more
* [Read more](https://charmhub.io/dns-aggregator/docs)
* [`dns_record` interface](https://canonical.github.io/charm-relation-interfaces/interfaces/dns_record/v0/)

## Project and community
* [Issues](https://github.com/canonical/dns-operators/issues)
* [Contribute](https://github.com/canonical/dns-operators/blob/main/CONTRIBUTING.md)
* [Matrix](https://matrix.to/#/#charmhub-charmdev:ubuntu.com)
