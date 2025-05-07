# Security

This document outlines common risks and possible best practices specifically for the DNS charms. It
focuses on configurations and protections available through the charms themselves.

The overall best practice is to [keep your charms updated](https://documentation.ubuntu.com/juju/3.6/reference/juju-cli/list-of-juju-cli-commands/refresh/) to the latest version available.  
A good understanding of [the DNS system](https://bind9.readthedocs.io/en/stable/chapter1.html) is also helpful.

## Configuration

The DNS charms have security-related configurations, and misconfiguring them can lead to vulnerabilities.  

### bind-operator

No security-related configurations available.

### dns-policy

`dns-policy` uses a Django application under the hood for its API and web interface. As such, it can be configured following
some of Django's configurations.  
- **debug**: Puts the application in [debug mode](https://docs.djangoproject.com/en/stable/ref/settings/#std-setting-DEBUG).
- **allowed-hosts**: Configures the [hosts allowed](https://docs.djangoproject.com/en/stable/ref/settings/#std-setting-ALLOWED_HOSTS) to reach the API and web interface of the application.

### dns-integrator

No security-related configurations available.

## Data

Only the dns-policy is using an external database to store its data, through a postgresql interface.

### Back up PostgreSQL

Follow the instructions of the PostgreSQL charm:
 - For [postgresql-k8s](https://charmhub.io/postgresql-k8s/docs/h-create-backup).
 - For [postgresql](https://charmhub.io/postgresql/docs/h-create-backup).

If you plan to restore PostgreSQL in a different model or cluster, you will need
to also back up the cluster passwords. See:
 - For [postgresql-k8s](https://charmhub.io/postgresql-k8s/docs/h-migrate-cluster).
 - For [postgresql](https://charmhub.io/postgresql/docs/h-migrate-cluster).

### Restore PostgreSQL

Follow the instructions given by PostgreSQL:
 - For postgresql-k8s: [local restore](https://charmhub.io/postgresql/docs/h-restore-backup), [foreign backup](https://charmhub.io/postgresql/docs/h-migrate-cluster).
 - for postgresql: [local restore](https://charmhub.io/postgresql/docs/h-restore-backup), [foreign backup](https://charmhub.io/postgresql/docs/h-migrate-cluster).

## Upstream

The DNS charms use external software to work properly.  
It can be useful to be aware of the security recommendations of those.

For details regarding upstream Bind configuration and broader security considerations, please
refer to the [official Bind documentation](https://bind9.readthedocs.io/en/stable/chapter7.html).

For details regarding upstream Django configuration and broader security considerations, please
refer to the [official Django documentation](https://docs.djangoproject.com/en/stable/topics/security/).
