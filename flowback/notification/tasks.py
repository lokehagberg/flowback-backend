# TODO Fix
# import json
#
# from django.core import serializers
# from django.db import models
# from django.core.mail import send_mass_mail
# from django.db.models import Count, Q, F, OuterRef, Subquery, Func
# from django.db.models.functions import Coalesce
# from django_celery_beat.models import IntervalSchedule, PeriodicTask
#
# from backend.celery import app
# from backend.settings import INSTANCE_NAME, DEFAULT_FROM_EMAIL
# from flowback.chat.models import DirectMessage, DirectMessageUserData
# from flowback.user.models import User
#
#
# @app.task
# def notification_send_mail(footer: str = None):
#     direct_message_userdata_subquery = DirectMessageUserData.objects.filter(
#         Q(user_id=OuterRef('user_id')) & Q(target_id=OuterRef('target_id'))).values('timestamp')[:1]
#
#     direct_message_subquery = DirectMessage.objects.filter(
#         Q(user_id=OuterRef('id')) | Q(target_id=OuterRef('id'))
#             ).annotate(last_read=Subquery(direct_message_userdata_subquery, output_field=models.DateTimeField())
#                        ).filter(created_at__gt=F('last_read')
#                                 ).annotate(unread_chat_notifications=Func('pk', function='Count')
#                                            ).values('unread_chat_notifications')
#
#     recipients = User.objects.filter(email_notifications=True, is_active=True
#                                      ).annotate(unread_notifications=Count(Q(notification__read=True)),
#                                                 unread_chat_notifications=Subquery(direct_message_subquery,
#                                                                                    output_field=models.IntegerField())
#                                                 ).filter(Q(unread_notifications__gt=0) |
#                                                          Q(unread_chat_notifications__gt=0)).all()
#
#     subject = INSTANCE_NAME
#     mails = []
#
#     for user in recipients:
#         message = []
#         if user.unread_notifications > 0:
#             message.append(f'{user.unread_notifications} unread notifications')
#
#         if user.unread_chat_notifications > 0:
#             message.append(f'{user.unread_chat_notifications} unread chat notifications')
#
#         message = f'You got {" and ".join(message)}!' + (f'\n\n{footer}' if footer else '')
#         mails.append([subject, message, DEFAULT_FROM_EMAIL, [user.email]])
#
#     if mails:
#         send_mass_mail(mails)
