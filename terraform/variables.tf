# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.

# Product module variables

variable "model_name" {
  description = "Name of the juju model (required)"
  type        = string
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
  type = object({
    cloud_name   = optional(string, "localhost")
    cloud_region = optional(string, "localhost")
    model_name   = optional(string, "machine")
    constraints  = optional(string, "")
    config = optional(map(string), {
      juju-http-proxy  = "" # override or set via locals
      juju-https-proxy = "" # override or set via locals
      juju-no-proxy    = "127.0.0.1,localhost,::1,10.0.0.0/8,172.16.0.0/12,192.168.0.0/16,.canonical.com,.launchpad.net,.internal,.jujucharms.com,.ubuntu.com"
    })
  })
  default = {}
}
