import logging
from typing import Any, Dict, Optional, Union

from rest_framework import status
from rest_framework.response import Response

logger = logging.getLogger(__name__)


class APIResponse(Response):

    def __init__(
        self,
        message: str = "",
        data: Optional[Dict[str, Any]] = None,
        status_code: int = None,
        **kwargs,
    ):
        if status_code is None:
            raise ValueError("status_code is required")

        if data is None:
            data = {}

        response_data = {
            "message": message,
            "data": data,
            "status_code": status_code,
        }

        super().__init__(data=response_data, status=status_code, **kwargs)

    @classmethod
    def success(
        cls,
        message: str = "요청이 성공적으로 처리되었습니다.",
        data: Optional[Dict[str, Any]] = None,
        **kwargs,
    ):
        """200 OK 성공 응답"""
        return cls(message=message, data=data, status_code=status.HTTP_200_OK, **kwargs)

    @classmethod
    def created(
        cls,
        message: str = "리소스가 생성되었습니다.",
        data: Optional[Dict[str, Any]] = None,
        **kwargs,
    ):
        """201 Created 응답"""
        return cls(
            message=message, data=data, status_code=status.HTTP_201_CREATED, **kwargs
        )

    @classmethod
    def bad_request(
        cls,
        message: str = "잘못된 요청입니다.",
        data: Optional[Dict[str, Any]] = None,
        **kwargs,
    ):
        """400 Bad Request 응답"""
        return cls(
            message=message,
            data=data,
            status_code=status.HTTP_400_BAD_REQUEST,
            **kwargs,
        )

    @classmethod
    def unauthorized(
        cls,
        message: str = "인증이 필요합니다.",
        data: Optional[Dict[str, Any]] = None,
        **kwargs,
    ):
        """401 Unauthorized 응답"""
        return cls(
            message=message,
            data=data,
            status_code=status.HTTP_401_UNAUTHORIZED,
            **kwargs,
        )

    @classmethod
    def forbidden(
        cls,
        message: str = "권한이 없습니다.",
        data: Optional[Dict[str, Any]] = None,
        **kwargs,
    ):
        """403 Forbidden 응답"""
        return cls(
            message=message, data=data, status_code=status.HTTP_403_FORBIDDEN, **kwargs
        )

    @classmethod
    def not_found(
        cls,
        message: str = "리소스를 찾을 수 없습니다.",
        data: Optional[Dict[str, Any]] = None,
        **kwargs,
    ):
        """404 Not Found 응답"""
        return cls(
            message=message, data=data, status_code=status.HTTP_404_NOT_FOUND, **kwargs
        )

    @classmethod
    def too_many_requests(
        cls,
        message: str = "요청이 너무 많습니다.",
        data: Optional[Dict[str, Any]] = None,
        **kwargs,
    ):
        """429 Too Many Requests 응답"""
        return cls(
            message=message,
            data=data,
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            **kwargs,
        )

    @classmethod
    def server_error(
        cls,
        message: str = "서버 오류가 발생했습니다.",
        data: Optional[Dict[str, Any]] = None,
        **kwargs,
    ):
        """500 Internal Server Error 응답"""
        if data is None:
            data = {"error": "An unexpected error occurred"}
        return cls(
            message=message,
            data=data,
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            **kwargs,
        )

    @classmethod
    def from_exception(
        cls, exception: Exception, message: Optional[str] = None, log_error: bool = True
    ):
        """예외를 받아서 적절한 응답을 생성"""
        if log_error:
            logger.error(
                f"Exception handled: {exception.__class__.__name__}: {str(exception)}"
            )

        # Django REST Framework ValidationError 처리
        if exception.__class__.__name__ == "ValidationError":
            # DRF ValidationError는 detail 속성을 가짐
            error_detail = getattr(exception, "detail", str(exception))
            return cls.bad_request(
                message=message or "유효성 검사에 실패했습니다.",
                data=(
                    error_detail
                    if isinstance(error_detail, dict)
                    else {"error": str(error_detail)}
                ),
            )

        # rest_framework_simplejwt TokenError 처리
        elif exception.__class__.__name__ == "TokenError":
            return cls.bad_request(
                message=message or "토큰이 유효하지 않거나 만료되었습니다.",
                data={"error": str(exception)},
            )

        # ValueError는 일반적으로 400 Bad Request
        elif isinstance(exception, ValueError):
            return cls.bad_request(
                message=message or "잘못된 요청입니다.", data={"error": str(exception)}
            )

        # KeyError는 필수 파라미터 누락
        elif isinstance(exception, KeyError):
            return cls.bad_request(
                message=message or "필수 파라미터가 누락되었습니다.",
                data={"error": f"Missing required field: {str(exception)}"},
            )

        # PermissionError는 403 Forbidden
        elif isinstance(exception, PermissionError):
            return cls.forbidden(
                message=message or "권한이 없습니다.", data={"error": str(exception)}
            )

        # FileNotFoundError, DoesNotExist 등은 404
        elif isinstance(exception, (FileNotFoundError, AttributeError)):
            if "DoesNotExist" in exception.__class__.__name__:
                return cls.not_found(
                    message=message or "리소스를 찾을 수 없습니다.",
                    data={"error": str(exception)},
                )

        # 그 외는 500 서버 오류
        return cls.server_error(
            message=message or "서버 오류가 발생했습니다.",
            data={"error": str(exception) if log_error else None},
        )

    @classmethod
    def handle(cls, func):
        """데코레이터로 사용하여 자동으로 예외 처리"""

        def wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                return cls.from_exception(e)

        return wrapper
