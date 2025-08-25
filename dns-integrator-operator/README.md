[![CharmHub Badge](https://charmhub.io/bind/badge.svg)](https://charmhub.io/dns-integrator)
[![Publish to edge](https://github.com/canonical/dns-operators/actions/workflows/publish-dns-integrator-operator-edge.yaml/badge.svg)](https://github.com/canonical/dns-operators/actions/workflows/publish-dns-integrator-operator-edge.yaml)
[![Promote charm](https://github.com/canonical/dns-operators/actions/workflows/promote-bind-operator.yaml/badge.svg)](https://github.com/canonical/dns-operators/actions/workflows/promote-bind-operator.yaml)
[![Discourse Status](https://img.shields.io/discourse/status?server=https%3A%2F%2Fdiscourse.charmhub.io&style=flat&label=CharmHub%20Discourse)](https://discourse.charmhub.io)

# DNS integrator operator

A [Juju](https://juju.is/) [charm](https://documentation.ubuntu.com/juju/3.6/reference/charm/)
deploying and managing a DNS record requests integrator on bare metal.

This charm simplifies the resource record requests creation towards an already deployed DNS charm
accepting the `dns_record` interface.

## Get started

The charm can be deployed to any machine model by pulling it from [Charmhub](https://charmhub.io/dns-integrator):
```
juju deploy dns-integrator --channel=latest/edge
```

You can then integrate it with any charm supporting the requirer side of the `dns_record` interface.  
Use the configuration of the charm to decide which resource record requests you want to send to the requirer charm.

### Basic operations

No actions are available as this charm is meant to be operated through its integrations.  
The charm can integrate with any requirer charm implementing the [`dns_record` interface](https://canonical.github.io/charm-relation-interfaces/interfaces/dns_record/v0/).

## Learn more
* [Read more](https://charmhub.io/dns-integrator/docs)

## Project and community
* [Issues](https://github.com/canonical/dns-operators/issues)
* [Contribute](https://github.com/canonical/dns-operators/blob/main/CONTRIBUTING.md)
* [Matrix](https://https://matrix.to/#/#charmhub-charmdev:ubuntu.com)
