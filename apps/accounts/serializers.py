import datetime
from django.contrib.auth import authenticate
from rest_framework import serializers
from django.contrib.auth.password_validation import validate_password
from accounts.models import User, VerificationCode


class RegistrationSerializer(serializers.ModelSerializer):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._verification_code = None

    code = serializers.CharField(
        write_only=True,
        max_length=6,
        required=True
    )
    password = serializers.CharField(
        write_only=True,
        validators=[validate_password],
        min_length=8
    )

    class Meta:
        model = User
        fields = ['phone', 'email', 'status', 'company_name', 'password', 'code']
        extra_kwargs = {'password': {'write_only': True, 'min_length': 8}}

    def validate(self, attrs):
        email = attrs.get('email')
        phone = attrs.get('phone')
        code = attrs.pop('code', None)
        if not email and not phone:
            raise serializers.ValidationError('Введите телефон или почту')
        if email and User.objects.filter(email=email).exists():
            raise serializers.ValidationError('Пользователь с такой почтой уже зарегистрирован')
        if phone and User.objects.filter(phone=phone).exists():
            raise serializers.ValidationError('Пользователь с таким номером телефона уже зарегистрирован')
        if attrs.get('status') == 'EMPLOYER':
            if not attrs.get('company_name'):
                raise serializers.ValidationError('Введите название своей компании')
        if attrs.get('status') == 'APPLICANT':
            if attrs.get('company_name'):
                raise serializers.ValidationError("Соискатель не может указывать название компании")

        destination = email if email else phone
        try:
            verification_code = VerificationCode.objects.get(
                code=code,
                destination=destination,
                is_used=False
            )
        except VerificationCode.DoesNotExist:
            raise serializers.ValidationError('Такого кода не существует')

        if verification_code.is_expired():
            raise serializers.ValidationError('Время действия кода истекло')

        self._verification_code = verification_code
        return attrs

    def create(self, validated_data):
        user = User.objects.create_user(**validated_data)
        user.is_active = True
        if user.email:
            user.verify_email()
        if user.phone:
            user.verify_phone()
        user.save()
        if hasattr(self, '_verification_code'):
            self._verification_code.is_used = True
            self._verification_code.save(update_fields=['is_used'])
        return user


class CodeSerializer(serializers.ModelSerializer):
    class Meta:
        model = VerificationCode
        fields = ['code']

    def validate_code(self, value):
        if len(value) != 6:
            raise serializers.ValidationError('В коде 6 цифр')
        if not value.isdigit():
            raise serializers.ValidationError('Код должен состоять только из цифр')
        return value


class UserProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields=['id','email','first_name','last_name','phone','company_name','avatar','birth_day','status','gender']
        read_only_fields=['id','status']

    def update(self, instance, validated_data):
        if instance.email and 'email' in validated_data:
            validated_data.pop('email')
        if instance.phone and 'phone' in validated_data:
            validated_data.pop('phone')
        if instance.status != 'EMPLOYER' and 'company_name' in validated_data:
            validated_data.pop('company_name')
        return super().update(instance, validated_data)

    def to_representation(self, instance):
        representation=super().to_representation(instance)
        if instance.status != 'EMPLOYER':
            representation.pop('company_name',None)
        return representation

    def validate_birth_day(self, value):
        today = datetime.date.today()
        if value > today:
            raise serializers.ValidationError('Дата рождения не может быть в будущем')
        age=(today - value).days /365.25
        if age<14:
            raise serializers.ValidationError('Пользователь должен быть старше 14 лет')
        if value < datetime.date(1900, 1, 1):
            raise serializers.ValidationError('Дата рождения слишком ранняя')
        return value


class LoginSerializerWithPassword(serializers.Serializer):
    email = serializers.EmailField(required=False)
    phone = serializers.CharField(required=False)
    password = serializers.CharField(write_only=True)

    def validate(self, attrs):
        email = attrs.get('email')
        phone = attrs.get('phone')
        password = attrs.get('password')

        if not email and not phone:
            raise serializers.ValidationError('Введите номер телефона или адрес электронной почты')
        user = None
        if email:
            try:
                User.objects.get(email=email)
            except User.DoesNotExist:
                raise serializers.ValidationError('Пользователя с такой почтой не существует')
            user = authenticate(email=email, password=password)
        elif phone:
            try:
                User.objects.get(phone=phone)
            except User.DoesNotExist:
                raise serializers.ValidationError('Пользователя с таким номером телефона не существует')
            user = authenticate(phone=phone, password=password)
        if not user:
            raise serializers.ValidationError('Неверные данные пользователя для входа')
        attrs['user'] = user
        return attrs

class LoginSerializerWithCode(serializers.Serializer):
    email = serializers.EmailField(required=False)
    phone = serializers.CharField(required=False)
    code = serializers.CharField(max_length=6, write_only=True, required=True)

    def validate(self, attrs):
        email = attrs.get('email')
        phone = attrs.get('phone')
        code = attrs.get('code')

        if not email and not phone:
            raise serializers.ValidationError('Введите номер телефона или адрес электронной почты')

        destination = None
        if email:
            destination = email
            try:
                User.objects.get(email=email)
            except User.DoesNotExist:
                raise serializers.ValidationError('Пользователя с такой почтой не существует')
        elif phone:
            destination = phone
            try:
                User.objects.get(phone=phone)
            except User.DoesNotExist:
                raise serializers.ValidationError('Пользователя с таким номером телефона не существует')

        code_serializer = CodeSerializer(data={'code': code})
        if not code_serializer.is_valid():
            raise serializers.ValidationError(code_serializer.errors)

        try:
            verification_code = VerificationCode.objects.get(
                destination=destination,
                code=code,
                is_used=False
            )
        except VerificationCode.DoesNotExist:
            raise serializers.ValidationError('Такого кода не существует')

        if verification_code.is_expired():
            raise serializers.ValidationError('Срок действия кода уже истек')
        if email:
            user = User.objects.get(email=email)
        elif phone:
            user = User.objects.get(phone=phone)
        else:
            raise serializers.ValidationError('Пользователь не существует')
        verification_code.is_used = True
        verification_code.save(update_fields=['is_used'])

        attrs['user'] = user
        return attrs

class PasswordResetSerializer(serializers.Serializer):
    code=serializers.CharField(max_length=6, write_only=True, required=True)
    email=serializers.EmailField(required=False)
    phone=serializers.CharField(required=False)
    new_password = serializers.CharField(
        write_only=True,
        required=True,
        validators=[validate_password]
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._verification_code = None

    def validate(self, attrs):
        email = attrs.get('email')
        phone = attrs.get('phone')
        code = attrs.get('code')

        if not email and not phone:
            raise serializers.ValidationError('Введите пароль или адрес электронной почты')

        destination = email if email else phone

        code_serializer = CodeSerializer(data={'code': code})
        if not code_serializer.is_valid():
            raise serializers.ValidationError(code_serializer.errors)
        try:
            verification_code = VerificationCode.objects.get(code=code, is_used=False,destination=destination)
        except VerificationCode.DoesNotExist:
            raise serializers.ValidationError('Такого кода не существует')

        if verification_code.is_expired():
            raise serializers.ValidationError('Время действия кода истекло')

        self._verification_code = verification_code
        return attrs

    def save(self, **kwargs):
        validated_data =self.validated_data
        try:
            if validated_data.get('email'):
                user=User.objects.get(email=validated_data.get('email'))
            else:
                user=User.objects.get(phone=validated_data.get('phone'))
        except User.DoesNotExist:
            raise serializers.ValidationError('Данного пользователя не существует')

        if user.check_password(validated_data.get('new_password')):
            raise serializers.ValidationError('Пароли не должны совпадать ')

        user.set_password(validated_data.get('new_password'))
        user.save()

        self._verification_code.is_used = True
        self._verification_code.save(update_fields=['is_used'])
        return user

class SocialAuthSerializer(serializers.Serializer):
    access_token = serializers.CharField(
        help_text='Токен доступа, полученный от провайдера'
    )











