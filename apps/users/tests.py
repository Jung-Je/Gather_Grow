import json
from datetime import timedelta
from unittest.mock import Mock, patch

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APIClient, APITestCase
from rest_framework_simplejwt.tokens import RefreshToken

User = get_user_model()


class BaseUserTestCase(APITestCase):
    """사용자 테스트 기본 클래스"""

    def setUp(self):
        """테스트 기본 설정"""
        self.client = APIClient()
        self.test_email = "test@example.com"
        self.test_password = "TestPass123!@#"
        self.test_username = "testuser"

    def create_user(self, **kwargs):
        """테스트용 사용자 생성"""
        defaults = {
            "email": self.test_email,
            "username": self.test_username,
            "password": self.test_password,
            "joined_type": "normal",
        }
        defaults.update(kwargs)
        user = User.objects.create_user(**defaults)
        return user

    def authenticate_user(self, user=None):
        """사용자 인증 헤더 설정"""
        if not user:
            user = self.create_user()
        self.client.force_authenticate(user=user)
        return user


class SignUpTestCase(BaseUserTestCase):
    """회원가입 테스트"""

    def test_signup_with_email_verification(self):
        """이메일 인증 후 회원가입 성공"""
        # 이메일 인증 캐시 설정
        cache.set(f"signup_email_verified:{self.test_email}", True, timeout=300)

        url = reverse("users:signup")
        data = {
            "email": self.test_email,
            "password": self.test_password,
            "username": self.test_username,
            "role": "user",
            "joined_type": "normal",
            "agreed_policy": True,
        }

        response = self.client.post(url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertIn("message", response.data)
        self.assertEqual(response.data["message"], "회원가입이 완료되었습니다.")

        # 사용자 생성 확인
        user = User.objects.get(email=self.test_email)
        self.assertEqual(user.username, self.test_username)
        self.assertTrue(user.check_password(self.test_password))

    def test_signup_without_email_verification(self):
        """이메일 인증 없이 회원가입 실패"""
        url = reverse("users:signup")
        data = {
            "email": self.test_email,
            "password": self.test_password,
            "username": self.test_username,
            "role": "user",
            "joined_type": "normal",
            "agreed_policy": True,
        }

        response = self.client.post(url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("message", response.data)

    def test_signup_duplicate_email(self):
        """중복 이메일로 회원가입 실패"""
        # 기존 사용자 생성
        self.create_user()

        # 이메일 인증 캐시 설정
        cache.set(f"signup_email_verified:{self.test_email}", True, timeout=300)

        url = reverse("users:signup")
        data = {
            "email": self.test_email,
            "password": "NewPass123!@#",
            "username": "newuser",
            "role": "user",
            "joined_type": "normal",
            "agreed_policy": True,
        }

        response = self.client.post(url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_signup_invalid_password(self):
        """유효하지 않은 비밀번호로 회원가입 실패"""
        cache.set(f"signup_email_verified:{self.test_email}", True, timeout=300)

        url = reverse("users:signup")
        data = {
            "email": self.test_email,
            "password": "weak",  # 너무 짧은 비밀번호
            "username": self.test_username,
            "role": "user",
            "joined_type": "normal",
            "agreed_policy": True,
        }

        response = self.client.post(url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)


class LoginTestCase(BaseUserTestCase):
    """로그인 테스트"""

    def test_login_success(self):
        """정상 로그인"""
        user = self.create_user()
        url = reverse("users:login")
        data = {"email": self.test_email, "password": self.test_password}

        response = self.client.post(url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("message", response.data)
        self.assertEqual(response.data["message"], "로그인에 성공했습니다.")

        # 쿠키 확인
        self.assertIn("access_token", response.cookies)
        self.assertIn("refresh_token", response.cookies)

    def test_login_wrong_password(self):
        """잘못된 비밀번호로 로그인 실패"""
        user = self.create_user()
        url = reverse("users:login")
        data = {"email": self.test_email, "password": "WrongPass123!"}

        response = self.client.post(url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        # 실패 횟수 증가 확인
        user.refresh_from_db()
        self.assertEqual(user.failed_login_attempts, 1)

    def test_login_nonexistent_user(self):
        """존재하지 않는 사용자로 로그인 실패"""
        url = reverse("users:login")
        data = {"email": "nonexistent@example.com", "password": self.test_password}

        response = self.client.post(url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_login_lockout_after_failures(self):
        """5회 실패 후 계정 잠금"""
        user = self.create_user()
        user.failed_login_attempts = 5
        user.last_failed_login = timezone.now()
        user.save()

        url = reverse("users:login")
        data = {"email": self.test_email, "password": self.test_password}

        response = self.client.post(url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("로그인 시도 횟수를 초과했습니다", response.data["message"])

    def test_login_reset_after_lockout_period(self):
        """30분 후 로그인 시도 횟수 초기화"""
        user = self.create_user()
        user.failed_login_attempts = 5
        user.last_failed_login = timezone.now() - timedelta(minutes=31)
        user.save()

        url = reverse("users:login")
        data = {"email": self.test_email, "password": self.test_password}

        response = self.client.post(url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        user.refresh_from_db()
        self.assertEqual(user.failed_login_attempts, 0)


class TokenRefreshTestCase(BaseUserTestCase):
    """토큰 갱신 테스트"""

    def test_refresh_token_success(self):
        """토큰 갱신 성공"""
        user = self.create_user()
        refresh = RefreshToken.for_user(user)

        # 쿠키에 리프레시 토큰 설정
        self.client.cookies["refresh_token"] = str(refresh)

        url = reverse("users:refresh-token")
        response = self.client.post(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("access_token", response.cookies)
        self.assertIn("refresh_token", response.cookies)

    def test_refresh_token_without_token(self):
        """리프레시 토큰 없이 갱신 실패"""
        url = reverse("users:refresh-token")
        response = self.client.post(url)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data["message"], "리프레시 토큰이 필요합니다.")

    def test_refresh_token_invalid(self):
        """유효하지 않은 리프레시 토큰으로 갱신 실패"""
        self.client.cookies["refresh_token"] = "invalid_token"

        url = reverse("users:refresh-token")
        response = self.client.post(url)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)


class LogoutTestCase(BaseUserTestCase):
    """로그아웃 테스트"""

    def test_logout_success(self):
        """정상 로그아웃"""
        user = self.create_user()
        refresh = RefreshToken.for_user(user)
        self.authenticate_user(user)

        # 쿠키에 리프레시 토큰 설정
        self.client.cookies["refresh_token"] = str(refresh)

        url = reverse("users:logout")
        response = self.client.post(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["message"], "로그아웃되었습니다.")

    def test_logout_without_auth(self):
        """인증 없이 로그아웃 실패"""
        url = reverse("users:logout")
        response = self.client.post(url)

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_logout_without_refresh_token(self):
        """리프레시 토큰 없이 로그아웃 실패"""
        user = self.create_user()
        self.authenticate_user(user)

        url = reverse("users:logout")
        response = self.client.post(url)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)


class PasswordResetTestCase(BaseUserTestCase):
    """비밀번호 재설정 테스트"""

    def test_password_reset_with_verification(self):
        """이메일 인증 후 비밀번호 재설정 성공"""
        user = self.create_user()

        # 이메일 인증 캐시 설정
        cache.set(f"password_reset_verified:{self.test_email}", True, timeout=300)

        url = reverse("users:password-reset")
        data = {
            "email": self.test_email,
            "password": "NewPass123!@#",
            "confirm_password": "NewPass123!@#",
        }

        response = self.client.post(url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["message"], "비밀번호가 성공적으로 변경되었습니다.")

        # 새 비밀번호로 로그인 확인
        user.refresh_from_db()
        self.assertTrue(user.check_password("NewPass123!@#"))

    def test_password_reset_without_verification(self):
        """이메일 인증 없이 비밀번호 재설정 실패"""
        user = self.create_user()

        url = reverse("users:password-reset")
        data = {
            "email": self.test_email,
            "password": "NewPass123!@#",
            "confirm_password": "NewPass123!@#",
        }

        response = self.client.post(url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_password_reset_password_mismatch(self):
        """비밀번호 확인 불일치"""
        user = self.create_user()
        cache.set(f"password_reset_verified:{self.test_email}", True, timeout=300)

        url = reverse("users:password-reset")
        data = {
            "email": self.test_email,
            "password": "NewPass123!@#",
            "confirm_password": "DifferentPass123!@#",
        }

        response = self.client.post(url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data["message"], "비밀번호가 일치하지 않습니다.")

    def test_password_reset_invalid_password(self):
        """유효하지 않은 비밀번호로 재설정 실패"""
        user = self.create_user()
        cache.set(f"password_reset_verified:{self.test_email}", True, timeout=300)

        url = reverse("users:password-reset")
        data = {
            "email": self.test_email,
            "password": "weak",
            "confirm_password": "weak",
        }

        response = self.client.post(url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)


class ProfileTestCase(BaseUserTestCase):
    """프로필 테스트"""

    def test_get_profile(self):
        """프로필 조회"""
        user = self.create_user()
        self.authenticate_user(user)

        url = reverse("users:profile")
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["data"]["email"], self.test_email)
        self.assertEqual(response.data["data"]["username"], self.test_username)

    def test_get_profile_without_auth(self):
        """인증 없이 프로필 조회 실패"""
        url = reverse("users:profile")
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_update_profile(self):
        """프로필 수정"""
        user = self.create_user()
        self.authenticate_user(user)

        url = reverse("users:profile")
        data = {
            "username": "newusername",
            "profile": "I am a developer",
            "education_level": "university_student",
            "location": "Seoul",
        }

        response = self.client.patch(url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["message"], "프로필 수정 성공")

        user.refresh_from_db()
        self.assertEqual(user.username, "newusername")
        self.assertEqual(user.profile, "I am a developer")
        self.assertEqual(user.education_level, "university_student")
        self.assertEqual(user.location, "Seoul")

    def test_update_profile_partial(self):
        """프로필 부분 수정"""
        user = self.create_user()
        self.authenticate_user(user)

        url = reverse("users:profile")
        data = {"username": "partialupdate"}

        response = self.client.patch(url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        user.refresh_from_db()
        self.assertEqual(user.username, "partialupdate")


class PasswordChangeTestCase(BaseUserTestCase):
    """비밀번호 변경 테스트 (마이페이지)"""

    def test_password_change_success(self):
        """비밀번호 변경 성공"""
        user = self.create_user()
        self.authenticate_user(user)

        url = reverse("users:password-change")
        data = {
            "old_password": self.test_password,
            "new_password": "NewPass456!@#",
            "confirm_new_password": "NewPass456!@#",
        }

        response = self.client.patch(url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["message"], "비밀번호가 성공적으로 변경되었습니다.")

        user.refresh_from_db()
        self.assertTrue(user.check_password("NewPass456!@#"))

    def test_password_change_wrong_old_password(self):
        """잘못된 현재 비밀번호로 변경 실패"""
        user = self.create_user()
        self.authenticate_user(user)

        url = reverse("users:password-change")
        data = {
            "old_password": "WrongOldPass123!",
            "new_password": "NewPass456!@#",
            "confirm_new_password": "NewPass456!@#",
        }

        response = self.client.patch(url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_password_change_mismatch(self):
        """새 비밀번호 확인 불일치"""
        user = self.create_user()
        self.authenticate_user(user)

        url = reverse("users:password-change")
        data = {
            "old_password": self.test_password,
            "new_password": "NewPass456!@#",
            "confirm_new_password": "DifferentPass456!@#",
        }

        response = self.client.patch(url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_password_change_invalid_new_password(self):
        """유효하지 않은 새 비밀번호"""
        user = self.create_user()
        self.authenticate_user(user)

        url = reverse("users:password-change")
        data = {
            "old_password": self.test_password,
            "new_password": "weak",
            "confirm_new_password": "weak",
        }

        response = self.client.patch(url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_password_change_without_auth(self):
        """인증 없이 비밀번호 변경 실패"""
        url = reverse("users:password-change")
        data = {
            "old_password": self.test_password,
            "new_password": "NewPass456!@#",
            "confirm_new_password": "NewPass456!@#",
        }

        response = self.client.patch(url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_password_complexity_requirements(self):
        """비밀번호 복잡도 요구사항 테스트"""
        user = self.create_user()
        self.authenticate_user(user)
        url = reverse("users:password-change")

        # 8자 미만
        data = {
            "old_password": self.test_password,
            "new_password": "Short1!",
            "confirm_new_password": "Short1!",
        }
        response = self.client.patch(url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("8자 이상", response.data["message"])

        # 영문자 없음
        data["new_password"] = data["confirm_new_password"] = "12345678!@#"
        response = self.client.patch(url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("영문자", response.data["message"])

        # 숫자 없음
        data["new_password"] = data["confirm_new_password"] = "NoNumbers!@#"
        response = self.client.patch(url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("숫자", response.data["message"])

        # 특수문자 없음
        data["new_password"] = data["confirm_new_password"] = "NoSpecial123"
        response = self.client.patch(url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("특수문자", response.data["message"])

        # 연속된 문자
        data["new_password"] = data["confirm_new_password"] = "Passs123!@#"
        response = self.client.patch(url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("연속", response.data["message"])


class AccountDeletionTestCase(BaseUserTestCase):
    """회원 탈퇴 테스트"""

    def test_account_deletion_normal_user(self):
        """일반 사용자 회원 탈퇴"""
        user = self.create_user()
        self.authenticate_user(user)

        url = reverse("users:account-delete")
        data = {"password": self.test_password}

        response = self.client.delete(url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("90일 후 모든 데이터가 완전히 삭제됩니다", response.data["message"])

        user.refresh_from_db()
        self.assertTrue(user.is_deleted)
        self.assertFalse(user.is_active)
        self.assertIsNotNone(user.deleted_at)
        self.assertIsNotNone(user.deletion_scheduled_at)
        self.assertEqual(user.email, f"deleted_{user.id}@deleted.com")
        self.assertEqual(user.username, f"탈퇴회원_{user.id}")

    def test_account_deletion_wrong_password(self):
        """잘못된 비밀번호로 탈퇴 실패"""
        user = self.create_user()
        self.authenticate_user(user)

        url = reverse("users:account-delete")
        data = {"password": "WrongPassword123!"}

        response = self.client.delete(url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data["message"], "비밀번호가 일치하지 않습니다.")

    def test_account_deletion_social_user(self):
        """소셜 가입 사용자 회원 탈퇴 (비밀번호 불필요)"""
        user = self.create_user(joined_type="kakao")
        self.authenticate_user(user)

        url = reverse("users:account-delete")
        response = self.client.delete(url, format="json")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        user.refresh_from_db()
        self.assertTrue(user.is_deleted)

    def test_account_deletion_already_deleted(self):
        """이미 탈퇴한 회원 재탈퇴 시도"""
        user = self.create_user()
        user.is_deleted = True
        user.save()
        self.authenticate_user(user)

        url = reverse("users:account-delete")
        data = {"password": self.test_password}

        response = self.client.delete(url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data["message"], "이미 탈퇴한 회원입니다.")

    def test_account_deletion_without_auth(self):
        """인증 없이 회원 탈퇴 실패"""
        url = reverse("users:account-delete")
        data = {"password": self.test_password}

        response = self.client.delete(url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)


class EmailVerificationTestCase(BaseUserTestCase):
    """이메일 인증 테스트"""

    @patch("django.core.mail.EmailMultiAlternatives.send")
    def test_send_signup_verification_code(self, mock_send):
        """회원가입 이메일 인증 코드 발송"""
        mock_send.return_value = 1

        url = reverse("users:signup-email-send")
        data = {"email": "newuser@example.com"}

        response = self.client.post(url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("인증 코드가 발송되었습니다", response.data["message"])

        # send 호출 확인
        mock_send.assert_called_once()

    def test_send_signup_verification_duplicate_email(self):
        """중복 이메일로 인증 코드 발송 실패"""
        self.create_user()

        url = reverse("users:signup-email-send")
        data = {"email": self.test_email}

        response = self.client.post(url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("이미 사용 중인 이메일입니다", response.data["message"])

    def test_verify_signup_code_success(self):
        """회원가입 인증 코드 확인 성공"""
        email = "newuser@example.com"
        code = "123456"

        # 캐시에 인증 코드 저장
        cache.set(f"email_code:signup:{email}", code, timeout=600)

        url = reverse("users:signup-email-verify")
        data = {"email": email, "code": code}

        response = self.client.post(url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("이메일 인증이 완료되었습니다", response.data["message"])

        # 인증 완료 캐시 확인
        self.assertTrue(cache.get(f"signup_email_verified:{email}"))

    def test_verify_signup_code_wrong(self):
        """잘못된 인증 코드"""
        email = "newuser@example.com"
        cache.set(f"email_code:signup:{email}", "123456", timeout=600)

        url = reverse("users:signup-email-verify")
        data = {"email": email, "code": "999999"}

        response = self.client.post(url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        # 실제 메시지가 다를 수 있으므로 상태 코드만 확인

    @patch("django.core.mail.EmailMultiAlternatives.send")
    def test_send_password_reset_code(self, mock_send):
        """비밀번호 재설정 인증 코드 발송"""
        mock_send.return_value = 1
        user = self.create_user()

        url = reverse("users:password-reset-email-send")
        data = {"email": self.test_email}

        response = self.client.post(url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        mock_send.assert_called_once()

    def test_verify_password_reset_code_success(self):
        """비밀번호 재설정 인증 코드 확인 성공"""
        user = self.create_user()
        code = "123456"

        cache.set(f"email_code:password_reset:{self.test_email}", code, timeout=600)

        url = reverse("users:password-reset-email-verify")
        data = {"email": self.test_email, "code": code}

        response = self.client.post(url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(cache.get(f"password_reset_verified:{self.test_email}"))


class SocialLoginTestCase(BaseUserTestCase):
    """소셜 로그인 테스트"""

    @patch("requests.post")
    @patch("requests.get")
    def test_kakao_login_new_user(self, mock_get, mock_post):
        """카카오 신규 사용자 로그인"""
        # 토큰 교환 응답 mock
        mock_post.return_value.status_code = 200
        mock_post.return_value.json.return_value = {
            "access_token": "fake_access_token",
            "token_type": "bearer"
        }
        
        # 사용자 정보 응답 mock
        mock_get.return_value.status_code = 200
        mock_get.return_value.json.return_value = {
            "id": "123456789",
            "kakao_account": {
                "email": "kakao@example.com",
                "profile": {
                    "nickname": "kakaouser"
                }
            }
        }

        url = reverse("users:kakao-login")
        data = {"code": "fake_auth_code"}

        response = self.client.post(url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # 사용자 생성 확인
        user = User.objects.get(email="kakao@example.com")
        self.assertEqual(user.joined_type, "kakao")

    @patch("requests.post")
    @patch("requests.get")
    def test_kakao_login_existing_user(self, mock_get, mock_post):
        """카카오 기존 사용자 로그인"""
        # 기존 사용자 생성
        existing_user = self.create_user(
            email="kakao@example.com", username="existinguser", joined_type="kakao"
        )

        # 토큰 교환 응답 mock
        mock_post.return_value.status_code = 200
        mock_post.return_value.json.return_value = {
            "access_token": "fake_access_token",
            "token_type": "bearer"
        }
        
        # 사용자 정보 응답 mock
        mock_get.return_value.status_code = 200
        mock_get.return_value.json.return_value = {
            "id": "123456789",
            "kakao_account": {
                "email": "kakao@example.com",
                "profile": {
                    "nickname": "kakaouser"
                }
            }
        }

        url = reverse("users:kakao-login")
        data = {"code": "fake_auth_code"}

        response = self.client.post(url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # 사용자 수 변화 없음 확인
        self.assertEqual(User.objects.filter(email="kakao@example.com").count(), 1)

    @patch("requests.post")
    @patch("requests.get")
    def test_google_login(self, mock_get, mock_post):
        """구글 로그인"""
        # 토큰 교환 응답 mock
        mock_post.return_value.status_code = 200
        mock_post.return_value.json.return_value = {
            "access_token": "fake_access_token",
            "token_type": "bearer"
        }
        
        # 사용자 정보 응답 mock
        mock_get.return_value.status_code = 200
        mock_get.return_value.json.return_value = {
            "id": "123456789",
            "email": "google@example.com",
            "name": "googleuser"
        }

        url = reverse("users:google-login")
        data = {"code": "fake_auth_code"}

        response = self.client.post(url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        user = User.objects.get(email="google@example.com")
        self.assertEqual(user.joined_type, "google")

    @patch("requests.post")
    @patch("requests.get")
    def test_naver_login(self, mock_get, mock_post):
        """네이버 로그인"""
        # 토큰 교환 응답 mock
        mock_post.return_value.status_code = 200
        mock_post.return_value.json.return_value = {
            "access_token": "fake_access_token",
            "token_type": "bearer"
        }
        
        # 사용자 정보 응답 mock
        mock_get.return_value.status_code = 200
        mock_get.return_value.json.return_value = {
            "response": {
                "id": "123456789",
                "email": "naver@example.com",
                "name": "naveruser"
            }
        }

        url = reverse("users:naver-login")
        data = {"code": "fake_auth_code"}

        response = self.client.post(url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        user = User.objects.get(email="naver@example.com")
        self.assertEqual(user.joined_type, "naver")


class RateLimitTestCase(BaseUserTestCase):
    """Rate Limiting 테스트"""

    @override_settings(CACHES={"default": {"BACKEND": "django.core.cache.backends.locmem.LocMemCache"}})
    def test_login_rate_limit(self):
        """로그인 API Rate Limit 테스트"""
        self.create_user()
        url = reverse("users:login")
        data = {"email": self.test_email, "password": "WrongPass123!"}

        # 5회 요청 (제한 내)
        for i in range(5):
            response = self.client.post(url, data, format="json")
            self.assertIn(
                response.status_code,
                [status.HTTP_400_BAD_REQUEST, status.HTTP_200_OK],
            )

        # 6회째 요청 (제한 초과)
        response = self.client.post(url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_429_TOO_MANY_REQUESTS)

    @override_settings(CACHES={"default": {"BACKEND": "django.core.cache.backends.locmem.LocMemCache"}})
    @patch("django.core.mail.EmailMultiAlternatives.send")
    def test_email_rate_limit(self, mock_send):
        """이메일 발송 API Rate Limit 테스트"""
        mock_send.return_value = 1
        url = reverse("users:signup-email-send")
        data = {"email": "test1@example.com"}

        # 3회 요청 (제한 내)
        for i in range(3):
            data = {"email": f"test{i+1}@example.com"}
            response = self.client.post(url, data, format="json")
            self.assertEqual(response.status_code, status.HTTP_200_OK)

        # 4회째 요청 (제한 초과)
        data = {"email": "test4@example.com"}
        response = self.client.post(url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_429_TOO_MANY_REQUESTS)