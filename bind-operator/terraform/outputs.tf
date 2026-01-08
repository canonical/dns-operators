# Copyright 2026 Canonical Ltd.
# See LICENSE file for licensing details.

output "app_name" {
  description = "Name of the deployed application"
  value       = juju_application.bind.name
}

output "application" {
  description = "The deployed application"
  value       = juju_application.bind
}

output "provides" {
  description = "Provided endpoints"
  value = {
    dns_authority = "dns-authority"
    dns_record    = "dns-record"
    dns_transfer  = "dns-transfer"
  }
}

output "requires" {
  description = "Required endpoints"
  value       = {}
}
