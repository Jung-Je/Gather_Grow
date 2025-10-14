import logging
import re


class SensitiveDataFilter(logging.Filter):
    """민감정보 마스킹 필터

    로그에 기록되는 이메일, 전화번호 등의 민감정보를 마스킹합니다.
    """

    def filter(self, record):
        """로그 레코드 필터링

        Args:
            record: 로그 레코드

        Returns:
            bool: 항상 True (로그를 출력하되 내용만 마스킹)
        """
        if hasattr(record, "msg"):
            # 이메일 마스킹 (예: test@example.com -> tes***@example.com)
            record.msg = re.sub(
                r"([a-zA-Z0-9._%+-]{3})[a-zA-Z0-9._%+-]*@([a-zA-Z0-9.-]+\.[a-zA-Z]{2,})",
                r"\1***@\2",
                str(record.msg),
            )

            # IP 주소 마스킹 (예: 192.168.1.100 -> 192.168.***.***)
            record.msg = re.sub(
                r"\b(\d{1,3})\.(\d{1,3})\.(\d{1,3})\.(\d{1,3})\b",
                r"\1.\2.***.***",
                str(record.msg),
            )

            # 전화번호 마스킹 (예: 010-1234-5678 -> 010-****-5678)
            record.msg = re.sub(r"\b(\d{2,3})-?\d{3,4}-?(\d{4})\b", r"\1-****-\2", str(record.msg))

            # JWT 토큰 마스킹 (Bearer 토큰)
            record.msg = re.sub(
                r"Bearer\s+[A-Za-z0-9\-_]+\.[A-Za-z0-9\-_]+\.[A-Za-z0-9\-_]+",
                "Bearer ***MASKED_TOKEN***",
                str(record.msg),
            )

            # 일반 토큰 마스킹 (20자 이상의 영숫자 문자열)
            record.msg = re.sub(r"\b[A-Za-z0-9]{20,}\b", "***MASKED_TOKEN***", str(record.msg))

        return True
