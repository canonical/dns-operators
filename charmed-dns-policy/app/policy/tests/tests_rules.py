# Copyright 2026 Canonical Ltd.
# See LICENSE file for licensing details.

"""Test the rules automatically approving or denying the record requests."""

import uuid

from django.contrib import admin
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.test import RequestFactory, TestCase
from django.urls import reverse
from rest_framework.test import APITestCase

from policy import ddns, rules
from policy.admin import RecordRequestAdmin, approve, deny, reset_to_pending
from policy.models import RecordRequest, Rule
from policy.rules import evaluate_rules

Status = RecordRequest.Status

INSTANCE = uuid.UUID('8ad9f1e2-0c2a-4f8e-9a2b-3b6d5f7c1e40')
# Another charm installation, e.g. one restored from a backup of the database
OTHER_INSTANCE = uuid.UUID('0c2a4f8e-9a2b-4b6d-8f7c-1e408ad9f1e2')


def create_record_request(
    host_label,
    domain,
    record_type,
    record_data,
    requirer_id='1',
    status=Status.PENDING,
    instance=INSTANCE,
):
    """Create a record request."""
    return RecordRequest.objects.create(
        host_label=host_label,
        domain=domain,
        ttl=600,
        record_type=record_type,
        record_data=record_data,
        requirer_id=requirer_id,
        instance=instance,
        status=status,
    )


def acme_challenge(
    host_label='_acme-challenge.www', domain='example.com', requirer_id='1', instance=INSTANCE
):
    """Create a pending ACME challenge TXT record request."""
    return create_record_request(
        host_label, domain, 'TXT', 'challenge', requirer_id, instance=instance
    )


def create_rule(name='ACME challenge', domain='example.com', **kwargs):
    """Create an ACME challenge rule."""
    return Rule.objects.create(
        name=name, kind=Rule.Kind.ACME_CHALLENGE, domain=domain, **kwargs
    )


class TestNoRuleByDefault(TestCase):
    """Test that the rules are left to the operators."""

    def test_no_rule_by_default(self):
        """Test that no rule exists, so nothing is decided automatically."""
        self.assertFalse(Rule.objects.exists())
        create_record_request('www', 'example.com', 'A', '10.0.0.1', status=Status.APPROVED)
        challenge = acme_challenge()
        evaluate_rules()
        challenge.refresh_from_db()
        self.assertIsNone(challenge.rule)


class RulesTestCase(TestCase):
    """Base test case, with an ACME challenge rule for example.com."""

    def setUp(self):
        """Set up."""
        self.rule = create_rule()

    def assert_decided(self, record_request, rule):
        """Assert the rule deciding a record request."""
        record_request.refresh_from_db()
        self.assertEqual(record_request.rule_id, rule.id if rule is not None else None)


class TestAcmeChallengeRule(RulesTestCase):
    """Test the ACME challenge rule."""

    def test_approved_a_record_of_the_same_requirer(self):
        """Test that the challenge of a domain with an approved A record is approved."""
        create_record_request('www', 'example.com', 'A', '10.0.0.1', status=Status.APPROVED)
        challenge = acme_challenge()
        evaluate_rules()
        self.assert_decided(challenge, self.rule)
        self.assertEqual(challenge.status, Status.PENDING)
        self.assertEqual(challenge.effective_status, Status.APPROVED)

    def test_approved_aaaa_record_of_the_same_requirer(self):
        """Test that the challenge of a domain with an approved AAAA record is approved."""
        create_record_request('www', 'example.com', 'AAAA', '::1', status=Status.PUBLISHED)
        challenge = acme_challenge(host_label='_acme-challenge', domain='www.example.com.')
        evaluate_rules()
        self.assert_decided(challenge, self.rule)

    def test_a_record_of_another_requirer(self):
        """Test that the A record of another requirer is not enough."""
        create_record_request(
            'www', 'example.com', 'A', '10.0.0.1', requirer_id='2', status=Status.APPROVED
        )
        challenge = acme_challenge()
        evaluate_rules()
        self.assert_decided(challenge, None)

    def test_a_record_of_another_instance(self):
        """Test that the A record of the same requirer id of another instance is not enough."""
        create_record_request(
            'www', 'example.com', 'A', '10.0.0.1', status=Status.APPROVED,
            instance=OTHER_INSTANCE,
        )
        challenge = acme_challenge()
        evaluate_rules()
        self.assert_decided(challenge, None)

    def test_challenge_without_instance(self):
        """Test that a challenge without instance is never matched."""
        create_record_request(
            'www', 'example.com', 'A', '10.0.0.1', status=Status.APPROVED, instance=None
        )
        challenge = acme_challenge(instance=None)
        evaluate_rules()
        self.assert_decided(challenge, None)

    def test_challenge_without_requirer(self):
        """Test that a challenge without requirer is never matched."""
        create_record_request(
            'www', 'example.com', 'A', '10.0.0.1', requirer_id=None, status=Status.APPROVED
        )
        challenge = acme_challenge(requirer_id=None)
        evaluate_rules()
        self.assert_decided(challenge, None)

    def test_a_record_not_approved(self):
        """Test that a pending or denied A record is not enough."""
        a_record = create_record_request('www', 'example.com', 'A', '10.0.0.1')
        challenge = acme_challenge()
        evaluate_rules()
        self.assert_decided(challenge, None)
        a_record.status = Status.DENIED
        a_record.save()
        evaluate_rules()
        self.assert_decided(challenge, None)

    def test_a_record_of_another_domain(self):
        """Test that only the A record of the challenged domain is considered."""
        create_record_request('example.com', 'com', 'A', '10.0.0.1', status=Status.APPROVED)
        create_record_request('api.www', 'example.com', 'A', '10.0.0.1', status=Status.APPROVED)
        challenge = acme_challenge()
        evaluate_rules()
        self.assert_decided(challenge, None)

    def test_other_records_are_not_matched(self):
        """Test that only the ACME challenge TXT records are matched."""
        create_record_request('www', 'example.com', 'A', '10.0.0.1', status=Status.APPROVED)
        others = [
            create_record_request('_acme-challenge.www', 'example.com', 'CNAME', 'other.com'),
            create_record_request('_other.www', 'example.com', 'TXT', 'value'),
            create_record_request('www', 'example.com', 'TXT', 'value'),
        ]
        evaluate_rules()
        for record_request in others:
            self.assert_decided(record_request, None)

    def test_ddns_domain_of_the_same_requirer(self):
        """Test that the challenges of an allocated domain and its subdomains are approved."""
        allocation = ddns.allocate(INSTANCE, '1', 'ddns.example.com')
        label = allocation.domain.partition('.')[0]
        challenges = [
            acme_challenge(host_label=f'_acme-challenge.{label}', domain='ddns.example.com'),
            acme_challenge(host_label=f'_acme-challenge.www.{label}', domain='ddns.example.com'),
        ]
        evaluate_rules()
        for challenge in challenges:
            self.assert_decided(challenge, self.rule)

    def test_ddns_domain_of_another_requirer(self):
        """Test that the allocated domain of another requirer is not enough."""
        allocation = ddns.allocate(INSTANCE, '2', 'ddns.example.com')
        challenge = acme_challenge(host_label='_acme-challenge', domain=allocation.domain)
        evaluate_rules()
        self.assert_decided(challenge, None)

    def test_ddns_domain_of_another_instance(self):
        """Test that the allocated domain of the same requirer id of another instance is not enough.

        Requirer ids start over from scratch in a deployment restored from a backup of the
        database, so the requirer of an old allocation may share its id with a new one.
        """
        allocation = ddns.allocate(OTHER_INSTANCE, '1', 'ddns.example.com')
        challenge = acme_challenge(host_label='_acme-challenge', domain=allocation.domain)
        evaluate_rules()
        self.assert_decided(challenge, None)

    def test_ddns_parent_domain_is_not_matched(self):
        """Test that the parent of an allocated domain is not owned by its requirer."""
        ddns.allocate(INSTANCE, '1', 'ddns.example.com')
        challenge = acme_challenge(host_label='_acme-challenge', domain='ddns.example.com')
        evaluate_rules()
        self.assert_decided(challenge, None)

    def test_ddns_allocation_triggers_the_evaluation(self):
        """Test that allocating a domain evaluates the rules again."""
        label = ddns.derive_label(INSTANCE, '1')
        challenge = acme_challenge(host_label=f'_acme-challenge.{label}', domain='ddns.example.com')
        evaluate_rules()
        self.assert_decided(challenge, None)
        ddns.allocate(INSTANCE, '1', 'ddns.example.com')
        self.assert_decided(challenge, self.rule)


class TestRuleDomain(TestCase):
    """Test the domain of the rules."""

    def setUp(self):
        """Set up."""
        create_record_request('www', 'example.com', 'A', '10.0.0.1', status=Status.APPROVED)
        create_record_request('api', 'example.com', 'A', '10.0.0.2', status=Status.APPROVED)
        self.www = acme_challenge()
        self.api = acme_challenge(host_label='_acme-challenge.api')

    def decided(self, record_request):
        """Get whether a record request is automatically decided."""
        record_request.refresh_from_db()
        return record_request.rule_id is not None

    def test_rule_only_applies_under_its_domain(self):
        """Test that a rule only applies to the records of its domain and subdomains."""
        create_rule(domain='www.example.com')
        self.assertTrue(self.decided(self.www))
        self.assertFalse(self.decided(self.api))

    def test_rule_domain_is_matched_on_label_boundaries(self):
        """Test that the domain of a rule is not matched as a plain string suffix."""
        create_rule(domain='ample.com')
        self.assertFalse(self.decided(self.www))

    def test_rule_domain_of_another_domain(self):
        """Test that a rule doesn't apply outside of its domain."""
        create_rule(domain='example.org')
        self.assertFalse(self.decided(self.www))
        self.assertFalse(self.decided(self.api))

    def test_changing_the_rule_domain_triggers_the_evaluation(self):
        """Test that changing the domain of a rule evaluates the rules again."""
        rule = create_rule(domain='www.example.com')
        rule.domain = 'api.example.com'
        rule.save()
        self.assertFalse(self.decided(self.www))
        self.assertTrue(self.decided(self.api))

    def test_rule_domain_is_normalized(self):
        """Test that the domain of a rule is normalized."""
        rule = create_rule(domain=' WWW.Example.COM. ')
        rule.refresh_from_db()
        self.assertEqual(rule.domain, 'www.example.com')
        self.assertTrue(self.decided(self.www))

    def test_rule_domain_is_validated(self):
        """Test that the domain of a rule must be a valid domain name."""
        for domain in ('', 'not a domain', 'example..com', '-example.com'):
            with self.assertRaises(ValidationError):
                Rule(name='invalid', kind=Rule.Kind.ACME_CHALLENGE, domain=domain).full_clean()
        Rule(name='valid', kind=Rule.Kind.ACME_CHALLENGE, domain='Example.com.').full_clean()


class TestEvaluation(RulesTestCase):
    """Test the evaluation of the rules."""

    def setUp(self):
        """Set up."""
        super().setUp()
        self.a_record = create_record_request(
            'www', 'example.com', 'A', '10.0.0.1', status=Status.APPROVED
        )
        self.challenge = acme_challenge()
        evaluate_rules()

    def test_only_pending_requests_are_decided(self):
        """Test that the manual reviews take precedence over the rules."""
        self.assert_decided(self.challenge, self.rule)
        self.challenge.status = Status.DENIED
        self.challenge.save()
        evaluate_rules()
        self.assert_decided(self.challenge, None)
        self.assertEqual(self.challenge.effective_status, Status.DENIED)

    def test_decision_is_dropped_when_the_dependency_changes(self):
        """Test that a decision is dropped when the A record is no longer approved."""
        self.a_record.delete()
        evaluate_rules()
        self.assert_decided(self.challenge, None)
        self.assertEqual(self.challenge.effective_status, Status.PENDING)

    def test_disabling_a_rule_triggers_the_evaluation(self):
        """Test that changing a rule evaluates the rules again."""
        self.rule.enabled = False
        self.rule.save()
        self.assert_decided(self.challenge, None)
        self.rule.enabled = True
        self.rule.save()
        self.assert_decided(self.challenge, self.rule)

    def test_deleting_a_rule_triggers_the_evaluation(self):
        """Test that deleting a rule evaluates the rules again."""
        self.rule.delete()
        self.assert_decided(self.challenge, None)
        create_rule(name='new')
        self.challenge.refresh_from_db()
        self.assertIsNotNone(self.challenge.rule)

    def test_deny_action(self):
        """Test that a rule can automatically deny the requests it matches."""
        self.rule.action = Rule.Action.DENY
        self.rule.save()
        self.assert_decided(self.challenge, self.rule)
        self.assertEqual(self.challenge.effective_status, Status.DENIED)

    def test_rules_are_evaluated_by_priority(self):
        """Test that the first matching rule, by priority, decides."""
        deny_rule = create_rule(name='deny', action=Rule.Action.DENY, priority=-1)
        self.assert_decided(self.challenge, deny_rule)
        deny_rule.priority = 1
        deny_rule.save()
        self.assert_decided(self.challenge, self.rule)

    def test_automatic_decisions_are_chained(self):
        """Test that a request can depend on the automatic decision of another one."""
        self.a_record.status = Status.PENDING
        self.a_record.save()
        original = rules.MATCHERS[Rule.Kind.ACME_CHALLENGE]

        def matcher(record_request, context):
            # Stands for a rule approving the A record, whatever its logic
            if record_request.pk == self.a_record.pk:
                return True
            return original(record_request, context)

        rules.MATCHERS[Rule.Kind.ACME_CHALLENGE] = matcher
        try:
            evaluate_rules()
        finally:
            rules.MATCHERS[Rule.Kind.ACME_CHALLENGE] = original
        self.assert_decided(self.a_record, self.rule)
        self.assert_decided(self.challenge, self.rule)


class TestApi(APITestCase):
    """Test that the API reports the automatic decisions as regular ones."""

    def setUp(self):
        """Set up."""
        self.user = User.objects.create_user('testuser', 'testuser@example.com', 'password')
        self.client.login(username='testuser', password='password')

    def submit(self, *record_requests):
        """Submit record requests like the charm does."""
        response = self.client.post(reverse('requests'), list(record_requests), format='json')
        self.assertEqual(response.status_code, 200)

    def listed(self, name):
        """Get the uuids of the record requests listed by an endpoint."""
        return {r['uuid']: r for r in self.client.get(reverse(name)).json()}

    def test_automatic_approval(self):
        """Test the life of an automatically approved ACME challenge."""
        create_rule()
        a_record = {
            'uuid': str(uuid.uuid4()), 'host_label': 'www', 'domain': 'example.com',
            'ttl': 600, 'record_type': 'A', 'record_data': '10.0.0.1', 'requirer_id': '1',
            'instance': str(INSTANCE),
        }
        challenge = {
            'uuid': str(uuid.uuid4()), 'host_label': '_acme-challenge.www',
            'domain': 'example.com', 'ttl': 600, 'record_type': 'TXT',
            'record_data': 'challenge', 'requirer_id': '1', 'instance': str(INSTANCE),
        }
        self.submit(a_record, challenge)
        self.assertEqual(set(self.listed('api_list_pending')), {a_record['uuid'], challenge['uuid']})
        self.assertEqual(self.listed('api_list_approved'), {})

        self.client.patch(reverse('api_request_approve', args=[a_record['uuid']]))
        approved = self.listed('api_list_approved')
        self.assertEqual(set(approved), {a_record['uuid'], challenge['uuid']})
        self.assertEqual(approved[challenge['uuid']]['status'], Status.APPROVED)
        self.assertNotIn('rule', approved[challenge['uuid']])
        self.assertEqual(self.listed('api_list_pending'), {})
        all_requests = self.listed('api_list_all')
        self.assertEqual(all_requests[challenge['uuid']]['status'], Status.APPROVED)

        self.client.patch(reverse('api_request_deny', args=[a_record['uuid']]))
        self.assertEqual(set(self.listed('api_list_pending')), {challenge['uuid']})
        self.assertEqual(set(self.listed('api_list_denied')), {a_record['uuid']})

    def test_automatic_denial(self):
        """Test that the automatically denied requests are listed as denied."""
        create_rule(action=Rule.Action.DENY)
        create_record_request('www', 'example.com', 'A', '10.0.0.1', status=Status.APPROVED)
        challenge = acme_challenge()
        evaluate_rules()
        denied = self.listed('api_list_denied')
        self.assertEqual(set(denied), {str(challenge.uuid)})
        self.assertEqual(denied[str(challenge.uuid)]['status'], Status.DENIED)

    def test_rule_is_not_writable(self):
        """Test that the API can't set the rule deciding a record request."""
        rule = create_rule()
        record_uuid = str(uuid.uuid4())
        self.submit({
            'uuid': record_uuid, 'host_label': 'www', 'domain': 'example.com',
            'ttl': 600, 'record_type': 'A', 'record_data': '10.0.0.1', 'rule': rule.id,
        })
        self.assertIsNone(RecordRequest.objects.get(pk=record_uuid).rule)


class TestAdmin(RulesTestCase):
    """Test the admin website overrides of the automatic decisions."""

    def setUp(self):
        """Set up."""
        super().setUp()
        self.reviewer = User.objects.create_superuser('admin', 'admin@example.com', 'password')
        self.request = RequestFactory().get('/')
        self.request.user = self.reviewer
        self.model_admin = RecordRequestAdmin(RecordRequest, admin.site)
        create_record_request('www', 'example.com', 'A', '10.0.0.1', status=Status.APPROVED)
        self.challenge = acme_challenge()
        evaluate_rules()
        self.challenge.refresh_from_db()

    def queryset(self):
        """Get the queryset of the challenge."""
        return RecordRequest.objects.filter(pk=self.challenge.pk)

    def test_decision_display(self):
        """Test that the admin website tells the automatic decisions apart."""
        self.assertEqual(
            self.model_admin.decision(self.challenge),
            'Approved automatically (rule: ACME challenge)',
        )
        self.challenge.status = Status.APPROVED
        self.challenge.rule = None
        self.assertEqual(self.model_admin.decision(self.challenge), 'Approved')

    def test_manual_override(self):
        """Test that a reviewer can override an automatic decision, and reset it."""
        deny(self.model_admin, self.request, self.queryset())
        self.challenge.refresh_from_db()
        self.assertEqual(self.challenge.effective_status, Status.DENIED)
        self.assertIsNone(self.challenge.rule)
        self.assertEqual(self.challenge.reviewer, self.reviewer)

        reset_to_pending(self.model_admin, self.request, self.queryset())
        self.challenge.refresh_from_db()
        self.assertEqual(self.challenge.status, Status.PENDING)
        self.assertEqual(self.challenge.rule, self.rule)
        self.assertIsNone(self.challenge.reviewer)

        approve(self.model_admin, self.request, self.queryset())
        self.challenge.refresh_from_db()
        self.assertEqual(self.challenge.status, Status.APPROVED)
        self.assertIsNone(self.challenge.rule)

    def test_changelist(self):
        """Test that the admin changelist renders the automatic decisions."""
        self.client.force_login(self.reviewer)
        response = self.client.get(reverse('admin:policy_recordrequest_changelist'))
        self.assertContains(response, 'Approved automatically (rule: ACME challenge)')
        response = self.client.get(
            reverse('admin:policy_recordrequest_changelist'), {'decision': 'automatic'}
        )
        self.assertContains(response, '_acme-challenge.www')
        response = self.client.get(reverse('admin:policy_rule_changelist'))
        self.assertContains(response, 'ACME challenge')

    def test_add_rule(self):
        """Test that adding a rule from the admin website evaluates the rules again."""
        self.rule.delete()
        self.challenge.refresh_from_db()
        self.assertIsNone(self.challenge.rule)
        self.client.force_login(self.reviewer)
        form = {
            'name': 'www', 'kind': Rule.Kind.ACME_CHALLENGE, 'action': Rule.Action.APPROVE,
            'enabled': 'on', 'priority': 0, 'description': '',
        }
        response = self.client.post(
            reverse('admin:policy_rule_add'), {**form, 'domain': 'not a domain'}
        )
        self.assertEqual(response.status_code, 200)
        self.assertFalse(Rule.objects.exists())
        response = self.client.post(
            reverse('admin:policy_rule_add'), {**form, 'domain': 'WWW.example.com.'}
        )
        self.assertEqual(response.status_code, 302)
        self.assertEqual(Rule.objects.get().domain, 'www.example.com')
        self.challenge.refresh_from_db()
        self.assertEqual(self.challenge.rule, Rule.objects.get())

