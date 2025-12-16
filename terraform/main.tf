# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.

# Juju model

resource "juju_model" "dns" {
  name = var.model_name

  cloud {
    name   = var.model.cloud_name
    region = var.model.cloud_region
  }

  config      = var.model.config
  constraints = var.model.constraints

  lifecycle {
    prevent_destroy = true
  }
}

# Bind charm module
module "bind" {
  source = "../bind-operator/terraform"

  app_name    = lookup(var.bind, "app_name", "bind")
  channel     = lookup(var.bind, "channel", "latest/edge")
  base        = lookup(var.bind, "base", "ubuntu@22.04")
  config      = lookup(var.bind, "config", {})
  constraints = lookup(var.bind, "constraints", null)
  revision    = lookup(var.bind, "revision", null)
  units       = lookup(var.bind, "units", 2)
  model_uuid  = juju_model.dns.id
}

# DNS Secondary charm module
module "dns_secondary" {
  source = "../dns-secondary-operator/terraform"

  app_name    = lookup(var.dns_secondary, "app_name", "dns-secondary")
  channel     = lookup(var.dns_secondary, "channel", "latest/edge")
  base        = lookup(var.dns_secondary, "base", "ubuntu@22.04")
  config      = lookup(var.dns_secondary, "config", {})
  constraints = lookup(var.dns_secondary, "constraints", null)
  revision    = lookup(var.dns_secondary, "revision", null)
  units       = lookup(var.dns_secondary, "units", 1)
  model_uuid  = juju_model.dns.id
}

# DNS Resolver charm module
module "dns_resolver" {
  source = "../dns-resolver-operator/terraform"

  app_name    = lookup(var.dns_resolver, "app_name", "dns-resolver")
  channel     = lookup(var.dns_resolver, "channel", "latest/edge")
  base        = lookup(var.dns_resolver, "base", "ubuntu@22.04")
  config      = lookup(var.dns_resolver, "config", {})
  constraints = lookup(var.dns_resolver, "constraints", null)
  revision    = lookup(var.dns_resolver, "revision", null)
  units       = lookup(var.dns_resolver, "units", 1)
  model_uuid  = juju_model.dns.id
}

# Integrations
resource "juju_integration" "bind_secondary_transfer" {
  model_uuid = juju_model.dns.id
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
  model_uuid = juju_model.dns.id
  application {
    name     = module.dns_secondary.application.name
    endpoint = module.dns_secondary.provides["dns_authority"]
  }

  application {
    name     = module.dns_resolver.application.name
    endpoint = module.dns_resolver.requires["dns_authority"]
  }
}
