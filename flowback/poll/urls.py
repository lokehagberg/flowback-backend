from django.urls import path

from .views.poll import (PollListApi,
                         PollNotificationSubscribeApi,
                         PollCreateAPI,
                         PollFastForwardAPI,
                         PollUpdateAPI,
                         PollDeleteAPI,
                         PollDelegatesListAPI,
                         PollPriorityUpdateAPI)
from .views.proposal import PollProposalListAPI, PollProposalDeleteAPI, PollProposalCreateAPI, \
    PollProposalPriorityUpdateAPI
from .views.vote import (PollProposalVoteListAPI,
                         PollProposalVoteUpdateAPI,
                         PollProposalDelegateVoteUpdateAPI,
                         DelegatePollVoteListAPI)
from .views.comment import PollCommentListAPI, PollCommentCreateAPI, PollCommentUpdateAPI, PollCommentDeleteAPI
from .views.prediction import (PollPredictionStatementListAPI,
                               PollPredictionBetListAPI,
                               PollPredictionStatementCreateAPI,
                               PollPredictionStatementDeleteAPI,
                               PollPredictionBetCreateAPI,
                               PollPredictionBetUpdateAPI,
                               PollPredictionBetDeleteAPI,
                               PollPredictionStatementVoteCreateAPI,
                               PollPredictionStatementVoteUpdateAPI,
                               PollPredictionStatementVoteDeleteAPI)
from .views.area import PollAreaStatementListAPI, PollAreaVoteAPI

group_poll_patterns = [
    path('list', PollListApi.as_view(), name='polls'),
    path('create', PollCreateAPI.as_view(), name='poll_create'),

    path('prediction/statement/list', PollPredictionStatementListAPI.as_view(), name='poll_prediction_statement_list'),
    path('prediction/bet/list', PollPredictionBetListAPI.as_view(), name='poll_prediction_bet_list'),
]

poll_patterns = [
    path('pool/<int:delegate_pool_id>/votes', DelegatePollVoteListAPI.as_view(), name='delegate_votes'),
    path('<int:poll>/subscribe', PollNotificationSubscribeApi.as_view(), name='poll_subscribe'),
    path('<int:poll>/update', PollUpdateAPI.as_view(), name='poll_update'),
    path('<int:poll_id>/fast_forward', PollFastForwardAPI.as_view(), name='poll_fast_forward'),
    path('<int:poll>/delete', PollDeleteAPI.as_view(), name='poll_delete'),
    path('<int:poll_id>/priority/update', PollPriorityUpdateAPI.as_view(), name='poll_priority_update'),
    path('<int:poll>/proposals', PollProposalListAPI.as_view(), name='poll_proposals'),
    path('<int:poll>/proposal/create', PollProposalCreateAPI.as_view(), name='poll_proposal_create'),
    path('proposal/<int:proposal>/delete', PollProposalDeleteAPI.as_view(), name='poll_proposal_delete'),
    path('proposal/<int:proposal_id>/priority/update', PollProposalPriorityUpdateAPI.as_view(),
         name='poll_proposal_priority_update'),
    path('<int:poll>/proposal/votes', PollProposalVoteListAPI.as_view(), name='poll_proposal_votes'),
    path('<int:poll>/proposal/vote/update', PollProposalVoteUpdateAPI.as_view(), name='poll_proposal_vote_update'),
    path('<int:poll>/proposal/vote/delegate/update', PollProposalDelegateVoteUpdateAPI.as_view(),
         name='poll_proposal_delegate_vote_update'),
    path('<int:poll>/delegates', PollDelegatesListAPI.as_view(), name='poll_delegates'),
    path('<int:poll_id>/comment/list', PollCommentListAPI.as_view(), name='poll_comments'),
    path('<int:poll_id>/comment/create', PollCommentCreateAPI.as_view(), name='poll_comment_create'),
    path('<int:poll_id>/comment/<int:comment_id>/update', PollCommentUpdateAPI.as_view(), name='poll_comment_update'),
    path('<int:poll_id>/comment/<int:comment_id>/delete', PollCommentDeleteAPI.as_view(), name='poll_comment_delete'),
    path('<int:poll_id>/prediction/statement/create', PollPredictionStatementCreateAPI.as_view(),
         name='poll_prediction_statement_create'),
    path('prediction/<int:prediction_statement_id>/statement/delete', PollPredictionStatementDeleteAPI.as_view(),
         name='poll_prediction_statement_delete'),
    path('prediction/<int:prediction_statement_id>/bet/create', PollPredictionBetCreateAPI.as_view(),
         name='poll_prediction_bet_create'),
    path('prediction/<int:prediction_statement_id>/bet/update', PollPredictionBetUpdateAPI.as_view(),
         name='poll_prediction_bet_update'),
    path('prediction/<int:prediction_statement_id>/bet/delete', PollPredictionBetDeleteAPI.as_view(),
         name='poll_prediction_bet_delete'),
    path('prediction/<int:prediction_statement_id>/statement/vote/create',
         PollPredictionStatementVoteCreateAPI.as_view(),
         name='poll_prediction_statement_vote_create'),
    path('prediction/<int:prediction_statement_id>/statement/vote/update',
         PollPredictionStatementVoteUpdateAPI.as_view(),
         name='poll_prediction_statement_vote_update'),
    path('prediction/<int:prediction_statement_id>/statement/vote/delete',
         PollPredictionStatementVoteDeleteAPI.as_view(),
         name='poll_prediction_statement_vote_delete'),
    path('<int:poll_id>/area/list', PollAreaStatementListAPI.as_view(), name='poll_area_list'),
    path('<int:poll_id>/area/update', PollAreaVoteAPI.as_view(), name='poll_area_update')
]
