from django.core.mail import send_mail
import random

from django.utils import timezone
from rest_framework import status
from rest_framework.exceptions import ValidationError
from rest_framework.generics import RetrieveUpdateAPIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework_simplejwt.tokens import RefreshToken
from django.core.cache import cache
from twilio.base.exceptions import TwilioRestException
from social_django.utils import psa
from accounts.models import VerificationCode
from accounts.serializers import RegistrationSerializer, LoginSerializerWithPassword, LoginSerializerWithCode, \
    UserProfileSerializer, PasswordResetSerializer, SocialAuthSerializer
from uasz_portal import settings
from twilio.rest import Client

def generate_code():
    return f'{random.randint(0,999999):06d}'

def send_on_email(email,message):
    subject='Ваш код подтверждения'
    send_mail(
        subject=subject,
        message=message,
        from_email=settings.EMAIL_HOST_USER,
        recipient_list=[email],
        fail_silently=False
    )

def send_on_phone(phone,text):
    client=Client(settings.TWILIO_ACCOUNT_SID, settings.TWILIO_AUTH_TOKEN)
    try:
        client.messages.create(
            body=text,
            from_=settings.TWILIO_MOBILE_NUMBER,
            to=phone
        )
    except TwilioRestException as e:
        print(f"Twilio Error: {e}")


def can_send_code(contact):
    last_send_time=cache.get(f'last_sent_{contact}')
    if last_send_time:
        elapsed_time=(timezone.now() - last_send_time).total_seconds()
        if elapsed_time<60:
            return False
    cache.set(f'last_sent_{contact}', timezone.now(),timeout=600)
    return True


class CodeSendView(APIView):
    def post(self, request,format=None):
        data=request.data
        email=data.get('email')
        phone=data.get('phone')

        if not email and not phone:
            raise ValidationError('Укажите номер телефона или адрес электронной почты')

        contact=email if email else phone

        if not can_send_code(contact):
            return Response({
                'message':'Код можно отправлять раз в 60 секунд'
            },status=status.HTTP_429_TOO_MANY_REQUESTS)

        code=generate_code()
        expiry=timezone.now() + timezone.timedelta(minutes=10)
        VerificationCode.objects.create(
            code=code,
            destination=contact,
            is_used=False,
            expired_at=expiry,
            type='EMAIL' if email else 'PHONE',
        )
        message=f'Ваш код подтверждения {code}'
        if email:
            send_on_email(email,message)
        elif phone:
            send_on_phone(phone,message)

        return Response({
            'message':'Код подтверждения отправлен',
            'expired_at':expiry,
            'contact':contact,
        },status=status.HTTP_200_OK)

class RegisterView(APIView):
    def post(self,request,format=None):
        serializer=RegistrationSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user=serializer.save()

        refresh=RefreshToken.for_user(user)
        tokens={
            'refresh': str(refresh),
            'access': str(refresh.access_token),
        }
        return Response({
            'message':'Пользователь успешно создан',
            'user_id':user.id,
            'tokens':tokens
        },status=status.HTTP_201_CREATED)

class LoginWithPasswordView(APIView):
    def post(self,request,format=None):
        serializer=LoginSerializerWithPassword(data=request.data)
        serializer.is_valid(raise_exception=True)
        user=serializer.validated_data.get('user')

        refresh=RefreshToken.for_user(user)
        tokens={
            'refresh': str(refresh),
            'access':str(refresh.access_token),
        }

        return Response({
            'message':'Вход по паролю выполнен успешно',
            'user_id':user.id,
            'tokens':tokens
        },status=status.HTTP_200_OK)


class LoginWithCodeView(APIView):
    def post(self,request,format=None):
        serializer=LoginSerializerWithCode(data=request.data)
        serializer.is_valid(raise_exception=True)
        user=serializer.validated_data.get('user')

        refresh=RefreshToken.for_user(user)

        tokens={
            'refresh': str(refresh),
            'access': str(refresh.access_token),
        }

        return Response({
            'message':'Вход по коду выполнен успешно',
            'user_id':user.id,
            'tokens':tokens
        },status=status.HTTP_200_OK)


class UserProfileView(RetrieveUpdateAPIView):
    serializer_class=UserProfileSerializer
    permission_classes=[IsAuthenticated]

    def get_object(self):
        return self.request.user

class PasswordResetView(APIView):
    def post(self,request,format=None):
        serializer=PasswordResetSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user=serializer.save()

        return Response({
            'message':'Пароль успешно изменён',
            'user_id':user.id,
        },status=status.HTTP_200_OK)


class LogoutView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self,request,format=None):
        try:
            refresh_token=request.data.get('refresh')
            token=RefreshToken(refresh_token)
            token.blacklist()
            return Response({
                'message': 'Пользователь успешно вышел'
            },status=status.HTTP_205_RESET_CONTENT)
        except Exception as e:
            return Response(status=status.HTTP_400_BAD_REQUEST)


# class SocialLoginView(APIView):
#     @psa('social:complete')
#     def post(self,request,*args, **kwargs):
#         serializer=SocialAuthSerializer(data=request.data)
#         serializer.is_valid(raise_exception=True)
#         user=request.backend.do_auth(serializer.validated_data.get('access_token'))
#         if user and user.is_active:
#             refresh=RefreshToken.for_user(user)
#             tokens={
#                 'refresh': str(refresh),
#                 'access': str(refresh.access_token),
#             }
#             return Response({
#                 'message':'Oauth аутентификация удалась',
#                 'user_id':user.id,
#                 'tokens':tokens
#             },status=status.HTTP_200_OK)
#         else:
#             return Response({
#                 'error':'Ошибка аутентификации'
#             },status=status.HTTP_400_BAD_REQUEST)

