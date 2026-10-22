from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.exceptions import TokenError
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.views import TokenObtainPairView

from .permissions import IsOwner


def user_data(user):
    return {'id': user.id, 'username': user.username, 'email': user.email}


class LoginSerializer(TokenObtainPairSerializer):
    def validate(self, attrs):
        data = super().validate(attrs)
        data['user'] = user_data(self.user)
        return data


class LoginView(TokenObtainPairView):
    serializer_class = LoginSerializer


class LogoutView(APIView):
    permission_classes = [IsOwner]

    def post(self, request):
        token = request.data.get('refresh')
        if not token:
            return Response({'refresh': ['This field is required.']}, status=400)
        try:
            RefreshToken(token).blacklist()
        except TokenError:
            return Response({'detail': 'Invalid or expired token.'}, status=400)
        return Response(status=205)


class MeView(APIView):
    permission_classes = [IsOwner]

    def get(self, request):
        return Response(user_data(request.user))


class ChangePasswordView(APIView):
    permission_classes = [IsOwner]

    def post(self, request):
        old = request.data.get('old_password')
        new = request.data.get('new_password')
        errors = {}
        if not old:
            errors['old_password'] = ['This field is required.']
        if not new:
            errors['new_password'] = ['This field is required.']
        if errors:
            return Response(errors, status=400)
        if not request.user.check_password(old):
            return Response({'old_password': ['Old password is incorrect.']}, status=400)
        try:
            validate_password(new, request.user)
        except DjangoValidationError as e:
            return Response({'new_password': list(e.messages)}, status=400)
        request.user.set_password(new)
        request.user.save()
        return Response({'detail': 'Password changed successfully.'})