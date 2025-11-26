from rest_framework.exceptions import ValidationError

from flowback.common.services import get_object
from flowback.files.services import upload_collection
from flowback.group.selectors.permission import group_user_permissions
from flowback.poll.models import PollProposal, Poll, PollProposalTypeSchedule


def poll_proposal_create(*, user_id: int,
                         poll_id: int,
                         title: str = None,
                         description: str = None,
                         attachments=None,
                         blockchain_id: int = None,
                         **data) -> PollProposal:
    poll = get_object(Poll, id=poll_id)
    group_user = group_user_permissions(user=user_id, group=poll.created_by.group.id,
                                        permissions=['create_proposal', 'admin'])

    if group_user.group.id != poll.created_by.group.id:
        raise ValidationError('Permission denied')

    poll.check_phase('proposal', 'dynamic', 'schedule')

    proposal = PollProposal(created_by=group_user,
                            poll=poll,
                            title=title,
                            description=description,
                            blockchain_id=blockchain_id)
    proposal.full_clean()

    collection = None
    if attachments:
        collection = upload_collection(user_id=user_id, file=attachments, upload_to="group/poll/proposals")

    proposal.attachments = collection
    proposal.save()

    if poll.poll_type == Poll.PollType.SCHEDULE:
        if not (data.get('start_date') and data.get('end_date')):
            raise Exception('Missing start_date and/or end_date, for proposal schedule creation')

        schedule_proposal = PollProposalTypeSchedule(proposal=proposal,
                                                     event_start_date=data['start_date'],
                                                     event_end_date=data['end_date'])

        try:
            schedule_proposal.full_clean()

        except ValidationError as e:
            proposal.delete()
            raise e

        schedule_proposal.save()

    return proposal


def poll_proposal_delete(*, user_id: int, proposal_id: int) -> None:
    proposal = get_object(PollProposal, id=proposal_id)
    group_user = group_user_permissions(user=user_id, group=proposal.created_by.group)

    if proposal.created_by == group_user and group_user.check_permission(delete_proposal=True):
        proposal.poll.check_phase('proposal', 'dynamic', 'schedule')

    elif not (group_user.check_permission(force_delete_permission=True) or group_user.is_admin):
        raise ValidationError("Deleting other users proposals needs either "
                              "group admin or force_delete_proposal permission")

    proposal.delete()
