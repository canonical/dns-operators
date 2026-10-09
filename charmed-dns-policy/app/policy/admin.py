# Copyright 2026 Canonical Ltd.
# See LICENSE file for licensing details.

"""Admin module registration."""

from django.contrib import admin
from django.contrib.auth.models import User
from django.db.models.query import QuerySet
from django.http import HttpRequest
from django.urls import reverse

from .models import DdnsAllocation, RecordRequest, Rule
from .rules import evaluate_rules


@admin.action(description="Approve")
def approve(modeladmin: admin.options.ModelAdmin, request: HttpRequest, queryset: QuerySet) -> None:
    """Approve record request."""
    queryset.update(status=RecordRequest.Status.APPROVED, reviewer=request.user, rule=None)
    evaluate_rules()


@admin.action(description="Deny")
def deny(modeladmin: admin.options.ModelAdmin, request: HttpRequest, queryset: QuerySet) -> None:
    """Deny record request."""
    queryset.update(status=RecordRequest.Status.DENIED, reviewer=request.user, rule=None)
    evaluate_rules()


@admin.action(description="Reset to pending (let the rules decide)")
def reset_to_pending(
    modeladmin: admin.options.ModelAdmin, request: HttpRequest, queryset: QuerySet
) -> None:
    """Drop the manual review of record requests, leaving them to the rules."""
    queryset.update(status=RecordRequest.Status.PENDING, reviewer=None)
    evaluate_rules()


class DecisionListFilter(admin.SimpleListFilter):
    """Filter the record requests by how their status was decided."""

    title = 'decision'
    parameter_name = 'decision'

    def lookups(self, request, model_admin):
        """Get the filter choices."""
        return [
            ('automatic', 'Automatic'),
            ('manual', 'Manual'),
            ('undecided', 'Undecided'),
        ]

    def queryset(self, request, queryset):
        """Filter the record requests."""
        pending = RecordRequest.Status.PENDING
        if self.value() == 'automatic':
            return queryset.filter(status=pending, rule__isnull=False)
        if self.value() == 'manual':
            return queryset.exclude(status=pending)
        if self.value() == 'undecided':
            return queryset.filter(status=pending, rule__isnull=True)
        return queryset


class RecordRequestAdmin(admin.ModelAdmin):
    """Define RecordRequest configuration in admin website."""

    def get_app_list(self, request: HttpRequest):
        """Get app list."""
        app_list = super().get_app_list(request)
        app_list.append({
            'name': 'Reviewer Interface',
            'url': reverse('approver_interface'),
        })
        return app_list

    def has_change_permission(self, request: HttpRequest, obj=None):
        """Change permission."""
        if obj is None:
            return request.user.is_superuser or request.user.groups.filter(name='Reviewers').exists()
        else:
            return request.user.is_superuser

    def has_delete_permission(self, request, obj=None):
        """Delete permission."""
        return request.user.is_superuser

    def save_model(self, request, obj, form, change):
        """Save a record request, then evaluate the rules again."""
        super().save_model(request, obj, form, change)
        evaluate_rules()

    def delete_model(self, request, obj):
        """Delete a record request, then evaluate the rules again."""
        super().delete_model(request, obj)
        evaluate_rules()

    def delete_queryset(self, request, queryset):
        """Delete record requests, then evaluate the rules again."""
        super().delete_queryset(request, queryset)
        evaluate_rules()

    @admin.display(description='Status', ordering='status')
    def decision(self, obj: RecordRequest) -> str:
        """Display the status, telling the automatic decisions apart."""
        if obj.status == RecordRequest.Status.PENDING and obj.rule is not None:
            label = RecordRequest.Status(obj.rule.action).label
            return f"{label} automatically (rule: {obj.rule})"
        return obj.get_status_display()

    actions = [approve, deny, reset_to_pending]
    list_select_related = ['rule', 'reviewer']
    readonly_fields = ['rule']
    list_per_page = 20
    list_max_show_all = 200
    search_fields = ['host_label', 'domain', 'record_type', 'record_data', 'status']
    search_help_text = 'Search by status, host label, domain, record type, or record data'
    list_display_links = ['uuid']
    list_display = [
        'host_label',
        'domain',
        'ttl',
        'record_type',
        'record_data',
        'active',
        'decision',
        'status_reason',
        'reviewer',
        'created_at',
        'last_modified_at',
        'uuid',
    ]
    list_filter = [
        'domain',
        'record_type',
        'active',
        'status',
        DecisionListFilter,
        'rule',
        'reviewer',
    ]


admin.site.register(RecordRequest, RecordRequestAdmin)


class DdnsAllocationAdmin(admin.ModelAdmin):
    """Define DdnsAllocation configuration in admin website.

    Allocations are read-only: a domain must never be reassigned or reused.
    """

    list_display = ['domain', 'instance', 'requirer_id', 'created_at']
    search_fields = ['domain', 'instance', 'requirer_id']

    def has_add_permission(self, request: HttpRequest) -> bool:
        """Check add permission."""
        return False

    def has_change_permission(self, request: HttpRequest, obj=None) -> bool:
        """Check change permission."""
        return False

    def has_delete_permission(self, request: HttpRequest, obj=None) -> bool:
        """Check delete permission."""
        return False


admin.site.register(DdnsAllocation, DdnsAllocationAdmin)


class RuleAdmin(admin.ModelAdmin):
    """Define Rule configuration in admin website.

    Saving or deleting a rule evaluates the rules again against every pending record
    request.
    """

    list_display = [
        'name', 'kind', 'domain', 'action', 'enabled', 'priority', 'last_modified_at'
    ]
    list_editable = ['enabled', 'priority']
    list_filter = ['kind', 'action', 'enabled']
    search_fields = ['name', 'domain', 'description']
    readonly_fields = ['created_at', 'last_modified_at']


admin.site.register(Rule, RuleAdmin)


class ReadOnlyUserAdmin(admin.ModelAdmin):
    """ReadOnly User for the admin site."""
    list_display = ['username', 'email', 'first_name', 'last_name', 'is_staff', 'is_active']
    list_display_links = []
    list_editable = []
    search_fields = ['username', 'email', 'first_name', 'last_name']

    def has_add_permission(self, request: HttpRequest) -> bool:
        """Check add permission."""
        return False

    def has_change_permission(self, request: HttpRequest, obj=None) -> bool:
        """Check change permission."""
        if request.user.is_superuser:
            return True
        return False

    def has_delete_permission(self, request: HttpRequest, obj=None) -> bool:
        """Check delete permission."""
        return False


admin.site.unregister(User)
admin.site.register(User, ReadOnlyUserAdmin)
