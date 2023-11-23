from django.utils import timezone
from rest_framework.exceptions import ValidationError

from flowback.common.services import get_object
from flowback.files.services import upload_collection
from flowback.group.selectors import group_user_permissions
from flowback.poll.models import PollProposal, Poll, PollProposalTypeSchedule


# TODO proposal can be created without schedule, dangerous
from flowback.poll.services.poll import poll_refresh_cheap


def poll_proposal_create(*, user_id: int, poll_id: int,
                         title: str = None, description: str = None, attachments=None, **data) -> PollProposal:
    poll = get_object(Poll, id=poll_id)
    group_user = group_user_permissions(user=user_id, group=poll.created_by.group.id, permissions=['create_proposal', 'admin'])

    if group_user.group.id != poll.created_by.group.id:
        raise ValidationError('Permission denied')

    poll.check_phase('proposal', 'dynamic')

    proposal = PollProposal(created_by=group_user, poll=poll, title=title, description=description)
    proposal.full_clean()

    collection = None
    if attachments:
        collection = upload_collection(user_id=user_id, file=attachments, upload_to="group/poll/proposals")

    proposal.attachments = collection
    proposal.save()

    extra = []
    if poll.poll_type == Poll.PollType.SCHEDULE:
        if not data.get('start_date') and not data.get('end_date'):
            raise Exception('Missing start_date and/or end_date, for proposal schedule creation')

        extra.append(PollProposalTypeSchedule(proposal=proposal, start_date=data['start_date'],
                                              end_date=data['end_date']))

    for extension in extra:
        extension.full_clean()
        extension.save()

    return proposal


def poll_proposal_delete(*, user_id: int, proposal_id: int) -> None:
    proposal = get_object(PollProposal, id=proposal_id)
    group_user = group_user_permissions(group=proposal.group, user=user_id,
                                        permissions=['admin', 'delete_proposal' 'force_delete_proposal'],
                                        raise_exception=False)
    poll_refresh_cheap(poll_id=proposal.poll.id)  # TODO get celery

    if proposal.created_by == group_user and group_user.permission.delete_proposal:
        proposal.poll.check_phase('proposal', 'dynamic')

    elif not group_user.permission.force_delete_proposal or group_user.is_admin:
        raise ValidationError("Deleting other users proposals needs either "
                              "group admin or force_delete_proposal permission")

    proposal.delete()
