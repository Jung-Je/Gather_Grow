from django.contrib.auth.models import (
    AbstractBaseUser,
    BaseUserManager,
    PermissionsMixin,
)
from django.db import models

from apps.common.models import BaseModel

ROLE_CHOICES = [
    ("admin", "관리자"),
    ("user", "일반 사용자"),
]

JOINED_TYPE_CHOICES = [
    ("kakao", "카카오"),
    ("google", "구글"),
    ("naver", "네이버"),
    ("normal", "일반"),
]

EDUCATION_LEVEL_CHOICES = [
    ("elementary_school", "초등학생"),
    ("middle_school", "중학생"),
    ("high_school", "고등학생"),
    ("university_student", "대학생"),
    ("graduate_student", "대학원생"),
    ("office_worker", "직장인"),
    ("job_seeker", "취업준비생"),
    ("other", "기타"),
]


class UserQuerySet(models.QuerySet):
    """소프트 삭제를 지원하는 커스텀 쿼리셋"""

    def active(self):
        """탈퇴하지 않은 활성 사용자만 조회"""
        return self.filter(is_deleted=False)

    def deleted(self):
        """탈퇴한 사용자만 조회"""
        return self.filter(is_deleted=True)

    def with_deleted(self):
        """탈퇴한 사용자 포함 전체 조회"""
        return self


class UserManager(BaseUserManager):
    """사용자 생성 및 관리를 위한 커스텀 매니저."""

    def get_queryset(self):
        """기본 쿼리셋은 탈퇴하지 않은 사용자만 반환"""
        return UserQuerySet(self.model, using=self._db).active()

    def with_deleted(self):
        """탈퇴한 사용자 포함 전체 조회"""
        return UserQuerySet(self.model, using=self._db).with_deleted()

    def deleted_only(self):
        """탈퇴한 사용자만 조회"""
        return UserQuerySet(self.model, using=self._db).deleted()

    def create_user(self, email, username, password=None, **extra_fields):
        """일반 사용자를 생성합니다.

        Args:
            email (str): 사용자 이메일 주소
            username (str): 사용자 이름
            password (str, optional): 비밀번호. Defaults to None.
            **extra_fields: 추가 필드들

        Returns:
            User: 생성된 사용자 객체

        Raises:
            ValueError: 이메일 또는 사용자 이름이 없을 경우
        """
        if not email:
            raise ValueError("이메일은 필수입니다")
        if not username:
            raise ValueError("사용자 이름은 필수입니다")

        email = self.normalize_email(email)
        user = self.model(email=email, username=username, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, username, password=None, **extra_fields):
        """슈퍼유저(관리자)를 생성합니다.

        Args:
            email (str): 사용자 이메일 주소
            username (str): 사용자 이름
            password (str, optional): 비밀번호. Defaults to None.
            **extra_fields: 추가 필드들

        Returns:
            User: 생성된 슈퍼유저 객체

        Raises:
            ValueError: is_staff 또는 is_superuser가 True가 아닐 경우
        """
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        extra_fields.setdefault("is_active", True)

        if extra_fields.get("is_staff") is not True:
            raise ValueError("Superuser must have is_staff=True.")
        if extra_fields.get("is_superuser") is not True:
            raise ValueError("Superuser must have is_superuser=True.")

        return self.create_user(email, username, password, **extra_fields)


class User(AbstractBaseUser, PermissionsMixin, BaseModel):
    """커스텀 사용자 모델.

    Django 기본 User 모델을 대체하는 커스텀 모델입니다.
    이메일을 기본 인증 필드로 사용합니다.

    Attributes:
        username (str): 사용자 이름 (최대 20자)
        email (str): 이메일 주소 (unique, 로그인에 사용)
        role (str): 사용자 역할 (admin/user)
        joined_type (str): 가입 유형 (kakao/google/naver/normal)
        profile (str): 자기소개 및 기술 스택
        profile_image (ImageField): 프로필 이미지
        education_level (str): 교육 수준
        location (str): 지역 정보
        is_active (bool): 계정 활성화 여부
        is_staff (bool): 스태프 권한 여부
        created_at (datetime): 생성 일시 (BaseModel에서 상속)
        updated_at (datetime): 수정 일시 (BaseModel에서 상속)
    """

    username = models.CharField(max_length=20)
    email = models.EmailField(unique=True)
    role = models.CharField(max_length=10, choices=ROLE_CHOICES, default="user")
    joined_type = models.CharField(max_length=20, choices=JOINED_TYPE_CHOICES)
    profile = models.TextField(blank=True, null=True)
    profile_image = models.ImageField(upload_to="profile_images/", blank=True, null=True)
    education_level = models.CharField(max_length=20, choices=EDUCATION_LEVEL_CHOICES, blank=True, null=True)
    location = models.CharField(max_length=100, blank=True, null=True)

    # 보안 관련 필드
    failed_login_attempts = models.IntegerField(default=0)
    last_failed_login = models.DateTimeField(null=True, blank=True)

    # 탈퇴 관련 필드
    is_deleted = models.BooleanField(default=False)
    deleted_at = models.DateTimeField(null=True, blank=True)
    deletion_scheduled_at = models.DateTimeField(null=True, blank=True)

    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)

    objects = UserManager()

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = ["username"]

    class Meta:
        db_table = "users"
        verbose_name = "사용자"
        verbose_name_plural = "사용자들"

    def __str__(self):
        return self.username
