# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.

terraform {
  required_version = ">= 1.0"
  required_providers {
    juju = {
      source  = "juju/juju"
      version = "1.0.0"
    }
  }
}

# To import an existing model, run this first:
# terraform import 'module.dns.juju_model.dns' <model-uuid>

module "dns" {
  source = "../../terraform"

  model_name = var.model_name

  # All other variables will use their defaults from the module
  # You can override them here if needed:
  # bind = {
  #   units = 3
  # }
  # dns_secondary = {
  #   units = 2
  # }
  # dns_resolver = {
  #   units = 2
  # }
}
