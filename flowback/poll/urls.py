from django.urls import path

from .views import (PollListApi,
                    PollNotificationSubscribeApi,
                    PollCreateAPI,
                    PollUpdateAPI,
                    PollDeleteAPI, PollProposalListAPI, PollProposalDeleteAPI, PollProposalCreateAPI,
                    PollProposalVoteListAPI, PollProposalVoteUpdateAPI, PollDelegatesListAPI,
                    PollProposalDelegateVoteUpdateAPI,
                    PollCommentListAPI, PollCommentCreateAPI, PollCommentUpdateAPI, PollCommentDeleteAPI,
                    DelegatePollVoteListAPI,
                    PollPredictionStatementListAPI, PollPredictionListAPI,
                    PollPredictionStatementCreateAPI, PollPredictionStatementDeleteAPI,
                    PollPredictionCreateAPI, PollPredictionUpdateAPI, PollPredictionDeleteAPI,
                    PollPredictionStatementVoteCreateAPI,
                    PollPredictionStatementVoteUpdateAPI,
                    PollPredictionStatementVoteDeleteAPI)


group_poll_patterns = [
    path('list', PollListApi.as_view(), name='polls'),
    path('create', PollCreateAPI.as_view(), name='poll_create'),

    path('prediction/statement/list', PollPredictionListAPI.as_view(), name='poll_prediction_statement_list'),
    path('prediction/list', PollPredictionListAPI.as_view(), name='poll_prediction_list'),
]


poll_patterns = [
    path('pool/<int:delegate_pool_id>/votes', DelegatePollVoteListAPI.as_view(), name='delegate_votes'),
    path('<int:poll>/subscribe', PollNotificationSubscribeApi.as_view(), name='poll_subscribe'),
    path('<int:poll>/update', PollUpdateAPI.as_view(), name='poll_update'),
    path('<int:poll>/delete', PollDeleteAPI.as_view(), name='poll_delete'),
    path('<int:poll>/proposals', PollProposalListAPI.as_view(), name='poll_proposals'),
    path('<int:poll>/proposal/create', PollProposalCreateAPI.as_view(), name='poll_proposal_create'),
    path('proposal/<int:proposal>/delete', PollProposalDeleteAPI.as_view(), name='poll_proposal_delete'),
    path('<int:poll>/proposal/votes', PollProposalVoteListAPI.as_view(), name='poll_proposal_votes'),
    path('<int:poll>/proposal/vote/update', PollProposalVoteUpdateAPI.as_view(), name='poll_proposal_vote_update'),
    path('<int:poll>/proposal/vote/delegate/update', PollProposalDelegateVoteUpdateAPI.as_view(),
         name='poll_proposal_delegate_vote_update'),
    path('<int:poll>/delegates', PollDelegatesListAPI.as_view(), name='poll_delegates'),
    path('<int:poll>/comment/list', PollCommentListAPI.as_view(), name='poll_comments'),
    path('<int:poll>/comment/create', PollCommentCreateAPI.as_view(), name='poll_comment_create'),
    path('<int:poll>/comment/<int:comment_id>/update', PollCommentUpdateAPI.as_view(), name='poll_comment_update'),
    path('<int:poll>/comment/<int:comment_id>/delete', PollCommentDeleteAPI.as_view(), name='poll_comment_delete'),

    path('<int:poll_id>/prediction/statement/create', PollPredictionStatementCreateAPI.as_view(),
         name='poll_prediction_statement_create'),
    path('prediction/<int:prediction_statement_id>/statement/delete', PollPredictionStatementDeleteAPI.as_view(),
         name='poll_prediction_statement_delete'),
    path('<int:prediction_statement_id>/prediction/create', PollPredictionCreateAPI.as_view(),
         name='poll_prediction_create'),
    path('<int:prediction_id>/prediction/update', PollPredictionUpdateAPI.as_view(),
         name='poll_prediction_update'),
    path('<int:prediction_id>/prediction/delete', PollPredictionDeleteAPI.as_view(),
         name='poll_prediction_delete'),
    path('prediction/<int:prediction_statement_id>/statement/vote/create',
         PollPredictionStatementVoteCreateAPI.as_view(),
         name='poll_prediction_statement_vote_create'),
    path('prediction/statement/vote/<int:prediction_statement_vote_id>/update',
         PollPredictionStatementVoteUpdateAPI.as_view(),
         name='poll_prediction_statement_vote_update'),
    path('prediction/statement/vote/<int:prediction_statement_vote_id>/delete',
         PollPredictionStatementVoteDeleteAPI.as_view(),
         name='poll_prediction_statement_vote_delete'),
]
