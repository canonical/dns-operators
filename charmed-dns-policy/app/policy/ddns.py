# Copyright 2026 Canonical Ltd.
# See LICENSE file for licensing details.

"""Allocation of the labels of the automatically allocated domains."""

import hashlib
import uuid

from django.db import IntegrityError, transaction

from .models import DdnsAllocation

# The Open Location Code character set to avoids accidentally forming words
# and reduces the chance of a human mistyping an allocated domain.
OPEN_LOCATION_CODE_ALPHABET = "23456789CFGHJMPQRVWX"

DDNS_LABEL_LENGTH = 8
ALLOCATION_ATTEMPTS = 50


class DdnsAllocationError(Exception):
    """Raised when no label could be allocated for a relation."""


def derive_label(instance, relation_id, attempt=0):
    """Derive the label of a relation from the identity of that relation.

    The `attempt` counter salts the digest, which gives a relation a different label on
    every attempt when the derived one turns out to be taken already.
    """
    try:
        instance = uuid.UUID(str(instance))
    except ValueError:
        pass

    digest = hashlib.blake2b(
        f"{instance}:{relation_id}:{attempt}".encode(), digest_size=16
    ).digest()

    value = int.from_bytes(digest, "big")
    characters = []
    for _ in range(DDNS_LABEL_LENGTH):
        value, index = divmod(value, len(OPEN_LOCATION_CODE_ALPHABET))
        characters.append(OPEN_LOCATION_CODE_ALPHABET[index])
    return "".join(characters).lower()


def allocate(instance, relation_id):
    """Get the label allocated to a relation, allocating a new one if needed.

    Allocations are never deleted, so a label handed out once is never handed out
    again, even after the relation it was allocated to is gone.

    A relation is identified by the pair (instance, relation_id), as relation ids are
    only unique within a single charm deployment.
    """
    allocation = DdnsAllocation.objects.filter(instance=instance, relation_id=relation_id).first()
    if allocation is not None:
        return allocation

    for attempt in range(ALLOCATION_ATTEMPTS):
        try:
            with transaction.atomic():
                return DdnsAllocation.objects.create(
                    instance=instance,
                    relation_id=relation_id,
                    label=derive_label(instance, relation_id, attempt),
                )
        except IntegrityError:
            allocation = DdnsAllocation.objects.filter(
                instance=instance, relation_id=relation_id
            ).first()
            if allocation is not None:
                return allocation

    raise DdnsAllocationError(
        f"Could not allocate a label for the relation {relation_id} of instance {instance}"
    )
