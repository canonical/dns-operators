# Copyright 2026 Canonical Ltd.
# See LICENSE file for licensing details.

output "models" {
  description = "Map of models and deployed components"
  value       = module.dns.models
}
