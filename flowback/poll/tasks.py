from celery import shared_task
from django.db.models import Count, Q

from flowback.common.services import get_object
from flowback.group.models import GroupTags
from flowback.poll.models import Poll, PollAreaStatement


@shared_task
def poll_area_vote_count(poll_id: int):
    poll = get_object(Poll, id=poll_id)
    statement = PollAreaStatement.objects.filter(poll=poll).annotate(
        result=Count('pollareastatementvote', filter=Q(pollareastatementvote__vote=True)) -
               Count('pollareastatementvote', filter=Q(pollareastatementvote__vote=False))).order_by('-result').first()

    if statement:
        tag = GroupTags.objects.filter(pollareastatementsegment__poll_area_statement_id=statement).first()
        poll.tag = tag
        poll.save()

        # Clean all area tag votes, we won't need it anymore
        PollAreaStatement.objects.filter(poll=poll).delete()

    return poll
