## Requirements

| Name | Version |
|------|---------|
| <a name="requirement_juju"></a> [juju](#requirement\_juju) | 1.0.0 |

## Providers

| Name | Version |
|------|---------|
| <a name="provider_juju"></a> [juju](#provider\_juju) | 1.0.0 |

## Modules

| Name | Source | Version |
|------|--------|---------|
| <a name="module_bind"></a> [bind](#module\_bind) | ../../bind-operator/terraform | n/a |
| <a name="module_dns_resolver"></a> [dns\_resolver](#module\_dns\_resolver) | ../../dns-resolver-operator/terraform | n/a |
| <a name="module_dns_secondary"></a> [dns\_secondary](#module\_dns\_secondary) | ../../dns-secondary-operator/terraform | n/a |

## Resources

| Name | Type |
|------|------|
| [juju_integration.bind_secondary_transfer](https://registry.terraform.io/providers/juju/juju/1.0.0/docs/resources/integration) | resource |
| [juju_integration.secondary_resolver_authority](https://registry.terraform.io/providers/juju/juju/1.0.0/docs/resources/integration) | resource |
| [juju_model.dns](https://registry.terraform.io/providers/juju/juju/1.0.0/docs/resources/model) | resource |

## Inputs

| Name | Description | Type | Default | Required |
|------|-------------|------|---------|:--------:|
| <a name="input_bind"></a> [bind](#input\_bind) | Configuration for the bind charm module | <pre>object({<br/>    app_name    = optional(string, "bind")<br/>    channel     = optional(string, "latest/edge")<br/>    base        = optional(string, "ubuntu@22.04")<br/>    config      = optional(map(string), {})<br/>    constraints = optional(string, null)<br/>    revision    = optional(number, null)<br/>    units       = optional(number, 2)<br/>  })</pre> | `{}` | no |
| <a name="input_config_model"></a> [config\_model](#input\_config\_model) | Configuration for the juju model. | `map(string)` | <pre>{<br/>  "juju-http-proxy": "",<br/>  "juju-https-proxy": "",<br/>  "juju-no-proxy": "127.0.0.1,localhost,::1,10.0.0.0/8,172.16.0.0/12,192.168.0.0/16,.canonical.com,.launchpad.net,.internal,.jujucharms.com,.ubuntu.com"<br/>}</pre> | no |
| <a name="input_constraints"></a> [constraints](#input\_constraints) | Constraints for each application. | `map(string)` | `{}` | no |
| <a name="input_dns_resolver"></a> [dns\_resolver](#input\_dns\_resolver) | Configuration for the dns-resolver charm module | <pre>object({<br/>    app_name    = optional(string, "dns-resolver")<br/>    channel     = optional(string, "latest/edge")<br/>    base        = optional(string, "ubuntu@22.04")<br/>    config      = optional(map(string), {})<br/>    constraints = optional(string, null)<br/>    revision    = optional(number, null)<br/>    units       = optional(number, 1)<br/>  })</pre> | `{}` | no |
| <a name="input_dns_secondary"></a> [dns\_secondary](#input\_dns\_secondary) | Configuration for the dns-secondary charm module | <pre>object({<br/>    app_name    = optional(string, "dns-secondary")<br/>    channel     = optional(string, "latest/edge")<br/>    base        = optional(string, "ubuntu@22.04")<br/>    config      = optional(map(string), {})<br/>    constraints = optional(string, null)<br/>    revision    = optional(number, null)<br/>    units       = optional(number, 1)<br/>  })</pre> | `{}` | no |
| <a name="input_juju_controller"></a> [juju\_controller](#input\_juju\_controller) | Controller connection information (not consumed directly by this module) | `map(string)` | `{}` | no |
| <a name="input_logging_config"></a> [logging\_config](#input\_logging\_config) | Logging configuration | `string` | `""` | no |
| <a name="input_model"></a> [model](#input\_model) | Partial overrides for the model configuration. | `any` | `{}` | no |
| <a name="input_model_name"></a> [model\_name](#input\_model\_name) | Name of the juju model (required) | `string` | n/a | yes |
| <a name="input_model_uuid"></a> [model\_uuid](#input\_model\_uuid) | UUID of an existing juju\_model to import (optional). Used with the import block to reuse an existing model instead of creating a new one. You can find it with `juju show-model <model-name>`. If not provided, a new model will be created. | `string` | `""` | no |
| <a name="input_proxy"></a> [proxy](#input\_proxy) | Proxy configuration (optional) | `map(string)` | `{}` | no |
| <a name="input_storage_constraint"></a> [storage\_constraint](#input\_storage\_constraint) | Storage constraint for the Juju model (e.g., 'root-disk-source=default'). Leave empty to use LXD's default storage pool. | `string` | `""` | no |

## Outputs

| Name | Description |
|------|-------------|
| <a name="output_metadata"></a> [metadata](#output\_metadata) | Deployment metadata |
| <a name="output_models"></a> [models](#output\_models) | Map of models and deployed components |
| <a name="output_provides"></a> [provides](#output\_provides) | Map of provided endpoints across all components |
| <a name="output_requires"></a> [requires](#output\_requires) | Map of required endpoints across all components |
