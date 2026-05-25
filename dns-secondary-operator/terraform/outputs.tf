# Copyright 2026 Canonical Ltd.
# See LICENSE file for licensing details.

output "app_name" {
  description = "Name of the deployed application"
  value       = juju_application.dns_secondary.name
}

output "application" {
  description = "The deployed application"
  value       = juju_application.dns_secondary
}

output "provides" {
  description = "Provided endpoints"
  value = {
    dns_authority = "dns-authority"
  }
}

output "requires" {
  description = "Required endpoints"
  value = {
    bind_certificates = "bind-certificates"
    dns_transfer      = "dns-transfer"
  }
}
