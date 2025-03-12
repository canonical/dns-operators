# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.

"""Define views."""

from rest_framework import generics, permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import RecordRequest
from .serializers import RecordRequestSerializer


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
            if any(str(r.uuid) == rr["uuid"] for r in existing_rrs):
               continue
            serializer.save()


        # Remove the record requests absent from the query
        for rr in existing_rrs:
            if not any(r["uuid"] == str(rr.uuid) for r in request.data):
                rr.delete()

        return Response({}, status=status.HTTP_200_OK)
