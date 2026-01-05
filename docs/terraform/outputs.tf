# Copyright 2026 Canonical Ltd.
# See LICENSE file for licensing details.

output "models" {
  description = "Map of models and deployed components"
  value       = module.dns.models
}

output "metadata" {
  description = "Deployment metadata"
  value       = module.dns.metadata
}

output "provides" {
  description = "Map of provided endpoints across all components"
  value       = module.dns.provides
}

output "requires" {
  description = "Map of required endpoints across all components"
  value       = module.dns.requires
}
