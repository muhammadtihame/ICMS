from itertools import chain
from django.views.generic import ListView
from django.contrib.auth import get_user_model
from core.models import NewsAndEvents, Semester, Session, Batch
from course.models import Program, Course
from quiz.models import Quiz

User = get_user_model()


class SearchView(ListView):
    template_name = "search/search_view.html"
    paginate_by = 20
    count = 0

    def get_context_data(self, *args, **kwargs):
        context = super().get_context_data(*args, **kwargs)
        context["count"] = self.count or 0
        context["query"] = self.request.GET.get("q")
        return context

    def get_queryset(self):
        request = self.request
        query = request.GET.get("q", None)

        if query is not None:
            # Core content
            news_events_results = NewsAndEvents.objects.search(query)
            
            # Course content
            program_results = Program.objects.search(query)
            course_results = Course.objects.search(query)
            
            # Quiz content
            quiz_results = Quiz.objects.search(query)
            
            # User content (students and lecturers)
            user_results = User.objects.search(query)
            
            # Academic content
            semester_results = Semester.objects.filter(
                semester__icontains=query
            ) | Semester.objects.filter(session__title__icontains=query)
            
            session_results = Session.objects.filter(
                title__icontains=query
            ) | Session.objects.filter(description__icontains=query)
            
            batch_results = Batch.objects.filter(
                name__icontains=query
            ) | Batch.objects.filter(program__title__icontains=query)

            # combine querysets
            queryset_chain = chain(
                news_events_results,
                program_results,
                course_results,
                quiz_results,
                user_results,
                semester_results,
                session_results,
                batch_results
            )
            queryset = sorted(
                queryset_chain, key=lambda instance: instance.pk, reverse=True
            )
            self.count = len(queryset)  # since queryset is actually a list
            return queryset
        return NewsAndEvents.objects.none()  # just an empty queryset as default
