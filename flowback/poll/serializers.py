from rest_framework import serializers

from flowback.group.serializers import GroupUserSerializer


class PollSerializer(serializers.Serializer):
    class FileSerializer(serializers.Serializer):
        file = serializers.CharField()
        file_name = serializers.CharField()

    id = serializers.IntegerField()
    created_by = GroupUserSerializer()
    group_id = serializers.IntegerField(source='created_by.group_id')
    group_name = serializers.CharField(source='created_by.group.name')
    group_image = serializers.ImageField(source='created_by.group.image')
    tag_id = serializers.IntegerField(allow_null=True)
    tag_name = serializers.CharField(source='tag.name', allow_null=True)
    attachments = FileSerializer(many=True, source="attachments.filesegment_set", allow_null=True)
    hide_poll_users = serializers.BooleanField(source='created_by.group.hide_poll_users')

    title = serializers.CharField()
    description = serializers.CharField()
    poll_type = serializers.IntegerField()
    allow_fast_forward = serializers.BooleanField()
    public = serializers.BooleanField()

    start_date = serializers.DateTimeField(allow_null=True)
    proposal_end_date = serializers.DateTimeField(allow_null=True)
    prediction_statement_end_date = serializers.DateTimeField(allow_null=True)
    area_vote_end_date = serializers.DateTimeField(allow_null=True)
    prediction_bet_end_date = serializers.DateTimeField(allow_null=True)
    delegate_vote_end_date = serializers.DateTimeField(allow_null=True)
    vote_end_date = serializers.DateTimeField(allow_null=True)
    end_date = serializers.DateTimeField(allow_null=True)

    status = serializers.IntegerField()
    result = serializers.BooleanField()
    participants = serializers.IntegerField()
    pinned = serializers.BooleanField()
    dynamic = serializers.BooleanField()
    interval_mean_absolute_correctness = serializers.DecimalField(max_digits=12, decimal_places=9, allow_null=True)

    group_joined = serializers.BooleanField(required=False)
    total_comments = serializers.IntegerField(required=False)
    quorum = serializers.IntegerField(allow_null=True)
