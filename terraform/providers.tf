# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.

# Minimal provider block so Terraform knows this module requires the juju provider.
# The provider will read authentication and controller configuration from the
# environment or from a provider block in the root module. This file is optional
# and can be removed if provider configuration is supplied by the caller.

provider "juju" {}
