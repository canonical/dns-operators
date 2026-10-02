## Requirements

| Name | Version |
|------|---------|
| <a name="requirement_terraform"></a> [terraform](#requirement\_terraform) | >= 1.6 |
| <a name="requirement_juju"></a> [juju](#requirement\_juju) | >= 1.0.0 |

## Providers

| Name | Version |
|------|---------|
| <a name="provider_juju"></a> [juju](#provider\_juju) | >= 1.0.0 |

## Modules

| Name | Source | Version |
|------|--------|---------|
| <a name="module_bind"></a> [bind](#module\_bind) | ../bind-operator/terraform | n/a |
| <a name="module_dns_resolver"></a> [dns\_resolver](#module\_dns\_resolver) | ../dns-resolver-operator/terraform | n/a |
| <a name="module_dns_secondary"></a> [dns\_secondary](#module\_dns\_secondary) | ../dns-secondary-operator/terraform | n/a |

## Resources

| Name | Type |
|------|------|
| [juju_integration.bind_secondary_transfer](https://registry.terraform.io/providers/juju/juju/latest/docs/resources/integration) | resource |
| [juju_integration.secondary_resolver_authority](https://registry.terraform.io/providers/juju/juju/latest/docs/resources/integration) | resource |
| [juju_model.dns](https://registry.terraform.io/providers/juju/juju/latest/docs/data-sources/model) | data source |

## Inputs

| Name | Description | Type | Default | Required |
|------|-------------|------|---------|:--------:|
| <a name="input_bind"></a> [bind](#input\_bind) | Configuration for the bind charm module | <pre>object({<br/>    app_name    = optional(string, "bind")<br/>    channel     = optional(string)<br/>    base        = optional(string)<br/>    config      = optional(map(string), {})<br/>    constraints = optional(string, null)<br/>    revision    = optional(number, null)<br/>    units       = optional(number, 2)<br/>  })</pre> | `{}` | no |
| <a name="input_dns_resolver"></a> [dns\_resolver](#input\_dns\_resolver) | Configuration for the dns-resolver charm module | <pre>object({<br/>    app_name    = optional(string, "dns-resolver")<br/>    channel     = optional(string)<br/>    base        = optional(string)<br/>    config      = optional(map(string), {})<br/>    constraints = optional(string, null)<br/>    revision    = optional(number, null)<br/>    units       = optional(number, 1)<br/>  })</pre> | `{}` | no |
| <a name="input_dns_secondary"></a> [dns\_secondary](#input\_dns\_secondary) | Configuration for the dns-secondary charm module | <pre>object({<br/>    app_name    = optional(string, "dns-secondary")<br/>    channel     = optional(string)<br/>    base        = optional(string)<br/>    config      = optional(map(string), {})<br/>    constraints = optional(string, null)<br/>    revision    = optional(number, null)<br/>    units       = optional(number, 1)<br/>  })</pre> | `{}` | no |
| <a name="input_model_uuid"></a> [model\_uuid](#input\_model\_uuid) | UUID of the juju model (find with 'juju show-model &lt;model-name&gt;') | `string` | n/a | yes |

## Outputs

| Name | Description |
|------|-------------|
| <a name="output_models"></a> [models](#output\_models) | Map of models and deployed components |

## Locals

| Name | Description | Default |
|------|-------------|---------|
| default_channel | Default charm channel | "latest/edge" |
| default_base | Default Ubuntu base | "ubuntu@22.04" |

