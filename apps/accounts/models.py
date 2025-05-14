from django.utils import timezone
from django.core.validators import FileExtensionValidator
from django.db.models import Q
from django.utils.translation import gettext_lazy as _
from django.db import models
from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from phonenumber_field.modelfields import PhoneNumberField


class UserAccountManager(BaseUserManager):
    def create_user(self, email=None, phone=None, password=None, **extra_fields):
        if not email and not phone:
            raise ValueError('Укажите телефон или почту')
        email = self.normalize_email(email) if email else None
        user = self.model(
            email=email,
            phone=phone,
            **extra_fields
        )
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault('is_admin', True)
        extra_fields.setdefault('is_active', True)
        extra_fields.setdefault('is_superuser', True)
        user = self.create_user(
            email=email,
            phone=None,
            password=password,
            **extra_fields
        )
        return user


class User(AbstractBaseUser, PermissionsMixin):
    STATUS_CHOICES = (
        ('APPLICANT', 'Соискатель'),
        ('EMPLOYER', 'Наниматель')
    )
    GENDER_CHOICES = (
        ('MALE','мужчина'),
        ('FEMALE','женщина'),
    )
    email = models.EmailField(
        verbose_name=_('Электронная почта'),
        max_length=255,
        unique=True,
        blank=True,
        null=True,
    )
    first_name = models.CharField(max_length=255, verbose_name=_('Имя'), blank=True)
    last_name = models.CharField(max_length=255, verbose_name=_('Фамилия'), blank=True)
    is_active = models.BooleanField(default=False, verbose_name='Активен')
    is_admin = models.BooleanField(default=False, verbose_name=_('Администратор'))
    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_('Дата создания'))
    updated_at = models.DateTimeField(auto_now=True, verbose_name=_('Дата обновления'))
    email_verified_at = models.DateTimeField(null=True, blank=True, verbose_name=_('Время подтверждения почты'))
    phone_verified_at = models.DateTimeField(null=True, blank=True, verbose_name=_('Время подтверждения телефона'))
    company_name = models.CharField(blank=True, max_length=255,verbose_name=_('Название компании'))
    gender=models.CharField(
        choices=GENDER_CHOICES,
        null=True,
        blank=True,
        max_length=6,
        verbose_name=_('Пол')
    )
    phone = PhoneNumberField(
        unique=True,
        verbose_name=_('Номер телефона'),
        blank=True,
        null=True,
        region='BY'
    )
    avatar = models.ImageField(
        verbose_name=_('Фотография пользователя'),
        upload_to='images/avatars/%Y/%m/%d',
        default='images/avatars/default.jpg',
        validators=[FileExtensionValidator(['png', 'jpg', 'jpeg'])],
        blank=True,
    )
    status = models.CharField(
        choices=STATUS_CHOICES,
        default='APPLICANT',
        max_length=9,
        verbose_name=_('Статус пользователя')
    )
    birth_day = models.DateField(verbose_name=_('Дата Рождения'), blank=True, null=True)
    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = []
    objects = UserAccountManager()

    class Meta:
        verbose_name = _('Пользователь')
        verbose_name_plural = _('Пользователи')
        ordering = ('created_at',)
        constraints = [
            models.CheckConstraint(
                check=Q(email__isnull=False) | Q(phone__isnull=False),
                name='at_least_one_contact'
            )
        ]

    def __str__(self):
        return self.email or str(self.phone)

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)

    def get_full_name(self):
        return f'{self.first_name} {self.last_name}'

    def get_short_name(self):
        return self.first_name

    def has_perm(self, perm, obj=None):
        return self.is_superuser

    def has_module_perm(self, app_label):
        return self.is_superuser

    @property
    def is_staff(self):
        return self.is_admin

    def verify_email(self):
        self.email_verified_at = timezone.now()
        self.save(update_fields=['email_verified_at'])

    def verify_phone(self):
        self.phone_verified_at = timezone.now()
        self.save(update_fields=['phone_verified_at'])


class VerificationCode(models.Model):
    TYPE_CHOICES = (
        ('EMAIL', 'email'),
        ('PHONE', 'phone')
    )
    code = models.CharField(max_length=6, verbose_name=_('Код подтверждения'))
    destination = models.CharField(max_length=100, verbose_name=_('Телефон/почта'))
    type = models.CharField(choices=TYPE_CHOICES, max_length=5, verbose_name=_('Куда'))
    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_('Время создания'))
    expired_at = models.DateTimeField(verbose_name=_('Время действия'))
    is_used = models.BooleanField(default=False)

    class Meta:
        verbose_name = _('Код верификации')
        verbose_name_plural = _('Коды верификации')

    def __str__(self):
        return f'{self.destination}-{self.code}'

    def is_expired(self):
        return self.expired_at < timezone.now()