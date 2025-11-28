# DNS Policy Terraform Module

Terraform module for deploying the [DNS Policy charm](https://charmhub.io/dns-policy).

The DNS Policy charm is a subordinate charm that provides a policy approval layer for DNS records. It requires a PostgreSQL database and integrates with DNS record providers to enable approval workflows for DNS record requests.

**Note:** This is a subordinate charm and does not have a `units` variable. It scales with the principal charm to which it is related.

## Usage

```hcl
module "dns_policy" {
  source = "git::https://github.com/canonical/dns-operators//dns-policy-operator/terraform?ref=main"

  model   = juju_model.my_model.name
  channel = "latest/stable"

  config = {
    debug          = "true"
    allowed-hosts  = "localhost,127.0.0.1"
  }
}
```

## Integration Example

Deploy DNS policy with a database and integrate it with Bind:

```hcl
data "juju_model" "dns" {
  name = "dns-model"
}

# Database for DNS policy
resource "juju_application" "postgresql" {
  name  = "postgresql"
  model = data.juju_model.dns.name

  charm {
    name    = "postgresql"
    channel = "14/stable"
  }

  units = 1
}

# Principal charm (Bind)
module "bind" {
  source = "git::https://github.com/canonical/dns-operators//bind-operator/terraform"
  model  = data.juju_model.dns.name
}

# Subordinate charm (DNS Policy)
module "dns_policy" {
  source = "git::https://github.com/canonical/dns-operators//dns-policy-operator/terraform"
  model  = data.juju_model.dns.name

  config = {
    allowed-hosts = "0.0.0.0"
  }
}

# Connect dns-policy to database
resource "juju_integration" "dns_policy_database" {
  model = data.juju_model.dns.name

  application {
    name     = juju_application.postgresql.name
    endpoint = "database"
  }

  application {
    name     = module.dns_policy.app_name
    endpoint = module.dns_policy.requires.database
  }
}

# Connect dns-policy to bind (subordinate relationship)
resource "juju_integration" "dns_policy_requirer" {
  model = data.juju_model.dns.name

  application {
    name     = module.bind.app_name
    endpoint = module.bind.provides.dns_record
  }

  application {
    name     = module.dns_policy.app_name
    endpoint = module.dns_policy.requires.dns_record_requirer
  }
}
```

<!-- BEGIN_TF_DOCS -->
## Requirements

| Name | Version |
|------|---------|
| <a name="requirement_terraform"></a> [terraform](#requirement\_terraform) | >= 1.6 |
| <a name="requirement_juju"></a> [juju](#requirement\_juju) | >= 0.14.0 |

## Providers

| Name | Version |
|------|---------|
| <a name="provider_juju"></a> [juju](#provider\_juju) | >= 0.14.0 |

## Resources

| Name | Type |
|------|------|
| [juju_application.dns_policy](https://registry.terraform.io/providers/juju/juju/latest/docs/resources/application) | resource |

## Inputs

| Name | Description | Type | Default | Required |
|------|-------------|------|---------|:--------:|
| <a name="input_app_name"></a> [app\_name](#input\_app\_name) | Name of the application in the Juju model | `string` | `"dns-policy"` | no |
| <a name="input_base"></a> [base](#input\_base) | The operating system on which to deploy | `string` | `"ubuntu@22.04"` | no |
| <a name="input_channel"></a> [channel](#input\_channel) | The channel to use when deploying a charm | `string` | `"latest/edge"` | no |
| <a name="input_config"></a> [config](#input\_config) | Application configuration. Details in https://charmhub.io/dns-policy/configure | `map(string)` | `{}` | no |
| <a name="input_model"></a> [model](#input\_model) | Reference to a `juju_model` resource | `string` | n/a | yes |
| <a name="input_revision"></a> [revision](#input\_revision) | Revision number of the charm | `number` | `null` | no |

## Outputs

| Name | Description |
|------|-------------|
| <a name="output_app_name"></a> [app\_name](#output\_app\_name) | Name of the deployed application |
| <a name="output_application"></a> [application](#output\_application) | The deployed application |
| <a name="output_provides"></a> [provides](#output\_provides) | Provided endpoints |
| <a name="output_requires"></a> [requires](#output\_requires) | Required endpoints |
<!-- END_TF_DOCS -->
