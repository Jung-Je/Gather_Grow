from django.contrib.auth import authenticate, get_user_model
from django.contrib.auth.tokens import PasswordResetTokenGenerator
from django.utils import timezone
from django.utils.encoding import force_str
from django.utils.http import urlsafe_base64_decode
from rest_framework import serializers

from apps.users.services.validators import PasswordValidator

User = get_user_model()


class UserSignUpSerializer(serializers.ModelSerializer):
    """사용자 회원가입 Serializer

    비밀번호 확인 및 유효성 검증을 포함한 회원가입 데이터를 처리합니다.
    """

    password = serializers.CharField(write_only=True)
    confirm_password = serializers.CharField(write_only=True)

    class Meta:
        model = User
        fields = [
            "email",
            "password",
            "confirm_password",
            "username",
            "joined_type",
        ]
        read_only_fields = ["joined_type"]

    def validate_email(self, value):
        """이메일 중복 여부를 검증합니다.

        Args:
            value (str): 검증할 이메일 주소

        Returns:
            str: 검증된 이메일 주소

        Raises:
            serializers.ValidationError: 이미 사용 중인 이메일인 경우
        """
        if User.objects.with_deleted().filter(email=value).exists():
            raise serializers.ValidationError("이미 사용 중인 이메일입니다.")
        return value

    def validate_password(self, value):
        """비밀번호 유효성을 검증합니다.

        - 최소 8자, 최대 50자
        - 영문자 포함 (대/소문자 구분 없음)
        - 숫자 포함 필수
        - 특수문자 포함 필수
        - 연속된 같은 문자 3개 이상 금지
        - 공백 포함 금지

        Args:
            value (str): 검증할 비밀번호

        Returns:
            str: 검증된 비밀번호

        Raises:
            serializers.ValidationError: 비밀번호가 유효성 검사를 통과하지 못한 경우
        """
        error_message = PasswordValidator.validate(value)
        if error_message:
            raise serializers.ValidationError(error_message)

        return value

    def validate(self, data):
        """비밀번호와 비밀번호 확인이 일치하는지 검증합니다.

        Args:
            data (dict): 검증할 데이터

        Returns:
            dict: 검증된 데이터

        Raises:
            serializers.ValidationError: 비밀번호가 일치하지 않는 경우
        """
        password = data.get("password")
        confirm_password = data.get("confirm_password")

        if password != confirm_password:
            raise serializers.ValidationError("비밀번호가 일치하지 않습니다.")

        return data

    def create(self, validated_data):
        """confirm_password를 제외하고 User 객체를 생성합니다.

        Args:
            validated_data (dict): 검증된 데이터

        Returns:
            User: 생성된 사용자 객체
        """
        validated_data.pop("confirm_password", None)
        return super().create(validated_data)


class UserLoginSerializer(serializers.Serializer):
    """사용자 로그인 Serializer

    이메일과 비밀번호로 사용자 인증을 처리합니다.
    """

    email = serializers.EmailField(required=True)
    password = serializers.CharField(required=True, write_only=True)

    def validate(self, data):
        """이메일과 비밀번호로 사용자를 인증합니다.

        Args:
            data (dict): 검증할 데이터 (email, password 포함)

        Returns:
            dict: 검증된 데이터 (user 객체 포함)

        Raises:
            serializers.ValidationError: 인증 실패, 계정 비활성화, 필드 누락 시
        """
        email = data.get("email")
        password = data.get("password")

        if email and password:
            # Django authenticate는 USERNAME_FIELD가 email이어도 username 파라미터를 사용
            user = authenticate(username=email, password=password)
            if user:
                if user.is_active:
                    data["user"] = user
                    user.last_login = timezone.now()
                    user.save()
                else:
                    raise serializers.ValidationError("User account is disabled.")
            else:
                raise serializers.ValidationError("Unable to login with provided credentials.")
        else:
            raise serializers.ValidationError("Email and password are required.")

        return data


class SetNewPasswordSerializer(serializers.Serializer):
    """패스워드 재설정 Serializer

    비밀번호 재설정 링크를 통해 새 비밀번호를 설정합니다.
    """

    password = serializers.CharField(min_length=8, write_only=True)
    confirm_password = serializers.CharField(min_length=8, write_only=True)
    token = serializers.CharField(write_only=True)
    uidb64 = serializers.CharField(write_only=True, required=False)
    uidb_64 = serializers.CharField(write_only=True, required=False)  # Handle camel case conversion

    class Meta:
        fields = ["password", "confirm_password", "token", "uidb64"]

    def validate(self, attrs):
        """비밀번호 일치 여부와 토큰 유효성을 검증합니다.

        Args:
            attrs (dict): 검증할 데이터

        Returns:
            dict: 검증된 데이터 (user 객체 포함)

        Raises:
            serializers.ValidationError: uidb64 누락, 비밀번호 불일치, 토큰 무효 시
        """
        # Handle both uidb64 and uidb_64 (camel case conversion)
        uidb64 = attrs.get("uidb64") or attrs.get("uidb_64")

        if not uidb64:
            raise serializers.ValidationError("uidb64 field is required")

        try:
            password = attrs.get("password")
            confirm_password = attrs.get("confirm_password")
            token = attrs.get("token")

            if password != confirm_password:
                raise serializers.ValidationError("비밀번호가 일치하지 않습니다.")

            uid = force_str(urlsafe_base64_decode(uidb64))
            user = User.objects.get(pk=uid)
        except (TypeError, ValueError, OverflowError, User.DoesNotExist):
            raise serializers.ValidationError("토큰이 유효하지 않습니다.")

        if not PasswordResetTokenGenerator().check_token(user, token):
            raise serializers.ValidationError("토큰이 유효하지 않거나 만료되었습니다.")

        attrs["user"] = user
        return attrs

    def save(self, **kwargs):
        """새 비밀번호를 저장합니다.

        Args:
            **kwargs: 추가 키워드 인자

        Returns:
            User: 비밀번호가 변경된 사용자 객체
        """
        user = self.validated_data["user"]
        user.set_password(self.validated_data["password"])
        user.save()
        return user


class UserResponseSerializer(serializers.ModelSerializer):
    """사용자 응답 Serializer

    API 응답에 사용되는 사용자 정보를 직렬화합니다.
    """

    class Meta:
        model = User
        fields = [
            "id",
            "email",
            "username",
            "role",
            "joined_type",
            "last_login",
        ]
