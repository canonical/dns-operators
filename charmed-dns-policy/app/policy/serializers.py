# Copyright 2026 Canonical Ltd.
# See LICENSE file for licensing details.

"""Define serializers."""

from rest_framework import serializers

from . import ddns
from .models import DdnsAllocation, RecordRequest


class RecordRequestSerializer(serializers.ModelSerializer):
    """Define record request serializer."""
    uuid = serializers.UUIDField(required=True)

    class Meta:
        """Define meta of the serializer."""
        model = RecordRequest
        fields = '__all__'


class DdnsAllocationSerializer(serializers.ModelSerializer):
    """Define the automatically allocated domain serializer."""

    class Meta:
        """Define meta of the serializer."""
        model = DdnsAllocation
        fields = ['instance', 'requirer_id', 'domain', 'created_at']
        read_only_fields = ['domain', 'created_at']


class DdnsAllocationRequestSerializer(serializers.Serializer):
    """Define the automatically allocated domain request serializer."""
    instance = serializers.UUIDField()
    requirer_id = serializers.CharField(max_length=255)
    parent = serializers.CharField()

    def validate_parent(self, value):
        """Validate and normalize the parent domain."""
        try:
            return ddns.normalize_parent(value)
        except ValueError as error:
            raise serializers.ValidationError(str(error)) from error
