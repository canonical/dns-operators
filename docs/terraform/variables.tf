# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.

variable "model_name" {
  description = "Name of the Juju model (will import if exists, create if not)"
  type        = string
}
