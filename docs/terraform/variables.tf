# Copyright 2026 Canonical Ltd.
# See LICENSE file for licensing details.

variable "model_uuid" {
  description = "UUID of the Juju model (find with 'juju show-model <model-name>')"
  type        = string
}
