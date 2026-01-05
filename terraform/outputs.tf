# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.

output "models" {
  description = "Map of models and deployed components"
  value = {
    product = {
      model_uuid = data.juju_model.dns.id
      components = {
        bind          = module.bind.application
        dns_secondary = module.dns_secondary.application
        dns_resolver  = module.dns_resolver.application
      }
    }
  }
}
