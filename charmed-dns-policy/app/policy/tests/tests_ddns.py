# Copyright 2026 Canonical Ltd.
# See LICENSE file for licensing details.

"""Test the allocation of the automatically allocated domain labels."""

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


class TestAllocate(TestCase):
    """Test the label allocation."""

    def setUp(self):
        """Set up."""
        self.instance = uuid.uuid4()

    def test_allocation_is_stable(self):
        """Test that a relation always gets back the same label."""
        allocation = ddns.allocate(self.instance, 42)
        self.assertEqual(ddns.allocate(self.instance, 42).label, allocation.label)
        self.assertEqual(DdnsAllocation.objects.count(), 1)

    def test_allocations_are_unique(self):
        """Test that two relations get two different labels."""
        labels = {ddns.allocate(self.instance, relation_id).label for relation_id in range(10)}
        self.assertEqual(len(labels), 10)

    def test_allocations_are_scoped_to_the_instance(self):
        """Test that the same relation id of another instance gets another label.

        Relation ids start over from scratch in a deployment restored from a backup of
        the database, so an allocation must never be handed to another instance.
        """
        allocation = ddns.allocate(self.instance, 1)
        other = ddns.allocate(uuid.uuid4(), 1)
        self.assertNotEqual(other.label, allocation.label)
        self.assertEqual(DdnsAllocation.objects.count(), 2)

    def test_allocation_is_reproducible(self):
        """Test that the allocated label is the one derived from the relation identity."""
        allocation = ddns.allocate(self.instance, 42)
        self.assertEqual(allocation.label, ddns.derive_label(self.instance, 42))

    def test_a_taken_label_is_not_reused(self):
        """Test that a label already taken is derived again instead of being reused."""
        DdnsAllocation.objects.create(
            instance=uuid.uuid4(), relation_id=1, label=ddns.derive_label(self.instance, 2)
        )
        allocation = ddns.allocate(self.instance, 2)
        self.assertEqual(allocation.label, ddns.derive_label(self.instance, 2, attempt=1))

    def test_allocation_gives_up_after_too_many_collisions(self):
        """Test that the allocation errors out when it can't find a free label."""
        DdnsAllocation.objects.create(instance=uuid.uuid4(), relation_id=1, label="c3f9m2q4")
        with patch.object(ddns, "derive_label", return_value="c3f9m2q4"):
            with self.assertRaises(ddns.DdnsAllocationError):
                ddns.allocate(self.instance, 2)


class TestDdnsAllocationView(APITestCase):
    """Test the automatically allocated domain label API."""

    def setUp(self):
        """Set up."""
        self.user = User.objects.create_user('testuser', 'testuser@example.com', 'password')
        self.instance = str(uuid.uuid4())

    def url(self, instance, relation_id):
        """Build the url of the allocation of a relation."""
        return reverse('ddns_allocation', args=[instance, relation_id])

    def test_allocate(self):
        """Test that getting a relation allocates a label for it."""
        self.client.login(username='testuser', password='password')
        response = self.client.get(self.url(self.instance, 1))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        allocation = response.json()
        self.assertEqual(allocation["instance"], self.instance)
        self.assertEqual(allocation["relation_id"], 1)
        self.assertEqual(allocation["label"], ddns.derive_label(self.instance, 1))

    def test_allocation_is_stable(self):
        """Test that a relation always gets back the same label."""
        self.client.login(username='testuser', password='password')
        label = self.client.get(self.url(self.instance, 1)).json()["label"]
        self.assertEqual(self.client.get(self.url(self.instance, 1)).json()["label"], label)
        self.assertNotEqual(self.client.get(self.url(self.instance, 2)).json()["label"], label)
        self.assertNotEqual(
            self.client.get(self.url(uuid.uuid4(), 1)).json()["label"], label
        )
        self.assertEqual(DdnsAllocation.objects.count(), 3)

    def test_allocation_failure(self):
        """Test that a relation that can't be allocated a label is reported as a conflict."""
        self.client.login(username='testuser', password='password')
        DdnsAllocation.objects.create(instance=uuid.uuid4(), relation_id=1, label="c3f9m2q4")
        with patch.object(ddns, "derive_label", return_value="c3f9m2q4"):
            response = self.client.get(self.url(self.instance, 2))
        self.assertEqual(response.status_code, status.HTTP_409_CONFLICT)

    def test_invalid_url(self):
        """Test that an instance that is not a uuid does not resolve."""
        self.client.login(username='testuser', password='password')
        response = self.client.get('/api/ddns/allocations/not-a-uuid/1/')
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_list(self):
        """Test that every allocation can be listed."""
        self.client.login(username='testuser', password='password')
        ddns.allocate(self.instance, 1)
        response = self.client.get(reverse('ddns_allocations'))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.json()), 1)
        self.assertEqual(response.json()[0]["instance"], self.instance)

    def test_unauthenticated_access(self):
        """Test unauthenticated access."""
        self.client.logout()
        response = self.client.get(self.url(self.instance, 1))
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
        self.assertEqual(
            self.client.get(reverse('ddns_allocations')).status_code,
            status.HTTP_401_UNAUTHORIZED,
        )
