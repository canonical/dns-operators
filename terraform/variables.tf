# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.

# Product module variables

variable "model_uuid" {
  description = "UUID of the juju model (find with 'juju show-model <model-name>')"
  type        = string
}

variable "bind" {
  description = "Configuration for the bind charm module"
  type = object({
    app_name    = optional(string, "bind")
    channel     = optional(string)
    base        = optional(string)
    config      = optional(map(string), {})
    constraints = optional(string, null)
    revision    = optional(number, null)
    units       = optional(number, 2)
  })
  default = {}
}

variable "dns_secondary" {
  description = "Configuration for the dns-secondary charm module"
  type = object({
    app_name    = optional(string, "dns-secondary")
    channel     = optional(string)
    base        = optional(string)
    config      = optional(map(string), {})
    constraints = optional(string, null)
    revision    = optional(number, null)
    units       = optional(number, 1)
  })
  default = {}
}

variable "dns_resolver" {
  description = "Configuration for the dns-resolver charm module"
  type = object({
    app_name    = optional(string, "dns-resolver")
    channel     = optional(string)
    base        = optional(string)
    config      = optional(map(string), {})
    constraints = optional(string, null)
    revision    = optional(number, null)
    units       = optional(number, 1)
  })
  default = {}
}
