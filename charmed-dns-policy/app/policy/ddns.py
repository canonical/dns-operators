# Copyright 2026 Canonical Ltd.
# See LICENSE file for licensing details.

"""Allocation of the automatically allocated domains."""

import hashlib
import re
import uuid

from django.db import IntegrityError, transaction

from .models import DdnsAllocation

# The Open Location Code character set to avoids accidentally forming words
# and reduces the chance of a human mistyping an allocated domain.
OPEN_LOCATION_CODE_ALPHABET = "23456789CFGHJMPQRVWX"

DDNS_LABEL_LENGTH = 8
ALLOCATION_ATTEMPTS = 50

DOMAIN_MAX_LENGTH = 253
# Maximum length of a parent domain, leaving room for the allocated label and its dot
PARENT_MAX_LENGTH = DOMAIN_MAX_LENGTH - DDNS_LABEL_LENGTH - 1
_DOMAIN_LABEL_PATTERN = re.compile(r"^(?!-)[a-z0-9-]{1,63}(?<!-)$")


class DdnsAllocationError(Exception):
    """Raised when no domain could be allocated for a relation."""


def normalize_parent(parent):
    """Normalize and validate the parent domain of an allocated domain.

    Raises:
        ValueError: when the parent is not a valid domain name.
    """
    parent = str(parent).strip().rstrip(".").lower()
    if not parent:
        raise ValueError("The parent domain is empty")
    if len(parent) > PARENT_MAX_LENGTH:
        raise ValueError(
            f"The parent domain is {len(parent)} characters long, "
            f"it must be at most {PARENT_MAX_LENGTH} characters"
        )
    for label in parent.split("."):
        if not _DOMAIN_LABEL_PATTERN.match(label):
            raise ValueError(f"The parent domain label {label!r} is not a valid domain label")
    return parent


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


def allocate(instance, relation_id, parent):
    """Get the domain allocated to a relation under a parent, allocating one if needed.

    Allocations are never deleted, so a domain handed out once is never handed out
    again, even after the relation it was allocated to is gone.

    A relation is identified by the pair (instance, relation_id), as relation ids are
    only unique within a single charm deployment.
    """
    parent = normalize_parent(parent)

    def existing():
        allocations = DdnsAllocation.objects.filter(instance=instance, relation_id=relation_id)
        return next((a for a in allocations if a.parent == parent), None)

    allocation = existing()
    if allocation is not None:
        return allocation

    for attempt in range(ALLOCATION_ATTEMPTS):
        try:
            with transaction.atomic():
                return DdnsAllocation.objects.create(
                    instance=instance,
                    relation_id=relation_id,
                    domain=f"{derive_label(instance, relation_id, attempt)}.{parent}",
                )
        except IntegrityError:
            allocation = existing()
            if allocation is not None:
                return allocation

    raise DdnsAllocationError(
        f"Could not allocate a domain under {parent} for the relation {relation_id} "
        f"of instance {instance}"
    )
