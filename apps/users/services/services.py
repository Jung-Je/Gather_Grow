import logging
from typing import Any, Dict, Tuple

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.db import transaction
from django.utils import timezone
from rest_framework_simplejwt.tokens import RefreshToken

from apps.users.serializers.authenticate_serializer import (
    UserLoginSerializer,
    UserResponseSerializer,
    UserSignUpSerializer,
)

logger = logging.getLogger(__name__)
User = get_user_model()


class AuthenticationService:
    """인증 관련 비즈니스 로직을 처리하는 서비스 클래스"""

    @staticmethod
    def signup(data: Dict[str, Any]) -> Dict[str, Any]:
        """
        사용자 회원가입 처리

        Args:
            data: 회원가입 데이터

        Returns:
            생성된 사용자 정보
        """
        # 회원가입용 이메일 인증 확인
        email = data.get("email")
        if not cache.get(f"signup_email_verified:{email}"):
            raise ValueError(
                "이메일 인증이 필요합니다. 먼저 이메일 인증을 완료해주세요."
            )

        serializer = UserSignUpSerializer(data=data)
        serializer.is_valid(raise_exception=True)

        with transaction.atomic():
            user = serializer.save()
            password = data.get("password")
            if password:
                user.set_password(password)
                user.save()

            # 인증 완료 캐시 삭제
            cache.delete(f"signup_email_verified:{email}")

            return UserResponseSerializer(user).data

    @staticmethod
    def login(data: Dict[str, Any]) -> Tuple[Dict[str, Any], str, str]:
        """
        사용자 로그인 처리

        Args:
            data: 로그인 데이터 (email, password)

        Returns:
            (사용자 정보, access_token, refresh_token) 튜플
        """
        email = data.get("email")

        # 로그인 실패 횟수 체크
        try:
            user = User.objects.get(email=email)

            # 5회 이상 실패시 계정 잠금 (30분)
            if user.failed_login_attempts >= 5:
                if user.last_failed_login:
                    time_passed = timezone.now() - user.last_failed_login
                    if time_passed.total_seconds() < 1800:  # 30분
                        remaining_time = int(1800 - time_passed.total_seconds())
                        raise ValueError(
                            f"로그인 시도 횟수를 초과했습니다. {remaining_time}초 후에 다시 시도해주세요."
                        )
                    else:
                        # 30분 지나면 초기화
                        user.failed_login_attempts = 0
                        user.save(update_fields=["failed_login_attempts"])
        except User.DoesNotExist:
            pass  # 존재하지 않는 이메일은 아래 serializer에서 처리

        try:
            serializer = UserLoginSerializer(data=data)
            serializer.is_valid(raise_exception=True)

            user = serializer.validated_data["user"]
            refresh = RefreshToken.for_user(user)

            # 로그인 성공시 실패 횟수 초기화
            user.failed_login_attempts = 0
            user.last_login = timezone.now()
            user.save(update_fields=["failed_login_attempts", "last_login"])

            user_data = UserResponseSerializer(user).data
            return user_data, str(refresh.access_token), str(refresh)

        except Exception as e:
            # 로그인 실패시 횟수 증가
            try:
                user = User.objects.get(email=email)
                user.failed_login_attempts += 1
                user.last_failed_login = timezone.now()
                user.save(update_fields=["failed_login_attempts", "last_failed_login"])
            except User.DoesNotExist:
                pass
            raise e

    @staticmethod
    def refresh_token(refresh_token: str) -> Tuple[str, str]:
        """
        토큰 갱신 처리

        Args:
            refresh_token: 리프레시 토큰

        Returns:
            (새 access_token, 새 refresh_token) 튜플
        """
        token = RefreshToken(refresh_token)
        access_token = str(token.access_token)

        # Token rotation
        if settings.SIMPLE_JWT.get("ROTATE_REFRESH_TOKENS", False):
            user_id = token.get("user_id")
            user = User.objects.get(id=user_id)

            # Create new refresh token
            new_refresh = RefreshToken.for_user(user)
            new_refresh_token = str(new_refresh)

            # Blacklist old token if configured
            if settings.SIMPLE_JWT.get("BLACKLIST_AFTER_ROTATION", False):
                try:
                    token.blacklist()
                except AttributeError:
                    pass  # Blacklist app not installed
        else:
            new_refresh_token = refresh_token

        return access_token, new_refresh_token

    @staticmethod
    def logout(refresh_token: str) -> None:
        """
        로그아웃 처리

        Args:
            refresh_token: 리프레시 토큰
        """
        token = RefreshToken(refresh_token)
        token.blacklist()

    @staticmethod
    def verify_email_for_password_reset(email: str) -> bool:
        """
        비밀번호 재설정을 위한 이메일 확인

        비밀번호 찾기 시 해당 이메일이 존재하는지 확인합니다.
        존재하는 경우 캐시에 임시 표시를 저장합니다.

        Args:
            email: 사용자 이메일

        Returns:
            이메일 존재 여부 (보안을 위해 외부에는 노출하지 않음)
        """
        try:
            user = User.objects.get(email=email)
            # 비밀번호 재설정 가능 상태를 캐시에 저장 (5분간 유효)
            cache.set(f"password_reset_verified:{email}", True, timeout=300)
            return True
        except User.DoesNotExist:
            # 보안을 위해 사용자가 존재하지 않아도 동일한 처리
            logger.info(f"Password reset requested for non-existent email: {email}")
            return False

    @staticmethod
    def reset_password_after_verification(email: str, new_password: str) -> bool:
        """
        이메일 인증 후 비밀번호 재설정 (비밀번호 찾기)

        이메일 인증이 완료된 후 새 비밀번호를 설정합니다.
        이 메서드는 로그인하지 않은 상태에서 사용됩니다.

        Args:
            email: 사용자 이메일
            new_password: 새 비밀번호

        Returns:
            비밀번호 재설정 성공 여부

        Raises:
            ValueError: 이메일 인증이 완료되지 않았거나 사용자가 없을 때
        """
        # 이메일 인증 확인
        if not cache.get(f"password_reset_verified:{email}"):
            raise ValueError(
                "이메일 인증이 필요합니다. 먼저 이메일 인증을 완료해주세요."
            )

        try:
            user = User.objects.get(email=email)
            user.set_password(new_password)
            user.save()

            # 인증 상태 캐시 삭제
            cache.delete(f"password_reset_verified:{email}")

            logger.info(f"Password reset successfully for user: {email}")
            return True
        except User.DoesNotExist:
            raise ValueError("사용자를 찾을 수 없습니다.")

    @staticmethod
    def change_password(user, old_password: str, new_password: str) -> bool:
        """
        로그인한 사용자의 비밀번호 변경 (마이페이지)

        현재 비밀번호를 확인한 후 새 비밀번호로 변경합니다.
        이 메서드는 로그인한 상태에서만 사용됩니다.

        Args:
            user: 현재 로그인한 사용자
            old_password: 현재 비밀번호
            new_password: 새 비밀번호

        Returns:
            비밀번호 변경 성공 여부

        Raises:
            ValueError: 현재 비밀번호가 일치하지 않을 때
        """
        if not user.check_password(old_password):
            raise ValueError("현재 비밀번호가 일치하지 않습니다.")

        user.set_password(new_password)
        user.save()

        logger.info(f"Password changed for user: {user.email}")
        return True

    @staticmethod
    def get_user_info(user) -> Dict[str, Any]:
        """
        사용자 정보 조회

        Args:
            user: User 인스턴스

        Returns:
            사용자 정보
        """
        return UserResponseSerializer(user).data

    @staticmethod
    def delete_account(user, password: str = None) -> bool:
        """
        회원 탈퇴 처리 (소프트 삭제)

        개인정보보호법에 따라 즉시 삭제하지 않고 90일 후 완전 삭제

        Args:
            user: 탈퇴할 사용자
            password: 비밀번호 (일반 가입자만 필요)

        Returns:
            탈퇴 성공 여부

        Raises:
            ValueError: 비밀번호 불일치 또는 이미 탈퇴한 회원
        """
        # 이미 탈퇴한 회원인지 확인
        if user.is_deleted:
            raise ValueError("이미 탈퇴한 회원입니다.")

        # 일반 가입자는 비밀번호 확인
        if user.joined_type == "normal":
            if not password:
                raise ValueError("비밀번호를 입력해주세요.")
            if not user.check_password(password):
                raise ValueError("비밀번호가 일치하지 않습니다.")

        # 소프트 삭제 처리
        user.is_deleted = True
        user.is_active = False  # 로그인 차단
        user.deleted_at = timezone.now()
        user.deletion_scheduled_at = timezone.now() + timezone.timedelta(
            days=90
        )  # 90일 후 완전 삭제

        # 개인정보 마스킹 (복구 불가능하도록)
        user.email = f"deleted_{user.id}@deleted.com"
        user.username = f"탈퇴회원_{user.id}"
        user.profile = None
        user.profile_image = None
        user.education_level = None
        user.location = None

        user.save()

        logger.info(f"User {user.id} account deleted (soft delete)")
        return True

    @staticmethod
    def permanently_delete_expired_users():
        """
        탈퇴 후 90일이 지난 회원 데이터 완전 삭제

        이 메서드는 주기적으로 실행되어야 함 (예: 매일 자정 크론잡)
        """
        expired_users = User.objects.filter(
            is_deleted=True, deletion_scheduled_at__lte=timezone.now()
        )

        count = expired_users.count()
        for user in expired_users:
            user_id = user.id
            user.delete()  # 완전 삭제
            logger.info(f"User {user_id} permanently deleted")

        logger.info(f"Permanently deleted {count} expired user accounts")
        return count
