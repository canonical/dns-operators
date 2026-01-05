# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.

# Juju model
data "juju_model" "dns" {
  uuid = var.model_uuid
}

# Bind charm module
module "bind" {
  source = "../bind-operator/terraform"

  app_name    = var.bind.app_name
  channel     = coalesce(var.bind.channel, local.default_channel)
  base        = coalesce(var.bind.base, local.default_base)
  config      = var.bind.config
  constraints = var.bind.constraints
  revision    = var.bind.revision
  units       = var.bind.units
  model_uuid  = data.juju_model.dns.id
}

# DNS Secondary charm module
module "dns_secondary" {
  source = "../dns-secondary-operator/terraform"

  app_name    = var.dns_secondary.app_name
  channel     = coalesce(var.dns_secondary.channel, local.default_channel)
  base        = coalesce(var.dns_secondary.base, local.default_base)
  config      = var.dns_secondary.config
  constraints = var.dns_secondary.constraints
  revision    = var.dns_secondary.revision
  units       = var.dns_secondary.units
  model_uuid  = data.juju_model.dns.id
}

# DNS Resolver charm module
module "dns_resolver" {
  source = "../dns-resolver-operator/terraform"

  app_name    = var.dns_resolver.app_name
  channel     = coalesce(var.dns_resolver.channel, local.default_channel)
  base        = coalesce(var.dns_resolver.base, local.default_base)
  config      = var.dns_resolver.config
  constraints = var.dns_resolver.constraints
  revision    = var.dns_resolver.revision
  units       = var.dns_resolver.units
  model_uuid  = data.juju_model.dns.id
}

# Integrations
resource "juju_integration" "bind_secondary_transfer" {
  model_uuid = data.juju_model.dns.id
  application {
    name     = module.bind.application.name
    endpoint = module.bind.provides["dns_transfer"]
  }

  application {
    name     = module.dns_secondary.application.name
    endpoint = module.dns_secondary.requires["dns_transfer"]
  }
}

resource "juju_integration" "secondary_resolver_authority" {
  model_uuid = data.juju_model.dns.id
  application {
    name     = module.dns_secondary.application.name
    endpoint = module.dns_secondary.provides["dns_authority"]
  }

  application {
    name     = module.dns_resolver.application.name
    endpoint = module.dns_resolver.requires["dns_authority"]
  }
}
