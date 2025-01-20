# Copyright 2024 Canonical Ltd.
# See LICENSE file for licensing details.

"""Define urls."""

from django.urls import path

from . import gui_views

urlpatterns = [
    path('pending/', gui_views.list_pending_with_action, name='list_pending_with_action'),
    path('all/', gui_views.list_all, name='list_all'),
    path('approved/', gui_views.list_approved, name='list_approved'),
    path('denied/', gui_views.list_denied, name='list_denied'),
    path('approver/approve/<uuid:pk>/', gui_views.approve_request, name='approve_request'),
    path('approver/deny/<uuid:pk>/', gui_views.deny_request, name='deny_request'),
]
