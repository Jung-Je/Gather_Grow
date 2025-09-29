from django.contrib.auth import authenticate, get_user_model
from django.contrib.auth.tokens import PasswordResetTokenGenerator
from django.utils import timezone
from django.utils.encoding import force_str
from django.utils.http import urlsafe_base64_decode
from rest_framework import serializers

User = get_user_model()


class UserSignUpSerializer(serializers.ModelSerializer):
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

    def validate_email(self, value):
        if User.objects.filter(email=value).exists():
            raise serializers.ValidationError("이미 존재하는 이메일입니다.")
        return value

    def validate_password(self, value):
        """
        비밀번호 유효성 검증
        - 최소 8자, 최대 50자
        - 영문자 포함 (대/소문자 구분 없음)
        - 숫자 포함 필수
        - 특수문자 포함 필수
        - 연속된 같은 문자 3개 이상 금지
        - 공백 포함 금지
        """
        import re

        # 1. 최소 길이 검증 (8자 이상)
        if len(value) < 8:
            raise serializers.ValidationError("비밀번호는 8자 이상이어야 합니다.")

        # 2. 최대 길이 검증 (50자 제한)
        if len(value) > 50:
            raise serializers.ValidationError("비밀번호는 50자를 초과할 수 없습니다.")

        # 3. 공백 검증
        if " " in value:
            raise serializers.ValidationError("비밀번호에는 공백이 포함될 수 없습니다.")

        # 4. 영문자 포함 검증 (대/소문자 상관없음)
        if not re.search(r"[a-zA-Z]", value):
            raise serializers.ValidationError(
                "비밀번호에는 영문자가 포함되어야 합니다."
            )

        # 5. 숫자 포함 검증
        if not re.search(r"[0-9]", value):
            raise serializers.ValidationError("비밀번호에는 숫자가 포함되어야 합니다.")

        # 6. 특수문자 포함 검증
        if not re.search(r'[!@#$%^&*()_+\-=\[\]{};\':"\\|,.<>\/?`~]', value):
            raise serializers.ValidationError(
                "비밀번호에는 특수문자가 포함되어야 합니다."
            )

        # 7. 연속된 같은 문자 3개 이상 금지
        if re.search(r"(.)\1{2,}", value):
            raise serializers.ValidationError(
                "동일한 문자를 3개 이상 연속으로 사용할 수 없습니다."
            )

        # 8. 동일한 문자(숫자/특수문자) 3번 이상 사용 금지
        from collections import Counter

        char_count = Counter(value)
        for char, count in char_count.items():
            if count >= 3 and (char.isdigit() or not char.isalpha()):
                raise serializers.ValidationError(
                    f"'{char}' 문자는 3번 이상 사용할 수 없습니다."
                )

        return value

    def validate(self, data):
        """비밀번호 일치 여부 확인"""
        password = data.get("password")
        confirm_password = data.get("confirm_password")

        if password != confirm_password:
            raise serializers.ValidationError("비밀번호가 일치하지 않습니다.")

        return data

    def create(self, validated_data):
        """confirm_password를 제외하고 User 생성"""
        validated_data.pop("confirm_password", None)
        return super().create(validated_data)


class UserLoginSerializer(serializers.Serializer):
    email = serializers.EmailField(required=True)
    password = serializers.CharField(required=True, write_only=True)

    def validate(self, data):
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
                raise serializers.ValidationError(
                    "Unable to login with provided credentials."
                )
        else:
            raise serializers.ValidationError("Email and password are required.")

        return data


class SetNewPasswordSerializer(serializers.Serializer):
    """
    패스워드 재설정 링크 시리얼라이저
    """

    password = serializers.CharField(min_length=8, write_only=True)
    confirm_password = serializers.CharField(min_length=8, write_only=True)
    token = serializers.CharField(write_only=True)
    uidb64 = serializers.CharField(write_only=True, required=False)
    uidb_64 = serializers.CharField(
        write_only=True, required=False
    )  # Handle camel case conversion

    class Meta:
        fields = ["password", "confirm_password", "token", "uidb64"]

    def validate(self, attrs):
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
        user = self.validated_data["user"]
        user.set_password(self.validated_data["password"])
        user.save()
        return user


class UserResponseSerializer(serializers.ModelSerializer):
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
