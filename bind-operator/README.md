[![CharmHub Badge](https://charmhub.io/bind/badge.svg)](https://charmhub.io/bind)
[![Publish to edge](https://github.com/canonical/dns-operators/actions/workflows/publish-charmed-bind-edge.yaml/badge.svg)](https://github.com/canonical/dns-operators/actions/workflows/publish-charmed-bind-edge.yaml)
[![Promote charm](https://github.com/canonical/dns-operators/actions/workflows/promote-bind-operator.yaml/badge.svg)](https://github.com/canonical/dns-operators/actions/workflows/promote-bind-operator.yaml)
[![Discourse Status](https://img.shields.io/discourse/status?server=https%3A%2F%2Fdiscourse.charmhub.io&style=flat&label=CharmHub%20Discourse)](https://discourse.charmhub.io)

# Bind operator

A [Juju](https://juju.is/) [charm](https://documentation.ubuntu.com/juju/3.6/reference/charm/)
deploying and managing a DNS server on bare metal.

This charm simplifies configuration of a DNS server by providing a single point
of configuration for all the requirers using the same DNS server. It can be
deployed on virtual machines or bare metal.

As such, the charm makes it easy to manage and propagate DNS configuration while
giving the freedom to deploy on the substrate of their choice.

For DevOps or SRE teams this charm will make operating any charm requiring dynamic DNS
configuration simple and straightforward through Juju's clean interface.

## Get started

The charm can be deployed to any machine model by pulling it from [Charmhub](https://charmhub.io/bind):
```
juju deploy bind --channel=latest/edge
```

You can then integrate it with any charm supporting the requirer side of the `dns_record` interface, and the bind operator will
start serving those DNS records.

### Basic operations

No actions are available as this charm is meant to be operated through its integrations.  
The charm can integrate with any requirer charm implementing the [`dns_record` interface](https://canonical.github.io/charm-relation-interfaces/interfaces/dns_record/v0/).

## Learn more
* [Read more](https://charmhub.io/bind/docs)
* [Official webpage](https://www.isc.org/bind/)

## Project and community
* [Issues](https://github.com/canonical/dns-operators/issues)
* [Contribute](https://github.com/canonical/dns-operators/blob/main/CONTRIBUTING.md)
* [Matrix](https://matrix.to/#/#charmhub-charmdev:ubuntu.com)
