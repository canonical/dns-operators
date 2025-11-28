# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.

variable "app_name" {
  description = "Name of the application in the Juju model"
  type        = string
  default     = "bind"
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
  description = "Application configuration. Details in https://charmhub.io/bind/configure"
  type        = map(string)
  default     = {}
}

variable "constraints" {
  description = "Juju constraints to apply for this application"
  type        = string
  default     = null
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

variable "units" {
  description = "Number of units to deploy"
  type        = number
  default     = 1
}
