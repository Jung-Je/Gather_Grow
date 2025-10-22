from functools import wraps
from typing import Callable

from django.core.cache import cache

from apps.common.responses import APIResponse


def rate_limit(key_prefix: str, rate: str, method: str = "POST") -> Callable:
    """Rate limiting 데코레이터

    슬라이딩 윈도우 카운터 방식으로 효율적이고 안정적인 속도 제한 구현

    Args:
        key_prefix: 캐시 키 prefix (예: 'login', 'email_send')
        rate: 제한 규칙 (예: '5/m', '10/h', '100/d')
        method: HTTP 메서드 (기본값: POST)

    Returns:
        데코레이터 함수

    Usage:
        @rate_limit(key_prefix='login', rate='5/m')
        def post(self, request):
            ...
    """

    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(self, request, *args, **kwargs):
            # 해당 메서드가 아니면 rate limiting 적용 안함
            if request.method != method:
                return func(self, request, *args, **kwargs)

            # rate 파싱 (예: '5/m' -> 5회, 60초)
            try:
                limit, period = rate.split("/")
                limit = int(limit)

                if period == "m":  # minute
                    seconds = 60
                elif period == "h":  # hour
                    seconds = 3600
                elif period == "d":  # day
                    seconds = 86400
                else:
                    seconds = 60  # 기본값 1분
            except (ValueError, AttributeError):
                # 파싱 실패시 기본값
                limit = 10
                seconds = 60

            # IP 주소 또는 사용자 식별
            if hasattr(request, "user") and request.user.is_authenticated:
                identifier = f"user_{request.user.id}"
            else:
                x_forwarded_for = request.META.get("HTTP_X_FORWARDED_FOR")
                if x_forwarded_for:
                    ip = x_forwarded_for.split(",")[0].strip()
                else:
                    ip = request.META.get("REMOTE_ADDR", "0.0.0.0")
                identifier = f"ip_{ip}"

            # 캐시 키 생성 (카운터 기반)
            cache_key = f"rate_limit:{key_prefix}:{identifier}"
            reset_key = f"rate_limit_reset:{key_prefix}:{identifier}"

            # 현재 요청 횟수 확인 (정수 카운터 사용)
            try:
                current_count = cache.get(cache_key, 0)
                reset_time = cache.get(reset_key)

                # 첫 요청이거나 윈도우가 만료된 경우
                if current_count == 0 or reset_time is None:
                    cache.set(cache_key, 1, timeout=seconds)
                    cache.set(reset_key, seconds, timeout=seconds)
                    return func(self, request, *args, **kwargs)

                # 제한 확인
                if current_count >= limit:
                    return APIResponse.too_many_requests(
                        message=f"너무 많은 요청입니다. {reset_time}초 후에 다시 시도해주세요."
                    )

                # 요청 카운트 증가 (atomic operation)
                cache.incr(cache_key)

                return func(self, request, *args, **kwargs)

            except ValueError:
                # incr 실패시 (키가 없거나 정수가 아닌 경우) 초기화
                cache.set(cache_key, 1, timeout=seconds)
                cache.set(reset_key, seconds, timeout=seconds)
                return func(self, request, *args, **kwargs)

        return wrapper

    return decorator


def login_rate_limit(func: Callable) -> Callable:
    """로그인 전용 rate limiting (5회/분)"""
    return rate_limit(key_prefix="login", rate="5/m")(func)


def email_rate_limit(func: Callable) -> Callable:
    """이메일 발송 전용 rate limiting (3회/시간)"""
    return rate_limit(key_prefix="email", rate="3/h")(func)


def password_reset_rate_limit(func: Callable) -> Callable:
    """비밀번호 재설정 전용 rate limiting (5회/시간)"""
    return rate_limit(key_prefix="password_reset", rate="5/h")(func)
