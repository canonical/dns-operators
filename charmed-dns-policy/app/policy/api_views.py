# Copyright 2026 Canonical Ltd.
# See LICENSE file for licensing details.

"""Define views."""

from rest_framework import generics, permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView

from . import ddns
from .models import DdnsAllocation, RecordRequest
from .serializers import (
    DdnsAllocationRequestSerializer,
    DdnsAllocationSerializer,
    RecordRequestSerializer,
)


class ListAllRequestsView(APIView):
    """List all requests view."""
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        """Get all requests."""
        record_requests = RecordRequest.objects.all()
        serializer = RecordRequestSerializer(record_requests, many=True)
        return Response(serializer.data)


class ListPendingRequestsView(APIView):
    """List pending requests view."""
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        """Get pending requests."""
        record_requests = RecordRequest.objects.filter(status='pending')
        serializer = RecordRequestSerializer(record_requests, many=True)
        return Response(serializer.data)


class ListApprovedRequestsView(APIView):
    """List approved requests view."""
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        """Get approved requests."""
        record_requests = RecordRequest.objects.filter(
            status__in=(
                RecordRequest.Status.APPROVED,
                RecordRequest.Status.FAILED,
                RecordRequest.Status.PUBLISHED,
            )
        )
        serializer = RecordRequestSerializer(record_requests, many=True)
        return Response(serializer.data)


class ListDeniedRequestsView(APIView):
    """List denied requests view."""
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        """Get denied requests."""
        record_requests = RecordRequest.objects.filter(status=RecordRequest.Status.DENIED)
        serializer = RecordRequestSerializer(record_requests, many=True)
        return Response(serializer.data)


class ApproveRequestView(APIView):
    """Approve request view."""
    permission_classes = [permissions.IsAuthenticated]

    def patch(self, request, pk):
        """Approve request."""
        try:
            record_request = RecordRequest.objects.get(pk=pk)
        except RecordRequest.DoesNotExist:
            return Response(status=status.HTTP_404_NOT_FOUND)
        record_request.status = RecordRequest.Status.APPROVED
        record_request.approver = request.user
        record_request.save()
        return Response(status=status.HTTP_200_OK)


class DenyRequestView(APIView):
    """Deny request view."""
    permission_classes = [permissions.IsAuthenticated]

    def patch(self, request, pk):
        """Deny request."""
        try:
            record_request = RecordRequest.objects.get(pk=pk)
        except RecordRequest.DoesNotExist:
            return Response(status=status.HTTP_404_NOT_FOUND)
        record_request.status = RecordRequest.Status.DENIED
        record_request.save()
        return Response(status=status.HTTP_200_OK)

class RequestsView(generics.ListCreateAPIView):
    """Handle all record requests from incoming relations."""
    permission_classes = [permissions.IsAuthenticated]
    queryset = RecordRequest.objects.all()
    serializer_class = RecordRequestSerializer

    def post(self, request):
        """Handle requests."""
        existing_rrs = RecordRequest.objects.all()

        # Add the new record requests
        for rr in request.data:
            # TODO: validate record request before setting status to pending
            rr["status"] = "pending"
            serializer = RecordRequestSerializer(data=rr)
            if not serializer.is_valid(raise_exception=True):
               continue
            existing_rr = next((r for r in existing_rrs if str(r.uuid) == rr["uuid"]), None)
            if existing_rr is not None:
                # Only the requirer can change, as the record is left to its review
                requirer_id = serializer.validated_data.get("requirer_id")
                if requirer_id is not None and existing_rr.requirer_id != requirer_id:
                    existing_rr.requirer_id = requirer_id
                    existing_rr.save(update_fields=["requirer_id"])
                continue
            serializer.save()


        # Remove the record requests absent from the query
        for rr in existing_rrs:
            if not any(r["uuid"] == str(rr.uuid) for r in request.data):
                rr.delete()

        return Response({}, status=status.HTTP_200_OK)


class DdnsAllocationsView(APIView):
    """List and allocate the automatically allocated domains."""
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        """List every domain ever allocated."""
        allocations = DdnsAllocation.objects.all()
        return Response(DdnsAllocationSerializer(allocations, many=True).data)

    def post(self, request):
        """Get the domain allocated to each relation, allocating one if it has none yet.

        The body is a list of `{"instance", "requirer_id", "parent"}` objects, and the
        response is the list of the matching allocations, in the same order.

        This is idempotent: a relation always gets back the domain it was first
        allocated under the same parent domain.

        Relations are scoped to an instance, the identifier of the charm they belong to,
        because relation ids are only unique within a single charm deployment.
        """
        serializer = DdnsAllocationRequestSerializer(data=request.data, many=True)
        serializer.is_valid(raise_exception=True)
        allocations = []
        for allocation_request in serializer.validated_data:
            try:
                allocations.append(ddns.allocate(**allocation_request))
            except ddns.DdnsAllocationError as error:
                return Response({"detail": str(error)}, status=status.HTTP_409_CONFLICT)
        return Response(DdnsAllocationSerializer(allocations, many=True).data)
