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
    channel    = "latest/edge"
    # renovate: depName="dns-resolver"
    revision = 1
  }

  assert {
    condition     = output.app_name == "dns-resolver"
    error_message = "dns-resolver app_name did not match expected"
  }
}
