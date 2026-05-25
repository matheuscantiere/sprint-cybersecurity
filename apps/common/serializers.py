from rest_framework import serializers


class ErrorDetailSerializer(serializers.Serializer):
    code = serializers.CharField()
    message = serializers.CharField()
    details = serializers.DictField(
        child=serializers.ListField(child=serializers.CharField()), required=False
    )  # noqa: E501


class ErrorEnvelopeSerializer(serializers.Serializer):
    error = ErrorDetailSerializer()
    request_id = serializers.CharField()
