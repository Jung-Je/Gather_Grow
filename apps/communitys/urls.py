from django.urls import path

from apps.communitys.views.answer_views import (
    AnswerDetailView,
    AnswerListView,
    MyAnswerListView,
)
from apps.communitys.views.question_views import (
    MyQuestionListView,
    QuestionDetailView,
    QuestionListView,
    QuestionSolvedToggleView,
)

app_name = "communitys"

urlpatterns = [
    # Question URLs
    path("questions/", QuestionListView.as_view(), name="question-list"),
    path("questions/my/", MyQuestionListView.as_view(), name="my-question-list"),
    path("questions/<int:question_id>/", QuestionDetailView.as_view(), name="question-detail"),
    path("questions/<int:question_id>/solved/", QuestionSolvedToggleView.as_view(), name="question-solved-toggle"),
    # Answer URLs
    path("questions/<int:question_id>/answers/", AnswerListView.as_view(), name="answer-list"),
    path("answers/my/", MyAnswerListView.as_view(), name="my-answer-list"),
    path("answers/<int:answer_id>/", AnswerDetailView.as_view(), name="answer-detail"),
]
