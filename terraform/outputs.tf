# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.

output "models" {
  description = "Map of models and deployed components"
  value = {
    product = {
      model_uuid = juju_model.dns.id
      components = {
        bind          = module.bind.application
        dns_secondary = module.dns_secondary.application
        dns_resolver  = module.dns_resolver.application
      }
    }
  }
}

output "metadata" {
  description = "Deployment metadata"
  value = {
    version     = "0.1.0"
    deployed_at = timestamp()
    updated_at  = timestamp()
  }
}

output "provides" {
  description = "Map of provided endpoints across all components"
  value = {
    bind_dns_transfer       = module.bind.provides["dns_transfer"]
    secondary_dns_authority = module.dns_secondary.provides["dns_authority"]
  }
}

output "requires" {
  description = "Map of required endpoints across all components"
  value = {
    secondary_dns_transfer = module.dns_secondary.requires["dns_transfer"]
    resolver_dns_authority = module.dns_resolver.requires["dns_authority"]
  }
}
