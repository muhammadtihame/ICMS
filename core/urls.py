from django.urls import path

from .views import (
    home_view,
    post_add,
    edit_post,
    delete_post,
    predict_api,
    predict_admin_page,
    predict_student_page,
    timetable_regenerate,
    timetable_admin_view,
    session_list_view,
    session_add_view,
    session_update_view,
    session_delete_view,
    semester_list_view,
    semester_add_view,
    semester_update_view,
    semester_delete_view,
    dashboard_view,
    announcement_list_view,
    announcement_add_view,
    announcement_edit_view,
    announcement_delete_view,
    comprehensive_timetable_view,
    batch_timetable_view,
    attendance_dashboard,
    admin_attendance,
    lecturer_attendance,
    student_attendance,
    batch_attendance,
    detention_list,
    attendance_reports,
    admin_feedback_view,
    feedback_detail_view,
    feedback_export_view,
    test_student_access,
    feedback_view,
    search_suggestions_api,
    universal_search_demo_view,
)


urlpatterns = [
    # Accounts url
    path("", home_view, name="home"),
    path("add_item/", post_add, name="add_item"),
    path("item/<int:pk>/edit/", edit_post, name="edit_post"),
    path("item/<int:pk>/delete/", delete_post, name="delete_post"),
    path("session/", session_list_view, name="session_list"),
    path("session/add/", session_add_view, name="add_session"),
    path("session/<int:pk>/edit/", session_update_view, name="edit_session"),
    path("session/<int:pk>/delete/", session_delete_view, name="delete_session"),
    path("semester/", semester_list_view, name="semester_list"),
    path("semester/add/", semester_add_view, name="add_semester"),
    path("semester/<int:pk>/edit/", semester_update_view, name="edit_semester"),
    path("semester/<int:pk>/delete/", semester_delete_view, name="delete_semester"),
    path("dashboard/", dashboard_view, name="dashboard"),
    path("timetable/", timetable_admin_view, name="timetable_admin"),
    path("timetable/comprehensive/", comprehensive_timetable_view, name="comprehensive_timetable"),
    path("timetable/batch/<int:batch_id>/", batch_timetable_view, name="batch_timetable"),
    
    # Attendance Management URLs
    path("attendance/", attendance_dashboard, name="attendance_dashboard"),
    path("attendance/admin/", admin_attendance, name="admin_attendance"),
    path("attendance/lecturer/", lecturer_attendance, name="lecturer_attendance"),
    path("attendance/student/", student_attendance, name="student_attendance"),
    path("attendance/batch/<int:batch_id>/", batch_attendance, name="batch_attendance"),
    path("attendance/detention/", detention_list, name="detention_list"),
    path("attendance/reports/", attendance_reports, name="attendance_reports"),
    
    # Predict Performance
    path("predict/", predict_api, name="predict_api"),
    path("predict/admin/", predict_admin_page, name="predict_admin_page"),
    path("predict/student/", predict_student_page, name="predict_student_page"),
    path("timetable/regenerate/", timetable_regenerate, name="timetable_regenerate"),
    
    # Announcement URLs
    path("announcements/", announcement_list_view, name="announcement_list"),
    path("announcements/add/", announcement_add_view, name="announcement_add"),
    path("announcements/<int:pk>/edit/", announcement_edit_view, name="announcement_edit"),
    path("announcements/<int:pk>/delete/", announcement_delete_view, name="announcement_delete"),

    # Student Feedback System
    path('feedback/', feedback_view, name='feedback'),
    path('admin-feedback/', admin_feedback_view, name='admin_feedback'),
    path('admin-feedback/<int:lecturer_id>/', feedback_detail_view, name='feedback_detail'),
    path('admin-feedback/export/', feedback_export_view, name='feedback_export'),

    # Test Student Access
    path('test-student-access/', test_student_access, name='test_student_access'),
    
    # Universal Search Suggestions API
    path('search-suggestions/', search_suggestions_api, name='search_suggestions_api'),
    
    # Universal Search Demo
    path('universal-search-demo/', universal_search_demo_view, name='universal_search_demo'),
]
