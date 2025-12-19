from django.urls import path

from .views import SchoolListView, SchoolDetailView, InstructorListView, InstructorDetailView

urlpatterns = [
    path("schools", SchoolListView.as_view()),
    path("schools/<int:pk>", SchoolDetailView.as_view()),
    path("instructors", InstructorListView.as_view()),
    path("instructors/<int:pk>", InstructorDetailView.as_view()),
]

