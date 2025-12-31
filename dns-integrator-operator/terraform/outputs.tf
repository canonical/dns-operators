# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.

output "app_name" {
  description = "Name of the deployed application"
  value       = juju_application.dns_integrator.name
}

output "application" {
  description = "The deployed application"
  value       = juju_application.dns_integrator
}

output "provides" {
  description = "Provided endpoints"
  value       = {}
}

output "requires" {
  description = "Required endpoints"
  value = {
    dns_record = "dns-record"
  }
}
