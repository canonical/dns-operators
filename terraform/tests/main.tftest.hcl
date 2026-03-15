# Copyright 2026 Canonical Ltd.
# See LICENSE file for licensing details.

run "setup_tests" {
  module {
    source = "./tests/setup"
  }
}

run "basic_deploy" {
  variables {
    model_uuid = run.setup_tests.model_uuid
    bind = {
      channel = "latest/edge"
      # renovate: depName="bind"
      revision = 80
    }
    dns_secondary = {
      channel = "latest/edge"
      # renovate: depName="dns-secondary"
      revision = 2
    }
    dns_resolver = {
      channel = "latest/edge"
      # renovate: depName="dns-resolver"
      revision = 1
    }
  }

  assert {
    condition     = output.models.product.components.bind.name == "bind"
    error_message = "bind app_name did not match expected"
  }
}
