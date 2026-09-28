# Copyright 2026 Canonical Ltd.
# See LICENSE file for licensing details.

"""Define models."""

import uuid

from django.contrib.auth.models import User
from django.db import models
from django.db.models import Q
from django.utils import timezone

from .domains import normalize_domain, validate_domain


class Rule(models.Model):
    """Rule automatically approving or denying the pending record requests.

    A rule only applies to the record requests left pending, i.e. the ones no reviewer
    has approved or denied, and whose domain name is the domain of the rule or one of its
    subdomains. The enabled rules are evaluated in ascending priority order
    and the first rule matching a pending record request decides whether it is
    automatically approved or denied. A reviewer can always override that decision by
    manually approving or denying the record request.
    """

    class Kind(models.TextChoices):
        """Kinds of rules, each one being a matching logic."""

        ACME_CHALLENGE = 'acme_challenge', (
            'ACME challenge TXT record of a domain owned by the same requirer'
        )

    class Action(models.TextChoices):
        """Actions applied to the record requests matched by a rule.

        The values are the statuses the matched record requests get.
        """

        APPROVE = 'approved', 'Approve'
        DENY = 'denied', 'Deny'

    name = models.CharField(max_length=255, unique=True)
    kind = models.CharField(max_length=50, choices=Kind.choices)
    domain = models.CharField(
        max_length=253,
        validators=[validate_domain],
        help_text='The rule only applies to the records of this domain and its subdomains.',
    )
    action = models.CharField(max_length=50, choices=Action.choices, default=Action.APPROVE)
    enabled = models.BooleanField(default=True)
    priority = models.IntegerField(
        default=0, help_text='Rules with a lower priority are evaluated first.'
    )
    description = models.TextField(blank=True, default='')
    created_at = models.DateTimeField(default=timezone.now)
    last_modified_at = models.DateTimeField(auto_now=True)

    class Meta:
        """Define meta of the model."""

        ordering = ['priority', 'id']

    def clean(self):
        """Normalize the rule."""
        super().clean()
        self.domain = normalize_domain(self.domain)

    def save(self, *args, **kwargs):
        """Save the rule, with a normalized domain."""
        self.domain = normalize_domain(self.domain)
        super().save(*args, **kwargs)

    def __str__(self):
        """Rule model string representation."""
        return self.name


class RecordRequestQuerySet(models.QuerySet):
    """Record request queryset."""

    def with_effective_status(self, *statuses):
        """Filter the record requests by effective status.

        The effective status of a pending record request decided by a rule is the
        status given by that rule.
        """
        pending = RecordRequest.Status.PENDING
        query = Q(status__in=[s for s in statuses if s != pending])
        query |= Q(status=pending, rule__action__in=statuses)
        if pending in statuses:
            query |= Q(status=pending, rule__isnull=True)
        return self.filter(query)


class RecordRequest(models.Model):
    """Record request model."""

    class Status(models.TextChoices):
        """Record request statuses.

        A record request, when received, passes some checks to see if it's invalid.
        If yes, its status is INVALID.
        If everything went alright, it receives the PENDING status.
        A reviewer can then deny or approve it, marking it DENIED or APPROVED.
        An approved record request is then sent to bind-operator which may add it to its config.
        If it does not get published it is marked as FAILED, if it does get published, is is PUBLISHED.
        """
        APPROVED = 'approved'
        DENIED = 'denied'
        FAILED = 'failed'
        INVALID = 'invalid'
        PENDING = 'pending'
        PUBLISHED = 'published'

    uuid = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    domain = models.CharField(max_length=255)
    host_label = models.CharField(max_length=255)
    ttl = models.IntegerField(null=True)
    record_type = models.CharField(max_length=10)
    record_data = models.CharField(max_length=255)
    active = models.BooleanField(default=False)
    requirer_id = models.CharField(max_length=255, null=True)
    status = models.CharField(max_length=50, choices=Status.choices)
    status_reason = models.CharField(max_length=255, null=True)
    reviewer = models.ForeignKey(User, null=True, on_delete=models.SET_NULL)
    created_at = models.DateTimeField(default=timezone.now)
    last_modified_at = models.DateTimeField(default=timezone.now)
    # Rule that automatically decided the record request, only set while it is pending
    rule = models.ForeignKey(
        Rule, null=True, blank=True, on_delete=models.SET_NULL, related_name='record_requests'
    )

    objects = RecordRequestQuerySet.as_manager()

    @property
    def effective_status(self):
        """Status of the record request, including the automatic decision of the rules."""
        if self.status == self.Status.PENDING and self.rule_id is not None:
            return self.rule.action
        return self.status

    def __str__(self):
        """Record request model string representation."""
        return f"[{self.effective_status}] {self.host_label} {self.domain} {self.ttl} {self.record_type} {self.record_data}"


class DdnsAllocation(models.Model):
    """Domain automatically allocated to a dns_record relation.

    The domain is a random label under the parent domain requested for the relation.
    A relation gets one allocation per parent domain it was requested under.

    An allocation is never removed and a domain is never reused, so a domain that was
    once allocated to a relation can never be handed to a different one.

    A relation is identified by the pair (instance, requirer_id), the requirer id being
    the id of the relation. The instance is the identifier of the charm the relation
    belongs to: relation ids are only unique within a single charm deployment, and
    start over from scratch in a deployment
    restored from a backup of this database. Keying the allocations on the instance too
    keeps them from being handed to the unrelated relations of such a deployment.
    """

    instance = models.UUIDField()
    requirer_id = models.CharField(max_length=255)
    domain = models.CharField(max_length=253, unique=True)
    created_at = models.DateTimeField(default=timezone.now)

    @property
    def parent(self):
        """Parent domain the domain was allocated under."""
        return self.domain.partition(".")[2]

    def __str__(self):
        """Ddns allocation model string representation."""
        return f"{self.domain} (instance {self.instance}, requirer {self.requirer_id})"
