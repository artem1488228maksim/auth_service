from django.urls import path


from accounts.views import (
    CodeSendView,
    RegisterView,
    LoginWithPasswordView,
    LoginWithCodeView,
    UserProfileView,
    PasswordResetView,
    LogoutView
)
app_name='accounts'
urlpatterns = [
    path('api/send-code/', CodeSendView.as_view(), name='send-code'),
    path('api/register/', RegisterView.as_view(), name='register'),
    path('api/login/password/', LoginWithPasswordView.as_view(), name='login-with-password'),
    path('api/login/code/', LoginWithCodeView.as_view(), name='login-with-code'),
    path('api/profile/', UserProfileView.as_view(), name='user-profile'),
    path('api/password-reset/', PasswordResetView.as_view(), name='password-reset'),
    path('api/logout/', LogoutView.as_view(), name='logout'),
]