[![CharmHub Badge](https://charmhub.io/bind/badge.svg)](https://charmhub.io/dns-policy)
[![Publish to edge](https://github.com/canonical/dns-operators/actions/workflows/publish_charm.yaml/badge.svg)](https://github.com/canonical/dns-operators/actions/workflows/publish_charm.yaml)
[![Promote charm](https://github.com/canonical/dns-operators/actions/workflows/promote_charm.yaml/badge.svg)](https://github.com/canonical/dns-operators/actions/workflows/promote_charm.yaml)
[![Discourse Status](https://img.shields.io/discourse/status?server=https%3A%2F%2Fdiscourse.charmhub.io&style=flat&label=CharmHub%20Discourse)](https://discourse.charmhub.io)

# Dns Policy Operator

A [subordinate](https://canonical-juju.readthedocs-hosted.com/en/latest/user/reference/charm/index.html#subordinate) [Juju](https://juju.is/) [charm](https://juju.is/docs/olm/charmed-operators)
enabling a policy layer on top of a DNS charm like [Bind](https://github.com/canonical/dns-operators/tree/main/bind-operator).

After deploying the Bind operator, you may want to restrict the possibility of any charm integrating with it and freely modifying the DNS records it serves. You may want to add formal human approval for each incoming DNS resource record request. That's when you want to use the DNS Policy charm.

By deploying this charm and integrating it with the Bind operator, you create a policy layer that can be operated using a web interface and/or an API, all provided by the Django workload operated by it.

## Get started

The charm can be deployed to any machine model by pulling it from [Charmhub](https://charmhub.io/bind):
```
juju deploy dns-policy --channel=latest/edge
```

You then need to integrate it with a charm supporting the `dns_record` interface for it to work as it is a subordinate charm.  

Before beeing able to review incoming dns record requests, you will need to create a reviewer account.  
To do that, use the `create-reviewer` command and then log in using it's credentials to the dns-policy interface.  
The charm can integrate with any requirer charm implementing the [dns_record interface](https://canonical.github.io/charm-relation-interfaces/interfaces/dns_record/v0/).
This charm will be give your reviewers the ability to manage all the DNS record requests from those requirer. Only one provider can be integrated.

### Basic operations

#### Create a reviewer

Once the charm deployed and running, you can create a reviewer with the following command:  
`juju run <dns-policy-unit> create-reviewer username=<reviewer-username> email=<reviewer-email>`  
The action will generate a password and display it once the user has been created.

Example:
```
$ juju run dns-policy/0 create-reviewer username=reviewer email=reviewer@example.com
Running operation 3 with 1 task
  - task 4 on unit-dns-policy-0

Waiting for task 4...
result: |
  User reviewer created successfully
  Generated password: znaLEEYA6s9sfFht
```

#### Restrict incoming requests

The workload of the DNS policy charm is a Django application. As such, it can be restricted on incoming requests
using the `allowed-hosts` configuration.  
Example: `juju config dns-policy allowed-hosts="1.2.3.4"`  
This will restrict incoming requests to only `1.2.3.4`.

See more information about allowed hosts in the [Django documentation](https://docs.djangoproject.com/en/5.1/ref/settings/#allowed-hosts).

#### Set logging

The workload snap and underlying Django application can be set to debug mode by setting the debug configuration.  
Example: `juju config dns-policy debug=true`  

See more information about debug mode in the [Django documentation](https://docs.djangoproject.com/en/5.1/ref/settings/#debug).

## Learn more
* [Read more](https://charmhub.io/dns-policy/docs)

## Project and community
* [Issues](https://github.com/canonical/dns-operators/issues)
* [Contribute](https://github.com/canonical/dns-operators/blob/main/CONTRIBUTING.md)
* [Matrix](https://chat.charmhub.io/charmhub/channels/charm-dev)
