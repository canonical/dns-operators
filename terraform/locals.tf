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
}
