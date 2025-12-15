# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.

locals {
  config_model = lookup(var.model, "config", {})

  model_defaults = {
    name         = "machine"
    cloud_name   = "localhost"
    cloud_region = "localhost"
    constraints  = var.storage_constraint
  }

  model = merge(local.model_defaults, var.model)

  juju_provider = {
    proxy = var.proxy
  }

  bind = {
    name  = lookup(var.bind, "app_name", "bind")
    units = lookup(var.bind, "units", 2)
  }

  dns_secondary = {
    name  = lookup(var.dns_secondary, "app_name", "dns-secondary")
    units = lookup(var.dns_secondary, "units", 1)
  }

  dns_resolver = {
    name  = lookup(var.dns_resolver, "app_name", "dns-resolver")
    units = lookup(var.dns_resolver, "units", 1)
  }
}
