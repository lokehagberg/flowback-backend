from rest_framework.exceptions import ValidationError
from rest_framework import status
from rest_framework.test import APIRequestFactory, force_authenticate, APITestCase

from flowback.comment.models import Comment
from flowback.comment.services import comment_delete, comment_update
from flowback.comment.tests.factories import CommentSectionFactory, CommentFactory, CommentVoteFactory
from flowback.comment.views import CommentListAPI, CommentVoteAPI, CommentAncestorListAPI
from flowback.user.tests.factories import UserFactory


class CommentSectionTest(APITestCase):
    def setUp(self):
        self.comment_section = CommentSectionFactory()

    # Tests if the comment_list API gives a tree structure that's ordered properly
    def test_comment_list(self):
        # Floor 0
        comment: Comment = CommentFactory(comment_section=self.comment_section, post__score=2)
        comment_b: Comment = CommentFactory(comment_section=self.comment_section, post__score=10)

        # Floor 1
        comment_1: Comment = CommentFactory(comment_section=self.comment_section, parent=comment, post__score=7)
        comment_2: Comment = CommentFactory(comment_section=self.comment_section, parent=comment, post__score=5)

        # Floor 2
        comment_11: Comment = CommentFactory(comment_section=self.comment_section, parent=comment_1, post__score=2)
        comment_21: Comment = CommentFactory(comment_section=self.comment_section, parent=comment_2, post__score=3)
        comment_22: Comment = CommentFactory(comment_section=self.comment_section, parent=comment_2)

        # Floor 3
        comment_111: Comment = CommentFactory(comment_section=self.comment_section, parent=comment_11, post__score=9)
        comment_112: Comment = CommentFactory(comment_section=self.comment_section, parent=comment_11)

        factory = APIRequestFactory()
        view = CommentListAPI.as_view()

        # Test all results
        request = factory.get('')
        force_authenticate(request, user=comment.author)
        response = view(request, comment_section_id=self.comment_section.id)

        expected_order = [comment_b.id, comment.id, comment_1.id, comment_11.id, comment_111.id, comment_112.id,
                          comment_2.id, comment_21.id, comment_22.id]

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data.get('results')), 9, 'Missing comments in tree')
        self.assertTrue(all([x.get('id') == expected_order[i] for i, x in enumerate(response.data.get('results'))]),
                        'Comments are not ordered by score')

        # Test filter by specific id and get related children
        request = factory.get('', data=dict(id=comment_1.id))
        force_authenticate(request, user=comment.author)
        response = view(request, comment_section_id=self.comment_section.id)

        expected_order = [comment_1.id, comment_11.id, comment_111.id, comment_112.id]

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data.get('results')), 4, 'Missing comments in tree')
        self.assertTrue(all([x.get('id') == expected_order[i] for i, x in enumerate(response.data.get('results'))]),
                        'Comments are not ordered by score')

        # Test ancestor list and get related parents
        factory = APIRequestFactory()
        view = CommentAncestorListAPI.as_view()

        request = factory.get('')
        force_authenticate(request, user=comment.author)
        response = view(request, comment_section_id=self.comment_section.id, comment_id=comment_22.id)

        expected_order = [comment_22.id, comment_2.id, comment.id]

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data.get('results')), 3, 'Missing comments in tree')
        self.assertTrue(all([x.get('id') == expected_order[i] for i, x in enumerate(response.data.get('results'))]),
                        'Comments are not ordered by ancestors')


    def test_comment_update(self):
        user_one = UserFactory()
        user_two = UserFactory()

        comment = CommentFactory(comment_section=self.comment_section, author=user_one)

        with self.assertRaises(ValidationError):
            comment_update(fetched_by=user_two.id, comment_section_id=self.comment_section, comment_id=comment.id, data=dict(message="Hello"))

        comment_update(fetched_by=user_one.id,
                       comment_section_id=self.comment_section,
                       comment_id=comment.id,
                       data=dict(message="Hello there"))

        self.assertEqual(Comment.objects.get(id=comment.id).message, "Hello there")


    def test_comment_delete(self):
        user_one = UserFactory()
        user_two = UserFactory()

        comment = CommentFactory(comment_section=self.comment_section, author=user_one)

        with self.assertRaises(ValidationError):
            comment_delete(fetched_by=user_two.id, comment_section_id=self.comment_section, comment_id=comment.id)

        comment_delete(fetched_by=user_one.id, comment_section_id=self.comment_section, comment_id=comment.id)


    # Test if the algorithm prioritizes potentially higher score comments
    def test_comment_vote(self):
        # Floor 2
        comment: Comment = CommentFactory(comment_section=self.comment_section)
        comment_two: Comment = CommentFactory(comment_section=self.comment_section)

        comment_vote_positive = [CommentVoteFactory(comment=comment, vote=True) for x in range(40)]
        comment_vote_negative = [CommentVoteFactory(comment=comment, vote=False) for x in range(20)]

        comment_two_vote_positive = [CommentVoteFactory(comment=comment_two, vote=True) for x in range(10)]
        comment_two_vote_negative = [CommentVoteFactory(comment=comment_two, vote=False) for x in range(1)]

        comment.refresh_from_db()
        comment_two.refresh_from_db()
        self.assertGreater(comment_two.score, comment.score)

        previous_comment_score = comment.score

        factory = APIRequestFactory()
        view = CommentVoteAPI.as_view()

        request = factory.post('', data=dict(vote=False))
        force_authenticate(request, user=comment_vote_positive[0].created_by)
        response = view(request, comment_section_id=self.comment_section.id, comment_id=comment.id)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        comment.refresh_from_db()

        self.assertLess(comment.score, previous_comment_score)
