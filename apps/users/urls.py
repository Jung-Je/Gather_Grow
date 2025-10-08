from django.urls import path

from apps.users.views.authentication_views import (
    PasswordResetView,
    UserLoginView,
    UserLogoutView,
    UserRefreshTokenView,
    UserSignUpView,
)
from apps.users.views.email_view import (
    PasswordResetEmailCodeView,
    SignUpEmailCodeView,
    VerifyPasswordResetCodeView,
    VerifySignUpCodeView,
)
from apps.users.views.mypage_views import PasswordChangeView, ProfileView
from apps.users.views.oauth_view import GoogleLoginView, KakaoLoginView, NaverLoginView

app_name = "users"

urlpatterns = [
    # 인증 관련
    path("signup/", UserSignUpView.as_view(), name="signup"),
    path("login/", UserLoginView.as_view(), name="login"),
    path("logout/", UserLogoutView.as_view(), name="logout"),
    path("refresh/", UserRefreshTokenView.as_view(), name="refresh-token"),
    # 이메일 인증 - 회원가입
    path("email/signup/send/", SignUpEmailCodeView.as_view(), name="signup-email-send"),
    path(
        "email/signup/verify/",
        VerifySignUpCodeView.as_view(),
        name="signup-email-verify",
    ),
    # 이메일 인증 - 비밀번호 찾기
    path(
        "email/password-reset/send/",
        PasswordResetEmailCodeView.as_view(),
        name="password-reset-email-send",
    ),
    path(
        "email/password-reset/verify/",
        VerifyPasswordResetCodeView.as_view(),
        name="password-reset-email-verify",
    ),
    # 비밀번호 관리
    path("password-reset/", PasswordResetView.as_view(), name="password-reset"),
    # 소셜 로그인
    path("social/google/", GoogleLoginView.as_view(), name="google-login"),
    path("social/naver/", NaverLoginView.as_view(), name="naver-login"),
    path("social/kakao/", KakaoLoginView.as_view(), name="kakao-login"),
    # 프로필
    path("profile/", ProfileView.as_view(), name="profile"),
    path("password-change/", PasswordChangeView.as_view(), name="password-change"),
]
