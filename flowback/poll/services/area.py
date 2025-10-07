from rest_framework.exceptions import ValidationError

from flowback.common.services import get_object
from flowback.group.selectors.permission import group_user_permissions
from flowback.poll.models import PollAreaStatement, PollAreaStatementSegment, PollAreaStatementVote, Poll


def poll_area_statement_create(user_id: int, poll_id: int, tags: list[int]):
    if len(tags) > 1:
        raise ValidationError('Area statements can only have one tag at most')

    poll = get_object(Poll, id=poll_id)
    group_user = group_user_permissions(user=user_id, group=poll.created_by.group)

    poll.check_phase('area_vote', 'dynamic')

    # Create Statement
    poll_area_statement = PollAreaStatement(created_by=group_user, poll=poll)

    poll_area_statement.full_clean()
    poll_area_statement.save()

    # Create Segments
    poll_area_statement_segments = [PollAreaStatementSegment(poll_area_statement=poll_area_statement,
                                                             tag_id=i) for i in tags]

    for segment in poll_area_statement_segments:
        segment.full_clean()
        segment.save()

    return poll_area_statement


def poll_area_statement_vote_update(user_id: int, poll_id: int, tag: int, vote: bool):
    tags = [tag]
    poll = get_object(Poll, id=poll_id)
    group_user = group_user_permissions(user=user_id, group=poll.created_by.group)

    if not vote:
        raise ValidationError('Vote must be True')

    PollAreaStatement.objects.filter(created_by=group_user, poll=poll).delete()
    poll_area_statement = poll_area_statement_create(user_id=user_id, poll_id=poll_id, tags=tags)

    poll.check_phase('area_vote', 'dynamic')

    # Delete all votes before creating a new vote
    PollAreaStatementVote.objects.filter(created_by=group_user, poll_area_statement__poll=poll).delete()

    PollAreaStatementVote.objects.update_or_create(created_by=group_user,
                                                   poll_area_statement=poll_area_statement,
                                                   defaults=dict(vote=vote))

    return poll_area_statement
