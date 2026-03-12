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
    # renovate: depName="dns-policy"
    revision = 2
  }

  assert {
    condition     = output.app_name == "dns-policy"
    error_message = "dns-policy app_name did not match expected"
  }
}
