# Copyright 2026 Canonical Ltd.
# See LICENSE file for licensing details.

terraform {
  required_version = ">= 1.6"
  required_providers {
    juju = {
      source  = "juju/juju"
      version = ">= 1.0.0"
    }
  }
}

# This module uses a data source to reference an existing Juju model
# To find your model UUID, run: juju show-model <model-name>

module "dns" {
  source = "../../terraform"

  model_uuid = var.model_uuid

  # All other variables will use their defaults from locals.tf
  # You can override them here if needed:
  # bind = {
  #   units = 3
  #   channel = "latest/stable"
  # }
  # dns_secondary = {
  #   units = 2
  # }
  # dns_resolver = {
  #   units = 2
  # }
}
