# Copyright 2026 Canonical Ltd.
# See LICENSE file for licensing details.

resource "juju_application" "dns_integrator" {
  name       = var.app_name
  model_uuid = var.model_uuid

  charm {
    name     = "dns-integrator"
    base     = var.base
    channel  = var.channel
    revision = var.revision
  }

  config      = var.config
  constraints = var.constraints
  units       = var.units

  dynamic "expose" {
    for_each = var.expose != null ? var.expose : []
    content {
      spaces    = expose.value.spaces
      cidrs     = expose.value.cidrs
      endpoints = expose.value.endpoints
    }
  }
}
