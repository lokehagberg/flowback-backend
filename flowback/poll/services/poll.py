from rest_framework.exceptions import ValidationError
from flowback.common.services import get_object, model_update
from flowback.files.services import upload_collection
from flowback.group.services.group import group_notification
from flowback.notification.services import NotificationManager
from flowback.poll.models import Poll, PollPhaseTemplate
from flowback.group.selectors import group_user_permissions
from django.utils import timezone
from datetime import datetime

from flowback.poll.services.vote import poll_proposal_vote_count
from flowback.poll.tasks import poll_area_vote_count, poll_prediction_bet_count

poll_notification = NotificationManager(sender_type='poll', possible_categories=['timeline',
                                                                                 'poll',
                                                                                 'comment_self',
                                                                                 'comment_all'])


def poll_notification_subscribe(*, user_id: int, poll_id: int, categories: list[str]):
    poll = get_object(Poll, id=poll_id)
    group_user_permissions(user=user_id, group=poll.created_by.group.id)

    poll_notification.channel_subscribe(user_id=user_id, sender_id=poll.id, category=categories)


def poll_create(*, user_id: int,
                group_id: int,
                title: str,
                description: str = None,
                blockchain_id: int = None,
                start_date: datetime,
                proposal_end_date: datetime = None,
                prediction_statement_end_date: datetime = None,
                area_vote_end_date: datetime = None,
                prediction_bet_end_date: datetime = None,
                delegate_vote_end_date: datetime = None,
                vote_end_date: datetime = None,
                end_date: datetime = None,
                poll_type: int,
                allow_fast_forward: bool = False,
                public: bool,
                tag: int = None,
                pinned: bool = None,
                dynamic: bool,
                attachments: list = None,
                quorum: int = None
                ) -> Poll:
    group_user = group_user_permissions(user=user_id, group=group_id, permissions=['create_poll', 'admin'])

    if pinned and not group_user.is_admin:
        raise ValidationError('Permission denied')

    if allow_fast_forward and not (group_user.is_admin or group_user.check_permission(poll_fast_forward=True)):
        raise ValidationError('Permission denied')

    if quorum is not None and not group_user.check_permission(poll_quorum=True) and not group_user.is_admin:
        raise ValidationError("Permission denied for custom poll quorum")

    if poll_type == Poll.PollType.SCHEDULE:
        if not end_date:
            raise ValidationError('Missing required parameter(s) for schedule poll')

        elif not dynamic:
            raise ValidationError('Schedule poll must be dynamic')

    elif not all([proposal_end_date,
                  prediction_statement_end_date,
                  area_vote_end_date,
                  prediction_bet_end_date,
                  delegate_vote_end_date,
                  vote_end_date,
                  end_date]):
        raise ValidationError('Missing required parameter(s) for generic poll')

    collection = None
    if attachments:
        collection = upload_collection(user_id=user_id,
                                       file=attachments,
                                       upload_to="group/poll/attachments")

    poll = Poll(created_by=group_user,
                title=title,
                description=description,
                start_date=start_date,
                blockchain_id=blockchain_id,
                proposal_end_date=proposal_end_date,
                prediction_statement_end_date=prediction_statement_end_date,
                area_vote_end_date=area_vote_end_date,
                prediction_bet_end_date=prediction_bet_end_date,
                delegate_vote_end_date=delegate_vote_end_date,
                vote_end_date=vote_end_date,
                end_date=end_date,
                poll_type=poll_type,
                allow_fast_forward=allow_fast_forward,
                public=public,
                tag_id=tag,
                pinned=pinned,
                dynamic=dynamic,
                quorum=quorum,
                attachments=collection)

    poll.full_clean()
    poll.save()

    # Group notification
    group_notification.create(sender_id=group_id,
                              action=poll_notification.Action.update,
                              category='poll',
                              message=f'User {group_user.user.username} created poll {poll.title}',
                              timestamp=start_date,
                              related_id=poll.id)

    poll_area_vote_count.apply_async(kwargs=dict(poll_id=poll.id), eta=poll.area_vote_end_date)
    poll_prediction_bet_count.apply_async(kwargs=dict(poll_id=poll.id), eta=poll.prediction_bet_end_date)

    # Poll notification
    for date, name, phase in poll.labels:
        poll_notification.create(sender_id=poll.id,
                                 action=poll_notification.Action.update,
                                 category='timeline',
                                 message=f'Poll {poll.title} has started {phase.replace("_", " ").capitalize()} phase')

    if poll_type == Poll.PollType.SCHEDULE:
        group_notification.create(sender_id=group_id,
                                  action=group_notification.Action.update,
                                  category='poll_schedule',
                                  message=f'Poll {poll.title} has finished, group schedule has been updated',
                                  related_id=poll.id)

    return poll


def poll_update(*, user_id: int, poll_id: int, data) -> Poll:
    poll = get_object(Poll, id=poll_id)
    group_user = group_user_permissions(user=user_id, group=poll.created_by.group.id)

    if data.get('pinned') is not None and not group_user.is_admin:
        raise ValidationError('Permission denied')

    non_side_effect_fields = ['title', 'description', 'pinned']

    poll, has_updated = model_update(instance=poll,
                                     fields=non_side_effect_fields,
                                     data=data)

    return poll


# TODO remove related notifications
def poll_delete(*, user_id: int, poll_id: int) -> None:
    poll = get_object(Poll, id=poll_id)
    group_id = poll.created_by.group.id
    group_user = group_user_permissions(user=user_id, group=group_id)

    force_deletion_access = group_user_permissions(group_user=group_user, permissions=['admin', 'force_delete_poll'],
                                                   raise_exception=False)

    if poll.created_by == group_user and not force_deletion_access:
        if poll.current_phase != 'waiting':
            raise ValidationError("Only administrators can delete ongoing/finished polls")

    else:
        group_user_permissions(group_user=group_user, permissions=['admin', 'force_delete_poll'])

    # Remove future notifications
    if poll.current_phase == 'waiting':
        group_notification.delete(sender_id=group_id, category='poll', related_id=poll.id)

    def delete_notifications_after(phase):
        poll_notification.delete(sender_id=poll_id,
                                 category='timeline',
                                 timestamp__gt=phase)

    match poll.current_phase:
        case 'waiting':
            delete_notifications_after(poll.proposal_end_date)
        case 'proposal':
            delete_notifications_after(poll.prediction_statement_end_date)
        case 'area_vote':
            delete_notifications_after(poll.area_vote_end_date)
        case 'prediction_bet':
            delete_notifications_after(poll.prediction_bet_end_date)
        case 'delegate_vote':
            delete_notifications_after(poll.delegate_vote_end_date)
        case 'vote':
            delete_notifications_after(poll.vote_end_date)
        case 'result':
            delete_notifications_after(poll.end_date)

    if poll.attachments:
        poll.attachments.delete()

    poll.delete()


def poll_fast_forward(*, user_id: int, poll_id: int, phase: str):
    poll = get_object(Poll, id=poll_id)
    group_user = group_user_permissions(user=user_id, group=poll.created_by.group.id)

    if not poll.allow_fast_forward:
        raise ValidationError("This poll can't be fast forwarded")

    if (not poll.created_by == group_user
            and not group_user_permissions(group_user=group_user, permissions=['poll_fast_forward', 'admin'])):
        raise ValidationError('User is not allowed to fast forward polls')

    poll.phase_exist(phase)

    phases = [label[2] for label in poll.labels]
    time_table = [label[2] for label in poll.time_table]
    print(time_table)

    if not poll.current_phase == 'waiting' and phases.index(phase) <= phases.index(poll.current_phase):
        raise ValidationError('Unable to fast forward poll to the same/previous phase')

    time_difference = poll.get_phase_start_date(phase) - timezone.now()

    # Save new times to dict
    for phase in time_table:
        phase_time = poll.get_phase_start_date(phase) - time_difference
        setattr(poll, poll.get_phase_start_date(phase, field_name=True), phase_time)

    poll.full_clean()
    poll.save()

    # TODO update/remove previous celery tasks
    if poll.area_vote_end_date > timezone.now():
        poll_area_vote_count.apply_async(kwargs=dict(poll_id=poll.id), eta=poll.area_vote_end_date)

    else:
        poll_area_vote_count.apply_async(kwargs=dict(poll_id=poll.id))

    if poll.prediction_bet_end_date > timezone.now():
        poll_prediction_bet_count.apply_async(kwargs=dict(poll_id=poll.id), eta=poll.prediction_bet_end_date)

    else:
        poll_prediction_bet_count.apply_async(kwargs=dict(poll_id=poll.id))

    poll_notification.shift(sender_id=poll_id,
                            category='timeline',
                            delta=time_difference)
    group_notification.shift(sender_id=group_user.group.id,
                             category='poll_schedule',
                             related_id=poll.id,
                             delta=time_difference)


def poll_phase_template_create(*, user_id: int,
                               group_id: int,
                               name: str,
                               poll_type: int,
                               poll_is_dynamic: bool,
                               area_vote_time_delta: int = None,
                               proposal_time_delta: int = None,
                               prediction_statement_time_delta: int = None,
                               prediction_bet_time_delta: int = None,
                               delegate_vote_time_delta: int = None,
                               vote_time_delta: int = None,
                               end_time_delta: int) -> PollPhaseTemplate:
    group_user = group_user_permissions(user=user_id, group=group_id, permissions=['admin'])

    template = PollPhaseTemplate(created_by_group_user=group_user,
                                 name=name,
                                 poll_type=poll_type,
                                 poll_is_dynamic=poll_is_dynamic,
                                 area_vote_time_delta=area_vote_time_delta,
                                 proposal_time_delta=proposal_time_delta,
                                 prediction_statement_time_delta=prediction_statement_time_delta,
                                 prediction_bet_time_delta=prediction_bet_time_delta,
                                 delegate_vote_time_delta=delegate_vote_time_delta,
                                 vote_time_delta=vote_time_delta,
                                 end_time_delta=end_time_delta)

    template.full_clean()
    template.save()

    return template


def poll_phase_template_update(*, user_id: int, template_id: int, data: dict):
    template = PollPhaseTemplate.objects.get(id=template_id)
    group_user_permissions(user=user_id, group=template.created_by_group_user.group, permissions=['admin'])

    non_side_effect_fields = ['name',
                              'poll_type',
                              'poll_is_dynamic',
                              'area_vote_time_delta'
                              'proposal_time_delta',
                              'prediction_statement_time_delta',
                              'prediction_bet_time_delta',
                              'delegate_vote_time_delta',
                              'vote_time_delta',
                              'end_time_delta']

    template, has_updated = model_update(instance=template,
                                         fields=non_side_effect_fields,
                                         data=data)

    return template


def poll_phase_template_delete(*, user_id: int, template_id: int):
    template = PollPhaseTemplate.objects.get(id=template_id)
    group_user_permissions(user=user_id, group=template.created_by_group_user.group, permissions=['admin'])

    template.delete()


def poll_finish(*, poll_id: int) -> None:
    poll = get_object(Poll, id=poll_id)

    if poll.status:
        raise ValidationError("Poll is already finished")

    poll_proposal_vote_count(poll_id=poll_id)
    poll.result = True
    poll.save()


def poll_refresh(*, poll_id: int) -> None:
    poll = get_object(Poll, id=poll_id)

    if not poll.dynamic:
        raise ValidationError("Attempted to refresh a poll that doesn't allow live update")

    if poll.status:
        raise ValidationError("Attempted to refresh a poll that's already finished")

    poll_proposal_vote_count(poll_id=poll_id)


# TODO setup celery
def poll_refresh_cheap(*, poll_id: int) -> None:
    poll = get_object(Poll, id=poll_id)

    if (poll.dynamic and not poll.status) or (not poll.status and timezone.now() >= poll.end_date):
        poll_proposal_vote_count(poll_id=poll_id)
