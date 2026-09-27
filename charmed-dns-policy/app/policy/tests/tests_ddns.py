# Copyright 2026 Canonical Ltd.
# See LICENSE file for licensing details.

"""Test the allocation of the automatically allocated domains."""

import uuid
from unittest.mock import patch

from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from policy import ddns
from policy.models import DdnsAllocation


class TestDeriveLabel(TestCase):
    """Test the label derivation."""

    def test_label_uses_the_open_location_code_alphabet(self):
        """Test that a derived label only uses the Open Location Code characters."""
        alphabet = set(ddns.OPEN_LOCATION_CODE_ALPHABET.lower())
        for relation_id in range(100):
            label = ddns.derive_label(uuid.uuid4(), relation_id)
            self.assertEqual(len(label), ddns.DDNS_LABEL_LENGTH)
            self.assertLessEqual(set(label), alphabet)

    def test_label_is_reproducible(self):
        """Test that a relation always derives the same label."""
        instance = uuid.uuid4()
        self.assertEqual(ddns.derive_label(instance, 1), ddns.derive_label(instance, 1))
        self.assertEqual(ddns.derive_label(instance, 1), ddns.derive_label(str(instance), 1))

    def test_label_depends_on_the_whole_identity(self):
        """Test that the instance, the relation id and the attempt all change the label."""
        instance = uuid.uuid4()
        labels = {
            ddns.derive_label(instance, 1),
            ddns.derive_label(instance, 2),
            ddns.derive_label(uuid.uuid4(), 1),
            ddns.derive_label(instance, 1, attempt=1),
        }
        self.assertEqual(len(labels), 4)


class TestNormalizeParent(TestCase):
    """Test the parent domain validation."""

    def test_parent_is_normalized(self):
        """Test that a parent domain is lowercased and stripped of its trailing dot."""
        self.assertEqual(ddns.normalize_parent(" DDNS.Example.com. "), "ddns.example.com")

    def test_invalid_parent(self):
        """Test that an invalid parent domain is rejected."""
        for parent in ("", ".", "a..b", "-a.com", "a_b.com", f"{'a' * 64}.com", "a." * 125):
            with self.assertRaises(ValueError, msg=parent):
                ddns.normalize_parent(parent)


class TestAllocate(TestCase):
    """Test the domain allocation."""

    def setUp(self):
        """Set up."""
        self.instance = uuid.uuid4()
        self.parent = "ddns.example.com"

    def test_allocation_is_stable(self):
        """Test that a relation always gets back the same domain."""
        allocation = ddns.allocate(self.instance, 42, self.parent)
        self.assertEqual(ddns.allocate(self.instance, 42, self.parent).domain, allocation.domain)
        self.assertEqual(DdnsAllocation.objects.count(), 1)

    def test_allocation_is_under_the_parent(self):
        """Test that the allocated domain is a random label under the parent domain."""
        allocation = ddns.allocate(self.instance, 42, "DDNS.example.com.")
        self.assertEqual(
            allocation.domain, f"{ddns.derive_label(self.instance, 42)}.{self.parent}"
        )
        self.assertEqual(allocation.parent, self.parent)

    def test_allocations_are_unique(self):
        """Test that two relations get two different domains."""
        domains = {
            ddns.allocate(self.instance, relation_id, self.parent).domain
            for relation_id in range(10)
        }
        self.assertEqual(len(domains), 10)

    def test_allocations_are_scoped_to_the_instance(self):
        """Test that the same relation id of another instance gets another domain.

        Relation ids start over from scratch in a deployment restored from a backup of
        the database, so an allocation must never be handed to another instance.
        """
        allocation = ddns.allocate(self.instance, 1, self.parent)
        other = ddns.allocate(uuid.uuid4(), 1, self.parent)
        self.assertNotEqual(other.domain, allocation.domain)
        self.assertEqual(DdnsAllocation.objects.count(), 2)

    def test_allocations_are_scoped_to_the_parent(self):
        """Test that a relation gets one domain per parent domain."""
        allocation = ddns.allocate(self.instance, 1, self.parent)
        other = ddns.allocate(self.instance, 1, "example.org")
        self.assertEqual(other.parent, "example.org")
        self.assertEqual(ddns.allocate(self.instance, 1, self.parent).domain, allocation.domain)
        self.assertEqual(DdnsAllocation.objects.count(), 2)

    def test_parent_suffix_is_not_mistaken_for_the_parent(self):
        """Test that a domain allocated under a subdomain doesn't match its parent."""
        ddns.allocate(self.instance, 1, f"sub.{self.parent}")
        allocation = ddns.allocate(self.instance, 1, self.parent)
        self.assertEqual(allocation.parent, self.parent)
        self.assertEqual(DdnsAllocation.objects.count(), 2)

    def test_a_taken_domain_is_not_reused(self):
        """Test that a domain already taken is derived again instead of being reused."""
        DdnsAllocation.objects.create(
            instance=uuid.uuid4(),
            relation_id=1,
            domain=f"{ddns.derive_label(self.instance, 2)}.{self.parent}",
        )
        allocation = ddns.allocate(self.instance, 2, self.parent)
        self.assertEqual(
            allocation.domain,
            f"{ddns.derive_label(self.instance, 2, attempt=1)}.{self.parent}",
        )

    def test_allocation_gives_up_after_too_many_collisions(self):
        """Test that the allocation errors out when it can't find a free domain."""
        DdnsAllocation.objects.create(
            instance=uuid.uuid4(), relation_id=1, domain=f"c3f9m2q4.{self.parent}"
        )
        with patch.object(ddns, "derive_label", return_value="c3f9m2q4"):
            with self.assertRaises(ddns.DdnsAllocationError):
                ddns.allocate(self.instance, 2, self.parent)


class TestDdnsAllocationsView(APITestCase):
    """Test the automatically allocated domain API."""

    def setUp(self):
        """Set up."""
        self.user = User.objects.create_user('testuser', 'testuser@example.com', 'password')
        self.instance = str(uuid.uuid4())
        self.parent = "ddns.example.com"
        self.url = reverse('ddns_allocations')

    def allocate(self, *relations):
        """Request the allocation of the (instance, relation_id, parent) relations."""
        return self.client.post(
            self.url,
            [
                {"instance": str(instance), "relation_id": relation_id, "parent": parent}
                for instance, relation_id, parent in relations
            ],
            format='json',
        )

    def test_allocate(self):
        """Test that posting relations allocates a domain for each of them."""
        self.client.login(username='testuser', password='password')
        response = self.allocate(
            (self.instance, 1, self.parent), (self.instance, 2, "Example.org.")
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        first, second = response.json()
        self.assertEqual(first["instance"], self.instance)
        self.assertEqual(first["relation_id"], 1)
        self.assertEqual(
            first["domain"], f"{ddns.derive_label(self.instance, 1)}.{self.parent}"
        )
        self.assertIn("created_at", first)
        self.assertEqual(second["relation_id"], 2)
        self.assertEqual(
            second["domain"], f"{ddns.derive_label(self.instance, 2)}.example.org"
        )

    def test_allocation_is_stable(self):
        """Test that a relation always gets back the same domain."""
        self.client.login(username='testuser', password='password')
        domain = self.allocate((self.instance, 1, self.parent)).json()[0]["domain"]
        response = self.allocate(
            (self.instance, 1, self.parent),
            (self.instance, 2, self.parent),
            (uuid.uuid4(), 1, self.parent),
        ).json()
        self.assertEqual(response[0]["domain"], domain)
        self.assertNotEqual(response[1]["domain"], domain)
        self.assertNotEqual(response[2]["domain"], domain)
        self.assertEqual(DdnsAllocation.objects.count(), 3)

    def test_empty_allocation(self):
        """Test that posting no relation allocates nothing."""
        self.client.login(username='testuser', password='password')
        response = self.allocate()
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.json(), [])

    def test_allocation_failure(self):
        """Test that a relation that can't be allocated a domain is reported as a conflict."""
        self.client.login(username='testuser', password='password')
        DdnsAllocation.objects.create(
            instance=uuid.uuid4(), relation_id=1, domain=f"c3f9m2q4.{self.parent}"
        )
        with patch.object(ddns, "derive_label", return_value="c3f9m2q4"):
            response = self.allocate((self.instance, 2, self.parent))
        self.assertEqual(response.status_code, status.HTTP_409_CONFLICT)

    def test_invalid_request(self):
        """Test that an invalid allocation request is rejected."""
        self.client.login(username='testuser', password='password')
        invalid_requests = [
            {"instance": self.instance, "relation_id": 1},
            {"instance": "not-a-uuid", "relation_id": 1, "parent": self.parent},
            {"instance": self.instance, "relation_id": -1, "parent": self.parent},
            {"instance": self.instance, "relation_id": 1, "parent": "not a domain"},
        ]
        for invalid_request in invalid_requests:
            response = self.client.post(self.url, [invalid_request], format='json')
            self.assertEqual(
                response.status_code, status.HTTP_400_BAD_REQUEST, msg=invalid_request
            )
        response = self.client.post(
            self.url,
            {"instance": self.instance, "relation_id": 1, "parent": self.parent},
            format='json',
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(DdnsAllocation.objects.count(), 0)

    def test_list(self):
        """Test that every allocation can be listed."""
        self.client.login(username='testuser', password='password')
        allocation = ddns.allocate(self.instance, 1, self.parent)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.json()), 1)
        self.assertEqual(response.json()[0]["instance"], self.instance)
        self.assertEqual(response.json()[0]["domain"], allocation.domain)

    def test_unauthenticated_access(self):
        """Test unauthenticated access."""
        self.client.logout()
        response = self.allocate((self.instance, 1, self.parent))
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
        self.assertEqual(self.client.get(self.url).status_code, status.HTTP_401_UNAUTHORIZED)
