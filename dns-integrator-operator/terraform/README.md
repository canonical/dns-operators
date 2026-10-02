## Requirements

| Name | Version |
|------|---------|
| <a name="requirement_terraform"></a> [terraform](#requirement\_terraform) | >= 1.6 |
| <a name="requirement_juju"></a> [juju](#requirement\_juju) | 1.0.0 |

## Providers

| Name | Version |
|------|---------|
| <a name="provider_juju"></a> [juju](#provider\_juju) | 1.0.0 |

## Modules

No modules.

## Resources

| Name | Type |
|------|------|
| [juju_application.dns_integrator](https://registry.terraform.io/providers/juju/juju/1.0.0/docs/resources/application) | resource |

## Inputs

| Name | Description | Type | Default | Required |
|------|-------------|------|---------|:--------:|
| <a name="input_app_name"></a> [app\_name](#input\_app\_name) | Name of the application in the Juju model | `string` | `"dns-integrator"` | no |
| <a name="input_base"></a> [base](#input\_base) | The operating system on which to deploy | `string` | `"ubuntu@22.04"` | no |
| <a name="input_channel"></a> [channel](#input\_channel) | The channel to use when deploying a charm | `string` | `"latest/edge"` | no |
| <a name="input_config"></a> [config](#input\_config) | Application configuration. Details in https://charmhub.io/dns-integrator/configure | `map(string)` | `{}` | no |
| <a name="input_constraints"></a> [constraints](#input\_constraints) | Juju constraints to apply for this application | `string` | `null` | no |
| <a name="input_endpoint_bindings"></a> [endpoint\_bindings](#input\_endpoint\_bindings) | Map of endpoint bindings | `map(string)` | `{}` | no |
| <a name="input_expose"></a> [expose](#input\_expose) | Expose configuration | <pre>list(object({<br/>    spaces    = optional(list(string))<br/>    cidrs     = optional(list(string))<br/>    endpoints = optional(list(string))<br/>  }))</pre> | `null` | no |
| <a name="input_expose_endpoints"></a> [expose\_endpoints](#input\_expose\_endpoints) | List of endpoints to expose as offers | `list(string)` | `[]` | no |
| <a name="input_machines"></a> [machines](#input\_machines) | List of machine IDs to deploy to | `set(string)` | `[]` | no |
| <a name="input_model_uuid"></a> [model\_uuid](#input\_model\_uuid) | Reference to a `juju_model` resource UUID | `string` | n/a | yes |
| <a name="input_resources"></a> [resources](#input\_resources) | Resources to use with the charm | `map(string)` | `{}` | no |
| <a name="input_revision"></a> [revision](#input\_revision) | Revision number of the charm | `number` | `null` | no |
| <a name="input_storage_directives"></a> [storage\_directives](#input\_storage\_directives) | Storage directives for the application | `map(string)` | `{}` | no |
| <a name="input_units"></a> [units](#input\_units) | Number of units to deploy | `number` | `1` | no |

## Outputs

| Name | Description |
|------|-------------|
| <a name="output_app_name"></a> [app\_name](#output\_app\_name) | Name of the deployed application |
| <a name="output_application"></a> [application](#output\_application) | The deployed application |
| <a name="output_provides"></a> [provides](#output\_provides) | Provided endpoints |
| <a name="output_requires"></a> [requires](#output\_requires) | Required endpoints |
