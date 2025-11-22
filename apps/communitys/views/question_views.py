from typing import Any

from django.db.models import Count, Q
from django.db.utils import DatabaseError, IntegrityError
from drf_spectacular.utils import (
    OpenApiParameter,
    OpenApiResponse,
    extend_schema,
)
from rest_framework.exceptions import ValidationError
from rest_framework.pagination import PageNumberPagination
from rest_framework.permissions import IsAuthenticated, IsAuthenticatedOrReadOnly
from rest_framework.views import APIView

from apps.common.responses import APIResponse
from apps.communitys.models import Question
from apps.communitys.serializers.question_serializer import (
    QuestionCreateSerializer,
    QuestionDetailSerializer,
    QuestionListSerializer,
    QuestionUpdateSerializer,
)
from apps.communitys.services.question_service import QuestionService


class QuestionPagination(PageNumberPagination):
    """질문 목록 페이지네이션"""

    page_size = 20
    page_size_query_param = "page_size"
    max_page_size = 100


class QuestionListView(APIView):
    """질문 목록 조회 및 생성 API"""

    permission_classes = [IsAuthenticatedOrReadOnly]

    @extend_schema(
        summary="질문 목록 조회",
        description="Q&A 질문 목록을 조회합니다. 카테고리, 답변 여부, 검색어로 필터링할 수 있습니다.",
        parameters=[
            OpenApiParameter(name="category", type=int, description="카테고리 ID"),
            OpenApiParameter(name="is_solved", type=bool, description="답변 여부 (true: 해결됨, false: 미해결)"),
            OpenApiParameter(name="search", type=str, description="검색어 (제목/내용)"),
            OpenApiParameter(name="page", type=int, description="페이지 번호 (기본값: 1)"),
            OpenApiParameter(name="page_size", type=int, description="페이지 크기 (기본값: 20, 최대: 100)"),
        ],
        responses={
            200: QuestionListSerializer(many=True),
            400: OpenApiResponse(description="잘못된 필터 값"),
        },
        tags=["Q&A"],
    )
    def get(self, request: Any) -> APIResponse:
        """질문 목록 조회 (필터링 지원)

        Query Parameters:
            category (int): 카테고리 ID
            is_solved (bool): 답변 여부 (true/false)
            search (str): 검색어 (제목/내용)
            page (int): 페이지 번호 (default: 1)
            page_size (int): 페이지 크기 (default: 20, max: 100)

        Returns:
            APIResponse:
                - 200: 질문 목록 (페이지네이션)
                - 400: 잘못된 필터 값
        """
        # 필터 파라미터 추출
        category_id = request.query_params.get("category")
        is_solved = request.query_params.get("is_solved")
        search = request.query_params.get("search")

        # category_id를 int로 변환
        if category_id:
            try:
                category_id = int(category_id)
            except ValueError:
                return APIResponse.bad_request(message="잘못된 카테고리 ID입니다.")

        # is_solved를 boolean으로 변환
        if is_solved is not None:
            is_solved = is_solved.lower() == "true"

        # 질문 목록 조회 (N+1 쿼리 방지를 위한 annotate 추가)
        queryset = Question.objects.select_related("category", "user").annotate(answer_count=Count("answers")).all()

        if category_id:
            queryset = queryset.filter(category_id=category_id)

        if is_solved is not None:
            queryset = queryset.filter(is_solved=is_solved)

        if search:
            queryset = queryset.filter(Q(title__icontains=search) | Q(content__icontains=search))

        queryset = queryset.order_by("-created_at")

        # 페이지네이션
        paginator = QuestionPagination()
        paginated_questions = paginator.paginate_queryset(queryset, request)
        serializer = QuestionListSerializer(paginated_questions, many=True)

        return APIResponse.success(
            message="질문 목록 조회 성공",
            data={
                "count": paginator.page.paginator.count,
                "next": paginator.get_next_link(),
                "previous": paginator.get_previous_link(),
                "results": serializer.data,
            },
        )

    @extend_schema(
        summary="질문 생성",
        description="새로운 질문을 작성합니다. 인증이 필요합니다.",
        request=QuestionCreateSerializer,
        responses={
            201: QuestionDetailSerializer,
            400: OpenApiResponse(description="잘못된 입력 데이터"),
            401: OpenApiResponse(description="인증 필요"),
        },
        tags=["Q&A"],
    )
    def post(self, request: Any) -> APIResponse:
        """질문 생성

        Args:
            request: HTTP 요청 객체 (인증 필요)
                - category (int): 카테고리 ID
                - title (str): 질문 제목 (최소 5자)
                - content (str): 질문 내용 (최소 10자)

        Returns:
            APIResponse:
                - 201: 질문 생성 성공
                - 400: 잘못된 입력 데이터
                - 401: 인증 필요
        """
        serializer = QuestionCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        # 질문 생성
        question = Question.objects.create(user=request.user, **serializer.validated_data)

        result_serializer = QuestionDetailSerializer(question)
        return APIResponse.created(message="질문이 작성되었습니다.", data=result_serializer.data)


class QuestionDetailView(APIView):
    """질문 상세 조회, 수정, 삭제 API"""

    permission_classes = [IsAuthenticatedOrReadOnly]

    @extend_schema(
        summary="질문 상세 조회",
        description="특정 질문의 상세 정보를 조회합니다. 조회 시 조회수가 증가합니다.",
        responses={
            200: QuestionDetailSerializer,
            404: OpenApiResponse(description="존재하지 않는 질문"),
        },
        tags=["Q&A"],
    )
    def get(self, request: Any, question_id: int) -> APIResponse:
        """질문 상세 조회

        Args:
            question_id: 질문 ID

        Returns:
            APIResponse:
                - 200: 질문 상세 정보
                - 404: 존재하지 않는 질문
        """
        # 서비스로 질문 조회 및 검증
        question = QuestionService.get_question_with_validation(question_id)
        if not question:
            return APIResponse.not_found(message="존재하지 않는 질문입니다.")

        # 조회수 증가
        question.increment_views()

        serializer = QuestionDetailSerializer(question)
        return APIResponse.success(message="질문 조회 성공", data=serializer.data)

    @extend_schema(
        summary="질문 수정",
        description="질문을 수정합니다. 작성자만 수정할 수 있으며, 답변이 달린 질문은 수정할 수 없습니다.",
        request=QuestionUpdateSerializer,
        responses={
            200: QuestionDetailSerializer,
            400: OpenApiResponse(description="잘못된 입력 또는 권한 없음"),
            401: OpenApiResponse(description="인증 필요"),
            404: OpenApiResponse(description="존재하지 않는 질문"),
        },
        tags=["Q&A"],
    )
    def patch(self, request: Any, question_id: int) -> APIResponse:
        """질문 수정

        Args:
            question_id: 질문 ID
            request: HTTP 요청 객체 (작성자만 가능)

        Returns:
            APIResponse:
                - 200: 질문 수정 성공
                - 400: 잘못된 입력 또는 권한 없음
                - 401: 인증 필요
                - 404: 존재하지 않는 질문
        """
        # 서비스로 질문 조회 및 검증
        question = QuestionService.get_question_with_validation(question_id)
        if not question:
            return APIResponse.not_found(message="존재하지 않는 질문입니다.")

        # 서비스로 권한 확인
        try:
            QuestionService.check_question_permission(question, request.user)
        except PermissionError as e:
            return APIResponse.forbidden(message=str(e))

        # instance를 전달하여 serializer 생성
        serializer = QuestionUpdateSerializer(instance=question, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)

        # 질문 업데이트
        for key, value in serializer.validated_data.items():
            setattr(question, key, value)
        question.save()

        result_serializer = QuestionDetailSerializer(question)
        return APIResponse.success(message="질문이 수정되었습니다.", data=result_serializer.data)

    @extend_schema(
        summary="질문 삭제",
        description="질문을 삭제합니다. 작성자만 삭제할 수 있으며, 답변이 달린 질문은 삭제할 수 없습니다.",
        responses={
            200: OpenApiResponse(description="질문 삭제 성공"),
            400: OpenApiResponse(description="권한 없음 또는 삭제 불가"),
            401: OpenApiResponse(description="인증 필요"),
            404: OpenApiResponse(description="존재하지 않는 질문"),
        },
        tags=["Q&A"],
    )
    def delete(self, request: Any, question_id: int) -> APIResponse:
        """질문 삭제

        Args:
            question_id: 질문 ID
            request: HTTP 요청 객체 (작성자만 가능)

        Returns:
            APIResponse:
                - 200: 질문 삭제 성공
                - 400: 권한 없음 또는 삭제 불가
                - 401: 인증 필요
                - 404: 존재하지 않는 질문
        """
        # 서비스로 질문 조회 및 검증
        question = QuestionService.get_question_with_validation(question_id)
        if not question:
            return APIResponse.not_found(message="존재하지 않는 질문입니다.")

        # 서비스로 권한 확인
        try:
            QuestionService.check_question_permission(question, request.user)
        except PermissionError as e:
            return APIResponse.forbidden(message=str(e))

        # 서비스로 수정/삭제 가능 여부 확인
        if not QuestionService.can_modify_question(question):
            return APIResponse.bad_request(message="답변이 달린 질문은 삭제할 수 없습니다.")

        question.delete()
        return APIResponse.success(message="질문이 삭제되었습니다.")


class QuestionSolvedToggleView(APIView):
    """질문 해결 여부 토글 API"""

    permission_classes = [IsAuthenticated]

    @extend_schema(
        summary="질문 해결 여부 토글",
        description="질문의 해결 여부를 변경합니다. 작성자만 변경할 수 있습니다.",
        responses={
            200: QuestionDetailSerializer,
            400: OpenApiResponse(description="권한 없음"),
            401: OpenApiResponse(description="인증 필요"),
            404: OpenApiResponse(description="존재하지 않는 질문"),
        },
        tags=["Q&A"],
    )
    def patch(self, request: Any, question_id: int) -> APIResponse:
        """질문 해결 여부 토글

        Args:
            question_id: 질문 ID
            request: HTTP 요청 객체 (작성자만 가능)

        Returns:
            APIResponse:
                - 200: 상태 변경 성공
                - 400: 권한 없음
                - 401: 인증 필요
                - 404: 존재하지 않는 질문
        """
        # 서비스로 질문 조회 및 검증
        question = QuestionService.get_question_with_validation(question_id)
        if not question:
            return APIResponse.not_found(message="존재하지 않는 질문입니다.")

        # 서비스로 권한 확인
        try:
            QuestionService.check_question_permission(question, request.user)
        except PermissionError as e:
            return APIResponse.forbidden(message=str(e))

        # 상태 토글
        if question.is_solved:
            question.mark_as_unsolved()
        else:
            question.mark_as_solved()

        serializer = QuestionDetailSerializer(question)
        return APIResponse.success(message="해결 여부가 변경되었습니다.", data=serializer.data)


class MyQuestionListView(APIView):
    """내가 작성한 질문 목록 API"""

    permission_classes = [IsAuthenticated]

    @extend_schema(
        summary="내가 작성한 질문 목록 조회",
        description="내가 작성한 질문 목록을 조회합니다. 답변 여부로 필터링할 수 있습니다.",
        parameters=[
            OpenApiParameter(name="is_solved", type=bool, description="답변 여부 (true: 해결됨, false: 미해결)"),
            OpenApiParameter(name="page", type=int, description="페이지 번호 (기본값: 1)"),
            OpenApiParameter(name="page_size", type=int, description="페이지 크기 (기본값: 20, 최대: 100)"),
        ],
        responses={
            200: QuestionListSerializer(many=True),
            401: OpenApiResponse(description="인증 필요"),
        },
        tags=["Q&A"],
    )
    def get(self, request: Any) -> APIResponse:
        """내가 작성한 질문 목록 조회

        Query Parameters:
            is_solved (bool, optional): 답변 여부 필터
            page (int): 페이지 번호 (default: 1)
            page_size (int): 페이지 크기 (default: 20, max: 100)

        Returns:
            APIResponse:
                - 200: 내 질문 목록 (페이지네이션)
                - 401: 인증 필요
        """
        is_solved = request.query_params.get("is_solved")

        # is_solved를 boolean으로 변환
        if is_solved is not None:
            is_solved = is_solved.lower() == "true"

        # N+1 쿼리 방지를 위한 annotate 추가
        queryset = (
            Question.objects.filter(user=request.user)
            .select_related("category", "user")
            .annotate(answer_count=Count("answers"))
        )

        if is_solved is not None:
            queryset = queryset.filter(is_solved=is_solved)

        queryset = queryset.order_by("-created_at")

        paginator = QuestionPagination()
        paginated_questions = paginator.paginate_queryset(queryset, request)
        serializer = QuestionListSerializer(paginated_questions, many=True)

        return APIResponse.success(
            message="내 질문 목록 조회 성공",
            data={
                "count": paginator.page.paginator.count,
                "next": paginator.get_next_link(),
                "previous": paginator.get_previous_link(),
                "results": serializer.data,
            },
        )
