# Copyright 2026 Canonical Ltd.
# See LICENSE file for licensing details.

"""Define serializers."""

from rest_framework import serializers

from .models import DdnsAllocation, RecordRequest


class RecordRequestSerializer(serializers.ModelSerializer):
    """Define record request serializer."""
    uuid = serializers.UUIDField(required=True)

    class Meta:
        """Define meta of the serializer."""
        model = RecordRequest
        fields = '__all__'


class DdnsAllocationSerializer(serializers.ModelSerializer):
    """Define the automatically allocated domain label serializer."""

    class Meta:
        """Define meta of the serializer."""
        model = DdnsAllocation
        fields = ['instance', 'relation_id', 'label', 'created_at']
        read_only_fields = ['label', 'created_at']
