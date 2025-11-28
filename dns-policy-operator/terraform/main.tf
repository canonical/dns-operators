# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.

resource "juju_application" "dns_policy" {
  name  = var.app_name
  model = var.model

  charm {
    name     = "dns-policy"
    base     = var.base
    channel  = var.channel
    revision = var.revision
  }

  config = var.config
  # NOTE: No units - this is a subordinate charm
  # NOTE: No constraints - subordinate charms inherit from principal
}
