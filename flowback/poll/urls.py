from django.urls import path

from .views import (PollListApi,
                    PollCreateAPI,
                    PollUpdateAPI,
                    PollDeleteAPI, PollProposalListAPI, PollProposalDeleteAPI, PollProposalCreateAPI,
                    PollProposalVoteListAPI, PollProposalVoteUpdateAPI, PollDelegatesListAPI)


poll_patterns = [
    path('list', PollListApi.as_view(), name='polls'),
    path('create', PollCreateAPI.as_view(), name='poll_create'),
    path('<int:poll>/update', PollUpdateAPI.as_view(), name='poll_update'),
    path('<int:poll>/delete', PollDeleteAPI.as_view(), name='poll_delete'),
    path('<int:poll>/proposals', PollProposalListAPI.as_view(), name='poll_proposals'),
    path('<int:poll>/proposal/create', PollProposalCreateAPI.as_view(), name='poll_proposal_create'),
    path('<int:poll>/proposal/<int:proposal>/delete', PollProposalDeleteAPI.as_view(), name='poll_proposal_delete'),
    path('<int:poll>/proposal/votes', PollProposalVoteListAPI.as_view(), name='poll_proposal_votes'),
    path('<int:poll>/proposal/vote/update', PollProposalVoteUpdateAPI.as_view(), name='poll_proposal_vote_update'),
    path('<int:poll>/proposal/vote/delegate/update', PollProposalVoteUpdateAPI.as_view(),
         name='poll_proposal_delegate_vote_update'),
    path('<int:poll>/delegates', PollDelegatesListAPI.as_view(), name='poll_delegates')
]