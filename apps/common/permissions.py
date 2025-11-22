from rest_framework import permissions


class IsOwnerOrReadOnly(permissions.BasePermission):
    """
    객체의 소유자만 수정/삭제할 수 있도록 제한하는 Permission

    - 읽기 권한: 모든 인증된 사용자
    - 쓰기 권한 (PUT, PATCH, DELETE): 객체의 소유자만 가능

    사용법:
        class MyView(APIView):
            permission_classes = [IsAuthenticated, IsOwnerOrReadOnly]

    Note:
        객체는 'user' 속성을 가져야 합니다.
    """

    def has_object_permission(self, request, view, obj):
        """객체 레벨 권한 체크

        Args:
            request: HTTP 요청 객체
            view: 뷰 객체
            obj: 권한을 체크할 객체

        Returns:
            bool: 권한이 있으면 True, 없으면 False
        """
        # 읽기 권한은 모든 요청에 허용
        if request.method in permissions.SAFE_METHODS:
            return True

        # 쓰기 권한은 객체의 소유자만 허용
        return obj.user == request.user


class IsLeaderOrReadOnly(permissions.BasePermission):
    """
    모임장만 수정/삭제할 수 있도록 제한하는 Permission

    - 읽기 권한: 모든 인증된 사용자
    - 쓰기 권한 (PUT, PATCH, DELETE): 모임장만 가능

    사용법:
        class GatheringUpdateView(APIView):
            permission_classes = [IsAuthenticated, IsLeaderOrReadOnly]

    Note:
        gathering 객체에 접근 가능해야 합니다.
    """

    def has_object_permission(self, request, view, obj):
        """객체 레벨 권한 체크

        Args:
            request: HTTP 요청 객체
            view: 뷰 객체
            obj: Gathering 객체

        Returns:
            bool: 권한이 있으면 True, 없으면 False
        """
        # 읽기 권한은 모든 요청에 허용
        if request.method in permissions.SAFE_METHODS:
            return True

        # 쓰기 권한은 모임장만 허용
        return obj.user == request.user


class IsAdminOrReadOnly(permissions.BasePermission):
    """
    관리자만 생성/수정/삭제할 수 있도록 제한하는 Permission

    - 읽기 권한: 모든 사용자
    - 쓰기 권한: 관리자만 가능

    사용법:
        class CategoryCreateView(APIView):
            permission_classes = [IsAdminOrReadOnly]
    """

    def has_permission(self, request, view):
        """뷰 레벨 권한 체크

        Args:
            request: HTTP 요청 객체
            view: 뷰 객체

        Returns:
            bool: 권한이 있으면 True, 없으면 False
        """
        # 읽기 권한은 모든 요청에 허용
        if request.method in permissions.SAFE_METHODS:
            return True

        # 쓰기 권한은 관리자만 허용
        return request.user and request.user.is_authenticated and request.user.is_staff
