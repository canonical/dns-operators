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

## Integrations

| Endpoint | Interface | Role | Limit | Description |
|----------|-----------|------|-------|-------------|
| `dns-record-requirer` | `dns_record` | requires | 1 | The DNS provider every aggregated request is forwarded to. |
| `dns-record-provider` | `dns_record` | provides | 1 | The main downstream requirer. Its record requests and its automatically allocated domain data are proxied. |
| `dns-record-provider-mixin` | `dns_record` | provides | - | Additional downstream requirers. Only their record requests are proxied. |

The `dns-record-provider` endpoint accepts a single integration. Juju is not able to
enforce that limit on a `provides` endpoint, so the charm goes into a blocked state and
stops forwarding anything while more than one application is integrated on it.

### Record requests

The record requests published by every downstream requirer, on `dns-record-provider` as
well as on `dns-record-provider-mixin`, are combined and published to the DNS provider as
a single set of requests. The responses of the provider are dispatched back to the
downstream requirer that asked for them, matched on the uuid of the request.

### Automatically allocated domains

The automatically allocated domain data is only proxied between the main downstream
requirer and the DNS provider. Mixin requirers neither declare addresses nor receive a
domain.

The `ddns-domain` allocated by the provider is republished to the main downstream
requirer as it is. The `ddns-addresses` declared by the main downstream requirer are
forwarded to the provider as they are. When it declares none, the charm forwards the
`ingress-address` of its units instead, so that the allocated domain still resolves to
the requirer.

The charm never publishes an empty `ddns-addresses` field, as the provider would then
resolve the allocated domain to the units of the aggregator rather than to the ones of
the requirer. While no address can be derived, the last published ones are kept.

### Basic operations

No actions and no configuration options are available, as this charm is entirely operated
through its integrations.

## Learn more
* [Read more](https://charmhub.io/dns-aggregator/docs)
* [`dns_record` interface](https://canonical.github.io/charm-relation-interfaces/interfaces/dns_record/v0/)

## Project and community
* [Issues](https://github.com/canonical/dns-operators/issues)
* [Contribute](https://github.com/canonical/dns-operators/blob/main/CONTRIBUTING.md)
* [Matrix](https://matrix.to/#/#charmhub-charmdev:ubuntu.com)
