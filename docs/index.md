---
myst:
  html_meta:
    "description lang=en": "Deploy DNS infrastructure with Juju charms. Automated DNS record management through bind, policy controls, and seamless integration with charmed applications."
---

# DNS operators

The DNS operators are a set of open-source [Juju](https://canonical.com/juju) {ref}`charms <juju:charm>` that deploy and operate [bind](https://www.isc.org/bind/), an authoritative [DNS](https://en.wikipedia.org/wiki/Domain_Name_System) server.

Charmed applications that need DNS records, such as an A record for a new service or a TXT record for an ACME challenge, request them over the `dns_record` relation and the charms publish them. An optional policy charm lets an administrator review and approve those requests.

The charms are meant for teams that run their infrastructure with Juju.

## In this documentation

```{list-table}
:header-rows: 1
:widths: 15 30

* -
  -
* - **Get started**
  - {ref}`Deploy your first DNS charm <tutorial_simple_deployment>` | {ref}`Deploy a secondary DNS server and resolver <tutorial_secondary_and_resolver>`
* - **Operations**
  - {ref}`Upgrade <how_to_upgrade>` | {ref}`Changelog <changelog>`
* - **Design**
  - {ref}`Project overview <explanation_project_overview>` | {ref}`Architecture <explanation_charm_architecture>` | {ref}`Bind charm <reference_bind_charm_architecture>` | {ref}`DNS policy charm <reference_dns_policy_charm_architecture>` | {ref}`Components <reference_components>`
* - **Security**
  - {ref}`Overview <explanation_security>`
```

## How this documentation is organized

This documentation uses the [Diátaxis documentation structure](https://diataxis.fr/).

- The {ref}`Tutorials <tutorial_index>` take you step-by-step through deploying a DNS server, then a secondary server with a resolver.
- The {ref}`How-to guides <how_to>` cover upgrading the charms and contributing to the project.
- {ref}`Reference <reference>` describes the components and the architecture of the bind and DNS policy charms.
- {ref}`Explanation <explanation>` covers the `dns_record` interface, how record requests are merged and aggregated, and security.
- The {ref}`Changelog <changelog>` lists all notable changes to the charms.

## Project and community

The DNS operators are a member of the Ubuntu family. They are an open-source project that welcomes
contributions, suggestions, fixes, and constructive feedback, on the code and on this documentation.

- [Code of conduct](https://ubuntu.com/community/docs/ethos/code-of-conduct)
- [File a bug](https://github.com/canonical/dns-operators/issues)
- Get support through the [Discourse forum](https://discourse.charmhub.io/)
- Join our [online chat](https://matrix.to/#/#charmhub-charmdev:ubuntu.com)
- {ref}`Contribute <how_to_contribute>`

```{toctree}
:hidden:
how-to/index.md
reference/index.md
explanation/index.md
terraform/index.md
tutorial/index.md
changelog.md
```
