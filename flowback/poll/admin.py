from django.contrib import admin
from .models import Poll, PollProposal, PollPredictionBet, PollPhaseTemplate, PollAreaStatement, PollAreaStatementVote, PollAreaStatementSegment


@admin.register(Poll)
class PollAdmin(admin.ModelAdmin):
    list_display = ('title', 'poll_type', 'active', 'public', 'start_date', 'end_date')
    list_filter = ('poll_type', 'active', 'public')
    search_fields = ('title', 'description')
    date_hierarchy = 'start_date'
    fieldsets = (
        (None, {
            'fields': ('created_by', 'title', 'description', 'poll_type', 'tag')
        }),
        ('Visibility', {
            'fields': ('active', 'public')
        }),
        ('Dates', {
            'fields': (
            'start_date', 'area_vote_end_date', 'proposal_end_date', 'prediction_statement_end_date', 'prediction_bet_end_date', 'delegate_vote_end_date', 'vote_end_date', 'end_date')
        }),
        ('Optional Dynamic Counting Support', {
            'fields': ('dynamic',)
        }),
    )
    ordering = ('-created_by', 'created_by')


@admin.register(PollProposal)
class PollProposalAdmin(admin.ModelAdmin):
    list_display = ('poll', 'title', 'description', 'score', 'created_by')


@admin.register(PollPredictionBet)
class PollPredictionAdmin(admin.ModelAdmin):
    list_display = ('prediction_statement', 'created_by')


@admin.register(PollPhaseTemplate)
class PollPhaseTemplateAdmin(admin.ModelAdmin):
    list_display = ('name',
                    'poll_type',
                    'poll_is_dynamic',
                    'created_by_group_user')

    list_filter = ('created_by_group_user', 'poll_type', 'poll_is_dynamic')
    search_fields = ('name',)
    date_hierarchy = 'created_at'

    fieldsets = (
        ('General', dict(fields=['created_by_group_user',
                                 'poll_type',
                                 'poll_is_dynamic'])),

        ('Delta', dict(fields=['area_vote_time_delta'
                               'proposal_time_delta',
                               'prediction_statement_time_delta',
                               'prediction_bet_time_delta',
                               'delegate_vote_time_delta',
                               'vote_time_delta',
                               'end_time_delta']))
    )

    ordering = ('-created_at', 'created_at')


@admin.register(PollAreaStatement)
class PollAreaStatementAdmin(admin.ModelAdmin):
    list_display = ('poll', 'created_by', 'created_at')
    list_filter = ('created_at',)
    search_fields = ('poll__title', 'created_by__user__username')
    date_hierarchy = 'created_at'


@admin.register(PollAreaStatementVote)
class PollAreaStatementVoteAdmin(admin.ModelAdmin):
    list_display = ('poll_area_statement', 'created_by', 'vote', 'created_at')
    list_filter = ('vote', 'created_at')
    search_fields = ('poll_area_statement__poll__title', 'created_by__user__username')
    date_hierarchy = 'created_at'


@admin.register(PollAreaStatementSegment)
class PollAreaStatementSegmentAdmin(admin.ModelAdmin):
    list_display = ('poll_area_statement', 'tag', 'created_at')
    list_filter = ('tag', 'created_at')
    search_fields = ('poll_area_statement__poll__title', 'tag__name')
    date_hierarchy = 'created_at'
