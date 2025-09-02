from django.db.models import Q
import django_filters
from .models import Program, CourseAllocation, Course


class ProgramFilter(django_filters.FilterSet):
    title = django_filters.CharFilter(lookup_expr="icontains", label="")

    class Meta:
        model = Program
        fields = ["title"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Change html classes and placeholders
        self.filters["title"].field.widget.attrs.update(
            {"class": "au-input", "placeholder": "Program name"}
        )


class CourseAllocationFilter(django_filters.FilterSet):
    lecturer = django_filters.CharFilter(method="filter_by_lecturer", label="")
    course = django_filters.CharFilter(method="filter_by_course", label="")
    program = django_filters.CharFilter(method="filter_by_program", label="")
    semester = django_filters.CharFilter(method="filter_by_semester", label="")
    session = django_filters.CharFilter(method="filter_by_session", label="")

    class Meta:
        model = CourseAllocation
        fields = []

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Change html classes and placeholders
        self.filters["lecturer"].field.widget.attrs.update(
            {"class": "au-input", "placeholder": "Lecturer"}
        )
        self.filters["course"].field.widget.attrs.update(
            {"class": "au-input", "placeholder": "Course"}
        )
        self.filters["program"].field.widget.attrs.update(
            {"class": "au-input", "placeholder": "Branch/Program"}
        )
        self.filters["semester"].field.widget.attrs.update(
            {"class": "au-input", "placeholder": "Semester (First/Second/Third)"}
        )
        self.filters["session"].field.widget.attrs.update(
            {"class": "au-input", "placeholder": "Session (e.g., 2024/2025)"}
        )

    def filter_by_lecturer(self, queryset, name, value):
        return queryset.filter(
            Q(lecturer__first_name__icontains=value)
            | Q(lecturer__last_name__icontains=value)
        )

    def filter_by_course(self, queryset, name, value):
        return queryset.filter(courses__title__icontains=value)

    def filter_by_program(self, queryset, name, value):
        return queryset.filter(courses__program__title__icontains=value)

    def filter_by_semester(self, queryset, name, value):
        return queryset.filter(courses__semester__icontains=value)

    def filter_by_session(self, queryset, name, value):
        return queryset.filter(session__session__icontains=value)
