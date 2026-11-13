# Copyright 2026 Canonical Ltd.
# See LICENSE file for licensing details.

"""Evaluate the rules again whenever what they depend on changes."""

from django.db.models.signals import post_delete, post_save
from django.dispatch import receiver

from .models import DdnsAllocation, Rule
from .rules import evaluate_rules


@receiver(post_save, sender=Rule, dispatch_uid="policy_rule_saved")
@receiver(post_delete, sender=Rule, dispatch_uid="policy_rule_deleted")
@receiver(post_save, sender=DdnsAllocation, dispatch_uid="policy_ddns_allocation_saved")
def reevaluate_rules(sender, **kwargs):
    """Evaluate the rules again against every pending record request."""
    evaluate_rules()
