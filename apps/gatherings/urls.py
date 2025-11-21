from django.urls import path

from apps.gatherings.views.category_views import (
    CategoryDetailView,
    CategoryListView,
    CategoryManageView,
    ChildCategoryListView,
    ParentCategoryListView,
)
from apps.gatherings.views.gathering_views import (
    GatheringDetailView,
    GatheringListView,
    GatheringStatisticsView,
    GatheringStatusView,
    MyGatheringListView,
)
from apps.gatherings.views.member_views import (
    GatheringMemberListView,
    LeaderTransferView,
    MemberApprovalView,
    MemberCancelJoinView,
    MemberJoinView,
    MemberLeaveView,
    MemberRemoveView,
    MemberStatusCheckView,
    PendingMemberListView,
)

app_name = "gatherings"

urlpatterns = [
    # Category URLs
    path("categories/", CategoryListView.as_view(), name="category-list"),
    path("categories/parents/", ParentCategoryListView.as_view(), name="parent-category-list"),
    path("categories/<int:parent_id>/children/", ChildCategoryListView.as_view(), name="child-category-list"),
    path("categories/manage/", CategoryManageView.as_view(), name="category-create"),
    path("categories/<int:category_id>/", CategoryDetailView.as_view(), name="category-detail"),
    path("categories/<int:category_id>/manage/", CategoryManageView.as_view(), name="category-manage"),
    # Gathering URLs
    path("", GatheringListView.as_view(), name="gathering-list"),
    path("my/", MyGatheringListView.as_view(), name="my-gathering-list"),
    path("<int:gathering_id>/", GatheringDetailView.as_view(), name="gathering-detail"),
    path("<int:gathering_id>/status/", GatheringStatusView.as_view(), name="gathering-status"),
    path("<int:gathering_id>/statistics/", GatheringStatisticsView.as_view(), name="gathering-statistics"),
    # Member URLs
    path("<int:gathering_id>/members/", GatheringMemberListView.as_view(), name="member-list"),
    path("<int:gathering_id>/members/pending/", PendingMemberListView.as_view(), name="pending-member-list"),
    path("<int:gathering_id>/join/", MemberJoinView.as_view(), name="member-join"),
    path("<int:gathering_id>/join/cancel/", MemberCancelJoinView.as_view(), name="member-cancel-join"),
    path("<int:gathering_id>/leave/", MemberLeaveView.as_view(), name="member-leave"),
    path("<int:gathering_id>/my-status/", MemberStatusCheckView.as_view(), name="member-status-check"),
    path("members/<int:member_id>/approval/", MemberApprovalView.as_view(), name="member-approval"),
    path("<int:gathering_id>/members/<int:member_id>/remove/", MemberRemoveView.as_view(), name="member-remove"),
    path("<int:gathering_id>/transfer-leadership/", LeaderTransferView.as_view(), name="leader-transfer"),
]
