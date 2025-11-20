from typing import Any

from drf_spectacular.utils import OpenApiParameter, OpenApiResponse, extend_schema
from rest_framework.pagination import PageNumberPagination
from rest_framework.permissions import IsAuthenticated, IsAuthenticatedOrReadOnly
from rest_framework.views import APIView

from apps.common.responses import APIResponse
from apps.communitys.models import Answer, Question
from apps.communitys.serializers.answer_serializer import (
    AnswerCreateSerializer,
    AnswerDetailSerializer,
    AnswerListSerializer,
    AnswerUpdateSerializer,
)


class AnswerPagination(PageNumberPagination):
    """답변 목록 페이지네이션"""

    page_size = 20
    page_size_query_param = "page_size"
    max_page_size = 100


class AnswerListView(APIView):
    """답변 목록 조회 및 생성 API"""

    permission_classes = [IsAuthenticatedOrReadOnly]

    @extend_schema(
        summary="답변 목록 조회",
        description="특정 질문에 달린 답변 목록을 조회합니다.",
        parameters=[
            OpenApiParameter(
                name="question_id",
                type=int,
                location=OpenApiParameter.PATH,
                description="질문 ID",
            ),
            OpenApiParameter(name="page", type=int, description="페이지 번호 (기본값: 1)"),
            OpenApiParameter(name="page_size", type=int, description="페이지 크기 (기본값: 20, 최대: 100)"),
        ],
        responses={
            200: AnswerListSerializer(many=True),
            404: OpenApiResponse(description="존재하지 않는 질문"),
        },
        tags=["Q&A"],
    )
    def get(self, request: Any, question_id: int) -> APIResponse:
        """답변 목록 조회

        Args:
            question_id: 질문 ID
            request: HTTP 요청 객체

        Query Parameters:
            page (int): 페이지 번호 (default: 1)
            page_size (int): 페이지 크기 (default: 20, max: 100)

        Returns:
            APIResponse:
                - 200: 답변 목록 (페이지네이션)
                - 404: 존재하지 않는 질문
        """
        try:
            # 질문 존재 여부 확인
            question = Question.objects.get(id=question_id)

            # 답변 목록 조회
            answers = Answer.objects.filter(question=question).select_related("user").order_by("created_at")

            # 페이지네이션
            paginator = AnswerPagination()
            paginated_answers = paginator.paginate_queryset(answers, request)
            serializer = AnswerListSerializer(paginated_answers, many=True)

            return APIResponse.success(
                message="답변 목록 조회 성공",
                data={
                    "count": paginator.page.paginator.count,
                    "next": paginator.get_next_link(),
                    "previous": paginator.get_previous_link(),
                    "results": serializer.data,
                },
            )

        except Question.DoesNotExist:
            return APIResponse.not_found(message="존재하지 않는 질문입니다.")

    @extend_schema(
        summary="답변 작성",
        description="질문에 답변을 작성합니다. 인증이 필요합니다. 이미 해결된 질문에는 답변을 작성할 수 없습니다.",
        parameters=[
            OpenApiParameter(
                name="question_id",
                type=int,
                location=OpenApiParameter.PATH,
                description="질문 ID",
            ),
        ],
        request=AnswerCreateSerializer,
        responses={
            201: AnswerDetailSerializer,
            400: OpenApiResponse(description="잘못된 입력 데이터 또는 이미 해결된 질문"),
            401: OpenApiResponse(description="인증 필요"),
            404: OpenApiResponse(description="존재하지 않는 질문"),
        },
        tags=["Q&A"],
    )
    def post(self, request: Any, question_id: int) -> APIResponse:
        """답변 작성

        Args:
            question_id: 질문 ID
            request: HTTP 요청 객체 (인증 필요)
                - content (str): 답변 내용 (최소 10자)

        Returns:
            APIResponse:
                - 201: 답변 작성 성공
                - 400: 잘못된 입력 또는 이미 해결된 질문
                - 401: 인증 필요
                - 404: 존재하지 않는 질문
        """
        try:
            # 질문 존재 여부 확인
            question = Question.objects.get(id=question_id)

            # 데이터에 question_id 추가
            data = request.data.copy()
            data["question"] = question_id

            # 데이터 검증
            serializer = AnswerCreateSerializer(data=data)
            serializer.is_valid(raise_exception=True)

            # 답변 생성
            answer = Answer.objects.create(
                question=question, user=request.user, content=serializer.validated_data["content"]
            )

            result_serializer = AnswerDetailSerializer(answer)
            return APIResponse.created(message="답변이 작성되었습니다.", data=result_serializer.data)

        except Question.DoesNotExist:
            return APIResponse.not_found(message="존재하지 않는 질문입니다.")
        except Exception as e:
            return APIResponse.from_exception(e, message="답변 작성에 실패했습니다.")


class AnswerDetailView(APIView):
    """답변 상세 조회, 수정, 삭제 API"""

    permission_classes = [IsAuthenticatedOrReadOnly]

    @extend_schema(
        summary="답변 상세 조회",
        description="특정 답변의 상세 정보를 조회합니다.",
        responses={
            200: AnswerDetailSerializer,
            404: OpenApiResponse(description="존재하지 않는 답변"),
        },
        tags=["Q&A"],
    )
    def get(self, request: Any, answer_id: int) -> APIResponse:
        """답변 상세 조회

        Args:
            answer_id: 답변 ID

        Returns:
            APIResponse:
                - 200: 답변 상세 정보
                - 404: 존재하지 않는 답변
        """
        try:
            answer = Answer.objects.select_related("question", "user").get(id=answer_id)
            serializer = AnswerDetailSerializer(answer)
            return APIResponse.success(message="답변 조회 성공", data=serializer.data)

        except Answer.DoesNotExist:
            return APIResponse.not_found(message="존재하지 않는 답변입니다.")

    @extend_schema(
        summary="답변 수정",
        description="답변을 수정합니다. 작성자만 수정할 수 있습니다.",
        request=AnswerUpdateSerializer,
        responses={
            200: AnswerDetailSerializer,
            400: OpenApiResponse(description="잘못된 입력"),
            401: OpenApiResponse(description="인증 필요"),
            403: OpenApiResponse(description="권한 없음"),
            404: OpenApiResponse(description="존재하지 않는 답변"),
        },
        tags=["Q&A"],
    )
    def patch(self, request: Any, answer_id: int) -> APIResponse:
        """답변 수정

        Args:
            answer_id: 답변 ID
            request: HTTP 요청 객체 (작성자만 가능)
                - content (str): 답변 내용

        Returns:
            APIResponse:
                - 200: 답변 수정 성공
                - 400: 잘못된 입력
                - 401: 인증 필요
                - 403: 권한 없음
                - 404: 존재하지 않는 답변
        """
        try:
            answer = Answer.objects.select_related("user").get(id=answer_id)

            # 작성자만 수정 가능
            if answer.user != request.user:
                return APIResponse.forbidden(message="답변 작성자만 수정할 수 있습니다.")

            # 데이터 검증
            serializer = AnswerUpdateSerializer(instance=answer, data=request.data, partial=True)
            serializer.is_valid(raise_exception=True)

            # 답변 업데이트
            answer.content = serializer.validated_data["content"]
            answer.save()

            result_serializer = AnswerDetailSerializer(answer)
            return APIResponse.success(message="답변이 수정되었습니다.", data=result_serializer.data)

        except Answer.DoesNotExist:
            return APIResponse.not_found(message="존재하지 않는 답변입니다.")
        except Exception as e:
            return APIResponse.from_exception(e, message="답변 수정에 실패했습니다.")

    @extend_schema(
        summary="답변 삭제",
        description="답변을 삭제합니다. 작성자만 삭제할 수 있습니다.",
        responses={
            200: OpenApiResponse(description="답변 삭제 성공"),
            401: OpenApiResponse(description="인증 필요"),
            403: OpenApiResponse(description="권한 없음"),
            404: OpenApiResponse(description="존재하지 않는 답변"),
        },
        tags=["Q&A"],
    )
    def delete(self, request: Any, answer_id: int) -> APIResponse:
        """답변 삭제

        Args:
            answer_id: 답변 ID
            request: HTTP 요청 객체 (작성자만 가능)

        Returns:
            APIResponse:
                - 200: 답변 삭제 성공
                - 401: 인증 필요
                - 403: 권한 없음
                - 404: 존재하지 않는 답변
        """
        try:
            answer = Answer.objects.select_related("user").get(id=answer_id)

            # 작성자만 삭제 가능
            if answer.user != request.user:
                return APIResponse.forbidden(message="답변 작성자만 삭제할 수 있습니다.")

            answer.delete()
            return APIResponse.success(message="답변이 삭제되었습니다.")

        except Answer.DoesNotExist:
            return APIResponse.not_found(message="존재하지 않는 답변입니다.")
        except Exception as e:
            return APIResponse.from_exception(e, message="답변 삭제에 실패했습니다.")


class MyAnswerListView(APIView):
    """내가 작성한 답변 목록 API"""

    permission_classes = [IsAuthenticated]

    @extend_schema(
        summary="내가 작성한 답변 목록 조회",
        description="내가 작성한 답변 목록을 조회합니다.",
        parameters=[
            OpenApiParameter(name="page", type=int, description="페이지 번호 (기본값: 1)"),
            OpenApiParameter(name="page_size", type=int, description="페이지 크기 (기본값: 20, 최대: 100)"),
        ],
        responses={
            200: AnswerListSerializer(many=True),
            401: OpenApiResponse(description="인증 필요"),
        },
        tags=["Q&A"],
    )
    def get(self, request: Any) -> APIResponse:
        """내가 작성한 답변 목록 조회

        Query Parameters:
            page (int): 페이지 번호 (default: 1)
            page_size (int): 페이지 크기 (default: 20, max: 100)

        Returns:
            APIResponse:
                - 200: 내 답변 목록 (페이지네이션)
                - 401: 인증 필요
        """
        answers = Answer.objects.filter(user=request.user).select_related("question", "user").order_by("-created_at")

        paginator = AnswerPagination()
        paginated_answers = paginator.paginate_queryset(answers, request)
        serializer = AnswerListSerializer(paginated_answers, many=True)

        return APIResponse.success(
            message="내 답변 목록 조회 성공",
            data={
                "count": paginator.page.paginator.count,
                "next": paginator.get_next_link(),
                "previous": paginator.get_previous_link(),
                "results": serializer.data,
            },
        )
