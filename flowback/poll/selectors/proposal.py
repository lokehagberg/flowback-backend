import django_filters
from django.db.models import F

from flowback.common.filters import NumberInFilter, ExistsFilter
from flowback.common.services import get_object
from flowback.poll.models import Poll, PollProposal
from flowback.user.models import User
from flowback.group.selectors import group_user_permissions


class BasePollProposalFilter(django_filters.FilterSet):
    group = django_filters.NumberFilter(field_name='created_by__group_id', lookup_expr='exact')
    created_by_user_id_list = NumberInFilter(field_name='created_by__user_id')
    order_by = django_filters.OrderingFilter(fields=(('created_at', 'created_at_asc'),
                                                     ('-created_at', 'created_at_desc'),
                                                     ('score', 'score_asc'),
                                                     ('-score', 'score_desc')))
    has_attachments = ExistsFilter(field_name='attachments')

    class Meta:
        model = PollProposal
        fields = dict(id=['exact'],
                      created_by=['exact'],
                      title=['exact', 'icontains'])


class BasePollProposalScheduleFilter(django_filters.FilterSet):
    order_by = django_filters.OrderingFilter(
        fields=(
            ('start_date', 'start_date_asc'),
            ('-start_date', 'start_date_desc'),
            ('end_date', 'end_date_asc'),
            ('-end_date', 'end_date_desc')
        )
    )

    group = django_filters.NumberFilter(field_name='created_by.group_id', lookup_expr='exact')

    start_date__lt = django_filters.DateTimeFilter(field_name='pollproposaltypeschedule.event.start_date',
                                                   lookup_expr='lt')
    start_date__gte = django_filters.DateTimeFilter(field_name='pollproposaltypeschedule.event.start_date',
                                                   lookup_expr='gte')
    end_date__lt = django_filters.DateTimeFilter(field_name='pollproposaltypeschedule.event.end_date',
                                                 lookup_expr='lt')
    end_date__gte = django_filters.DateTimeFilter(field_name='pollproposaltypeschedule.event.end_date',
                                                 lookup_expr='gte')

    poll_title = django_filters.CharFilter(field_name='poll.title', lookup_expr='exact')
    poll_title__icontains = django_filters.CharFilter(field_name='poll.title', lookup_expr='icontains')

    class Meta:
        model = PollProposal
        fields = dict(id=['exact'],
                      created_by=['exact'],
                      title=['exact', 'icontains'])


def poll_proposal_list(*, fetched_by: User, poll_id: int, filters=None):
    filters = filters or {}
    fieldset = ['id', 'poll_id', 'created_by', 'title', 'description', 'attachments', 'blockchain_id', 'score']

    if poll_id:
        poll = get_object(Poll, id=poll_id)

        if not poll.public:
            group_user_permissions(user=fetched_by, group=poll.created_by.group.id)

        qs = PollProposal.objects.filter(created_by__group_id=poll.created_by.group.id, poll=poll)\
            .order_by(F('score').desc(nulls_last=True))

        if poll.created_by.group.hide_poll_users:
            fieldset.remove('created_by')
            [filters.pop(key, None) for key in ['created_by_user_id_list', 'created_by']]
            qs = qs.values(*fieldset).all()

        if poll.poll_type == Poll.PollType.SCHEDULE:
            return BasePollProposalScheduleFilter(filters, qs).qs
        else:
            return BasePollProposalFilter(filters, qs).qs


def poll_user_schedule_list(*, fetched_by: User, filters=None):
    filters = filters or {}
    qs = PollProposal.objects.filter(created_by__group__groupuser__user__in=[fetched_by],
                                     poll__poll_type=Poll.PollType.SCHEDULE,
                                     poll__status=1).order_by('poll', 'score')\
        .distinct('poll').all()

    return BasePollProposalScheduleFilter(filters, qs).qs
