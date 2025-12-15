# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.

# Product module variables

variable "model_name" {
  description = "Name of the juju model (required)"
  type        = string
}

variable "juju_controller" {
  description = "Controller connection information (not consumed directly by this module)"
  type        = map(string)
  default     = {}
}

variable "proxy" {
  description = "Proxy configuration (optional)"
  type        = map(string)
  default     = {}
}

variable "logging_config" {
  description = "Logging configuration"
  type        = string
  default     = ""
}

variable "bind" {
  description = "Configuration for the bind charm module"
  type = object({
    app_name    = optional(string, "bind")
    channel     = optional(string, "latest/edge")
    base        = optional(string, "ubuntu@22.04")
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
    channel     = optional(string, "latest/edge")
    base        = optional(string, "ubuntu@22.04")
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
    channel     = optional(string, "latest/edge")
    base        = optional(string, "ubuntu@22.04")
    config      = optional(map(string), {})
    constraints = optional(string, null)
    revision    = optional(number, null)
    units       = optional(number, 1)
  })
  default = {}
}

variable "model" {
  description = "Partial overrides for the model configuration."
  type        = any
  default     = {}
}

variable "constraints" {
  description = "Constraints for each application."
  type        = map(string)
  default     = {}
}

variable "config_model" {
  description = "Configuration for the juju model."
  type        = map(string)
  default = {
    juju-http-proxy  = "" # override or set via locals
    juju-https-proxy = "" # override or set via locals
    juju-no-proxy    = "127.0.0.1,localhost,::1,10.0.0.0/8,172.16.0.0/12,192.168.0.0/16,.canonical.com,.launchpad.net,.internal,.jujucharms.com,.ubuntu.com"
  }
}

variable "model_uuid" {
  description = "UUID of an existing juju_model to import (optional). Used with the import block to reuse an existing model instead of creating a new one. You can find it with `juju show-model <model-name>`. If not provided, a new model will be created."
  type        = string
  default     = ""
}

variable "storage_constraint" {
  description = "Storage constraint for the Juju model (e.g., 'root-disk-source=default'). Leave empty to use LXD's default storage pool."
  type        = string
  default     = ""
}
