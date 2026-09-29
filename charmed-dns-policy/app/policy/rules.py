# Copyright 2026 Canonical Ltd.
# See LICENSE file for licensing details.

"""Evaluation of the rules automatically approving or denying the record requests."""

from collections import defaultdict

from django.db import transaction

from .domains import fqdn, is_within, normalize_domain
from .models import DdnsAllocation, RecordRequest, Rule

ACME_CHALLENGE_LABEL = "_acme-challenge"
ADDRESS_RECORD_TYPES = ("A", "AAAA")
# Statuses of the record requests that were approved, whether published yet or not
APPROVED_STATUSES = (
    RecordRequest.Status.APPROVED,
    RecordRequest.Status.FAILED,
    RecordRequest.Status.PUBLISHED,
)


class EvaluationContext:
    """State of the record requests and allocations the rules are evaluated against."""

    def __init__(self, record_requests, decisions, rules_by_id, allocations):
        """Build the context.

        Args:
            record_requests: every record request.
            decisions: id of the rule currently deciding each pending record request,
                by record request uuid.
            rules_by_id: the enabled rules, by id.
            allocations: (requirer id, domain) pairs of the automatically allocated
                domains.
        """
        self.address_names = set()
        for record_request in record_requests:
            if record_request.record_type.upper() not in ADDRESS_RECORD_TYPES:
                continue
            if not record_request.requirer_id:
                continue
            status = record_request.status
            if status == RecordRequest.Status.PENDING:
                rule = rules_by_id.get(decisions.get(record_request.uuid))
                status = rule.action if rule is not None else status
            if status in APPROVED_STATUSES:
                self.address_names.add(
                    (
                        record_request.requirer_id,
                        fqdn(record_request.host_label, record_request.domain),
                    )
                )

        self.ddns_domains = defaultdict(list)
        for requirer_id, domain in allocations:
            self.ddns_domains[requirer_id].append(normalize_domain(domain))

    def has_approved_address(self, requirer_id, name):
        """Check whether a requirer has an approved A or AAAA record for a domain."""
        return (requirer_id, name) in self.address_names

    def has_ddns_domain(self, requirer_id, name):
        """Check whether a domain resolves through a domain allocated to a requirer.

        An allocated domain comes with a wildcard record, so it covers its subdomains.
        """
        return any(is_within(name, domain) for domain in self.ddns_domains.get(requirer_id, ()))


def matches_acme_challenge(record_request, context):
    """Match the ACME challenge TXT records of a domain owned by the same requirer.

    The domain is owned by the requirer when it has an approved A or AAAA record for it,
    or when it is, or is under, a domain automatically allocated to it.
    """
    if record_request.record_type.upper() != "TXT" or not record_request.requirer_id:
        return False
    label, _, name = fqdn(record_request.host_label, record_request.domain).partition(".")
    if label != ACME_CHALLENGE_LABEL or not name:
        return False
    return context.has_approved_address(
        record_request.requirer_id, name
    ) or context.has_ddns_domain(record_request.requirer_id, name)


MATCHERS = {
    Rule.Kind.ACME_CHALLENGE: matches_acme_challenge,
}


def decide(record_request, rules, context):
    """Get the first rule matching a pending record request, if any.

    A rule only applies to the record requests of its domain and its subdomains.
    """
    name = fqdn(record_request.host_label, record_request.domain)
    for rule in rules:
        if not is_within(name, normalize_domain(rule.domain)):
            continue
        matcher = MATCHERS.get(rule.kind)
        if matcher is not None and matcher(record_request, context):
            return rule
    return None


def evaluate_rules():
    """Evaluate the rules against every pending record request.

    The record requests that are not pending anymore are left to their reviewers, and
    any automatic decision is dropped from them.

    A rule may depend on the decision taken for other record requests, e.g. an ACME
    challenge depends on the approval of the A record of its domain. The decisions are
    therefore evaluated again until they no longer change.
    """
    with transaction.atomic():
        RecordRequest.objects.exclude(status=RecordRequest.Status.PENDING).filter(
            rule__isnull=False
        ).update(rule=None)

        rules = list(Rule.objects.filter(enabled=True).order_by("priority", "id"))
        rules_by_id = {rule.id: rule for rule in rules}
        record_requests = list(RecordRequest.objects.all())
        pending = [r for r in record_requests if r.status == RecordRequest.Status.PENDING]
        allocations = list(DdnsAllocation.objects.values_list("requirer_id", "domain"))

        decisions = {record_request.uuid: None for record_request in pending}
        if rules:
            # Bounded, should the decisions of some rules never settle
            for _ in range(len(pending) + 1):
                context = EvaluationContext(record_requests, decisions, rules_by_id, allocations)
                new_decisions = {}
                for record_request in pending:
                    rule = decide(record_request, rules, context)
                    new_decisions[record_request.uuid] = rule.id if rule is not None else None
                if new_decisions == decisions:
                    break
                decisions = new_decisions

        changes = defaultdict(list)
        for record_request in pending:
            if record_request.rule_id != decisions[record_request.uuid]:
                changes[decisions[record_request.uuid]].append(record_request.uuid)
        for rule_id, uuids in changes.items():
            RecordRequest.objects.filter(
                uuid__in=uuids, status=RecordRequest.Status.PENDING
            ).update(rule_id=rule_id)
