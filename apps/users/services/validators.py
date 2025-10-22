import re
from collections import Counter
from typing import Optional


class PasswordValidator:
    """비밀번호 유효성 검증 클래스

    비밀번호 복잡도 규칙:
    - 최소 8자, 최대 50자
    - 영문자 포함 필수
    - 숫자 포함 필수
    - 특수문자 포함 필수
    - 연속된 같은 문자 3개 이상 금지
    - 공백 포함 금지
    """

    MIN_LENGTH = 8
    MAX_LENGTH = 50
    SPECIAL_CHARS = r'[!@#$%^&*()_+\-=\[\]{};\':"\\|,.<>/?`~]'

    @classmethod
    def validate(cls, password: str) -> Optional[str]:
        """비밀번호 유효성 검증

        Args:
            password: 검증할 비밀번호

        Returns:
            에러 메시지 또는 None (유효한 경우)
        """
        # 1. 최소 길이 검증
        if len(password) < cls.MIN_LENGTH:
            return f"비밀번호는 {cls.MIN_LENGTH}자 이상이어야 합니다."

        # 2. 최대 길이 검증
        if len(password) > cls.MAX_LENGTH:
            return f"비밀번호는 {cls.MAX_LENGTH}자를 초과할 수 없습니다."

        # 3. 공백 검증
        if " " in password:
            return "비밀번호에는 공백이 포함될 수 없습니다."

        # 4. 영문자 포함 검증
        if not re.search(r"[a-zA-Z]", password):
            return "비밀번호에는 영문자가 포함되어야 합니다."

        # 5. 숫자 포함 검증
        if not re.search(r"[0-9]", password):
            return "비밀번호에는 숫자가 포함되어야 합니다."

        # 6. 특수문자 포함 검증
        if not re.search(cls.SPECIAL_CHARS, password):
            return "비밀번호에는 특수문자가 포함되어야 합니다."

        # 7. 연속된 같은 문자 3개 이상 금지
        if re.search(r"(.)\1{2,}", password):
            return "동일한 문자를 3개 이상 연속으로 사용할 수 없습니다."

        # 8. 동일한 문자(숫자/특수문자) 3번 이상 사용 금지
        char_count = Counter(password)
        for char, count in char_count.items():
            if count >= 3 and (char.isdigit() or not char.isalpha()):
                return f"'{char}' 문자는 3번 이상 사용할 수 없습니다."

        return None  # 유효한 비밀번호
