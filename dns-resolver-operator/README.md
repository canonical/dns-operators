# DNS resolver operator

A [Juju](https://juju.is/) [charm](https://documentation.ubuntu.com/juju/3.6/tutorial/)
deploying and managing a DNS resolver server on bare metal.

This charm simplifies configuration of a DNS server by providing a single point
of configuration for all the requirers using the same DNS server. It can be
deployed on virtual machines or bare metal.

As such, the charm makes it easy to manage and propagate DNS configuration while
giving the freedom to deploy on the substrate of their choice.

For DevOps or SRE teams this charm will make operating any charm requiring dynamic DNS
configuration simple and straightforward through Juju's clean interface.

## Get started

The charm can be deployed to any machine model by pulling it from [Charmhub](https://charmhub.io/dns-resolver):
```
juju deploy dns-resolver --channel=latest/edge
```

You can then integrate it with any charm supporting the provider side of the `dns_authority` interface, and the dns-resolver operator will
start acting as a DNS resolver server for the authority one.

### Basic operations

No actions are available as this charm is meant to be operated through its integrations.
The charm can integrate with any provider charm implementing the dns_authority interface.

## Learn more
* [Read more](https://charmhub.io/bind/docs)
* [Official webpage](https://www.isc.org/bind/)

## Project and community
* [Issues](https://github.com/canonical/dns-operators/issues)
* [Contribute](https://github.com/canonical/dns-operators/blob/main/CONTRIBUTING.md)
* [Matrix](https://matrix.to/#/#charmhub-charmdev:ubuntu.com)
