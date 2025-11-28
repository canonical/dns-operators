# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.

output "app_name" {
  description = "Name of the deployed application"
  value       = juju_application.dns_policy.name
}

output "application" {
  description = "The deployed application"
  value       = juju_application.dns_policy
}

output "provides" {
  description = "Provided endpoints"
  value = {
    dns_record_provider = "dns-record-provider"
  }
}

output "requires" {
  description = "Required endpoints"
  value = {
    database            = "database"
    dns_record_requirer = "dns-record-requirer"
  }
}
