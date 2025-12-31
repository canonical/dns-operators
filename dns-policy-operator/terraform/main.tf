# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.

resource "juju_application" "dns_policy" {
  name       = var.app_name
  model_uuid = var.model_uuid

  charm {
    name     = "dns-policy"
    base     = var.base
    channel  = var.channel
    revision = var.revision
  }

  config = var.config
  # NOTE: No units - this is a subordinate charm
  # NOTE: No constraints - subordinate charms inherit from principal

  dynamic "expose" {
    for_each = var.expose != null ? var.expose : []
    content {
      spaces    = expose.value.spaces
      cidrs     = expose.value.cidrs
      endpoints = expose.value.endpoints
    }
  }
}
