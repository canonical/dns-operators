# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.

variable "app_name" {
  description = "Name of the application in the Juju model"
  type        = string
  default     = "dns-policy"
}

variable "base" {
  description = "The operating system on which to deploy"
  type        = string
  default     = "ubuntu@22.04"
}

variable "channel" {
  description = "The channel to use when deploying a charm"
  type        = string
  default     = "latest/edge"
}

variable "config" {
  description = "Application configuration. Details in https://charmhub.io/dns-policy/configure"
  type        = map(string)
  default     = {}
}

variable "model" {
  description = "Reference to a `juju_model` resource"
  type        = string
}

variable "revision" {
  description = "Revision number of the charm"
  type        = number
  default     = null
}
