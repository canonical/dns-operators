# DNS Secondary Terraform Module

Terraform module for deploying the [DNS Secondary charm](https://charmhub.io/dns-secondary).

The DNS Secondary charm provides a secondary DNS server that receives zone transfers from a primary DNS server, with support for TLS-encrypted transfers.

## Usage

```hcl
module "dns_secondary" {
  source = "git::https://github.com/canonical/dns-operators//dns-secondary-operator/terraform?ref=main"

  model   = juju_model.my_model.name
  channel = "latest/stable"
  units   = 2

  config = {
    public-ips      = "192.168.2.10,192.168.2.11"
    remote-hostname = "primary.example.com"
  }
}
```

## Integration Example

Deploy DNS secondary and connect it to a primary DNS server with TLS support:

```hcl
data "juju_model" "dns" {
  name = "dns-model"
}

module "bind" {
  source = "git::https://github.com/canonical/dns-operators//bind-operator/terraform"
  model  = data.juju_model.dns.name
  units  = 1
}

module "dns_secondary" {
  source = "git::https://github.com/canonical/dns-operators//dns-secondary-operator/terraform"
  model  = data.juju_model.dns.name
  units  = 2

  config = {
    public-ips = "192.168.2.10,192.168.2.11"
  }
}

# Connect for zone transfers
resource "juju_integration" "dns_transfer" {
  model = data.juju_model.dns.name

  application {
    name     = module.bind.app_name
    endpoint = module.bind.provides.dns_transfer
  }

  application {
    name     = module.dns_secondary.app_name
    endpoint = module.dns_secondary.requires.dns_transfer
  }
}

# Optional: TLS certificates integration
resource "juju_application" "self_signed_certificates" {
  name  = "self-signed-certificates"
  model = data.juju_model.dns.name

  charm {
    name    = "self-signed-certificates"
    channel = "latest/stable"
  }
}

resource "juju_integration" "tls" {
  model = data.juju_model.dns.name

  application {
    name     = juju_application.self_signed_certificates.name
    endpoint = "certificates"
  }

  application {
    name     = module.dns_secondary.app_name
    endpoint = module.dns_secondary.requires.bind_certificates
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
| [juju_application.dns_secondary](https://registry.terraform.io/providers/juju/juju/latest/docs/resources/application) | resource |

## Inputs

| Name | Description | Type | Default | Required |
|------|-------------|------|---------|:--------:|
| <a name="input_app_name"></a> [app\_name](#input\_app\_name) | Name of the application in the Juju model | `string` | `"dns-secondary"` | no |
| <a name="input_base"></a> [base](#input\_base) | The operating system on which to deploy | `string` | `"ubuntu@22.04"` | no |
| <a name="input_channel"></a> [channel](#input\_channel) | The channel to use when deploying a charm | `string` | `"latest/edge"` | no |
| <a name="input_config"></a> [config](#input\_config) | Application configuration. Details in https://charmhub.io/dns-secondary/configure | `map(string)` | `{}` | no |
| <a name="input_constraints"></a> [constraints](#input\_constraints) | Juju constraints to apply for this application | `string` | `null` | no |
| <a name="input_model"></a> [model](#input\_model) | Reference to a `juju_model` resource | `string` | n/a | yes |
| <a name="input_revision"></a> [revision](#input\_revision) | Revision number of the charm | `number` | `null` | no |
| <a name="input_units"></a> [units](#input\_units) | Number of units to deploy | `number` | `1` | no |

## Outputs

| Name | Description |
|------|-------------|
| <a name="output_app_name"></a> [app\_name](#output\_app\_name) | Name of the deployed application |
| <a name="output_application"></a> [application](#output\_application) | The deployed application |
| <a name="output_provides"></a> [provides](#output\_provides) | Provided endpoints |
| <a name="output_requires"></a> [requires](#output\_requires) | Required endpoints |
<!-- END_TF_DOCS -->
