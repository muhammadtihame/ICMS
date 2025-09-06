from django.urls import path
from django.conf import settings
from .views import (
    home_view,
    announcement_list_view,
    announcement_add_view,
    announcement_edit_view,
    announcement_delete_view,
    dashboard_view,
    timetable_admin_view,
    session_list_view,
    session_add_view,
    session_update_view,
    session_delete_view,
    semester_list_view,
    semester_add_view,
    semester_update_view,
    semester_delete_view,
    comprehensive_timetable_view,
    batch_timetable_view,
    feedback_popup_view,
    admin_feedback_view,
    feedback_detail_view,
    feedback_export_view,
    feedback_view,
    universal_search_demo_view,
    tuition_fee_dashboard,
    student_tuition_fees,
    update_tuition_fee,
    bulk_update_tuition_fees,
    tuition_fee_reports,
    ai_predictions_view,
    student_performance_prediction,
    test_view,
    health_check,
    # Post management views
    post_add,
    edit_post,
    delete_post,
    # Attendance views
    attendance_dashboard,
    admin_attendance,
    lecturer_attendance,
    student_attendance,
    batch_attendance,
    attendance_reports,
    # Prediction views
    predict_admin_page,
    predict_student_page,
    predict_api,
    # Attendance views
    detention_list,
    # Timetable views
    timetable_regenerate,
    # Result checking
    check_result_by_enrollment,
)

urlpatterns = [
    # Health check endpoint for Render
    path('health/', health_check, name='health_check'),
    
    # Test view to bypass all redirects
    path('test/', test_view, name='test_view'),
    
    # Home page
    path("", home_view, name="home"),
    
    # Dashboard
    path("dashboard/", dashboard_view, name="dashboard"),
    
    # Session Management
    path("session/", session_list_view, name="session_list"),
    path("session/add/", session_add_view, name="add_session"),
    path("session/<int:pk>/edit/", session_update_view, name="edit_session"),
    path("session/<int:pk>/delete/", session_delete_view, name="delete_session"),
    
    # Semester Management
    path("semester/", semester_list_view, name="semester_list"),
    path("semester/add/", semester_add_view, name="add_semester"),
    path("semester/<int:pk>/edit/", semester_update_view, name="edit_semester"),
    path("semester/<int:pk>/delete/", semester_delete_view, name="delete_semester"),
    
    # Timetable Management
    path("timetable/", timetable_admin_view, name="timetable_admin"),
    path("timetable/comprehensive/", comprehensive_timetable_view, name="comprehensive_timetable"),
    path("timetable/batch/<int:batch_id>/", batch_timetable_view, name="batch_timetable"),
    path("timetable/regenerate/", timetable_regenerate, name="timetable_regenerate"),
    
    # Announcement URLs
    path("announcements/", announcement_list_view, name="announcement_list"),
    path("announcements/add/", announcement_add_view, name="announcement_add"),
    path("announcements/<int:pk>/edit/", announcement_edit_view, name="announcement_edit"),
    path("announcements/<int:pk>/delete/", announcement_delete_view, name="announcement_delete"),
    
    # Post Management URLs
    path("add_item/", post_add, name="add_item"),
    path("edit_item/<int:pk>/", edit_post, name="edit_post"),
    path("delete_item/<int:pk>/", delete_post, name="delete_post"),

    # Student Feedback System
    path('feedback/', feedback_view, name='feedback'),
    path('feedback-popup/', feedback_popup_view, name='feedback_popup'),
    path('admin-feedback/', admin_feedback_view, name='admin_feedback'),
    path('admin-feedback/<int:lecturer_id>/', feedback_detail_view, name='feedback_detail'),
    path('admin-feedback/export/', feedback_export_view, name='feedback_export'),

    # Universal Search Demo
    path('universal-search-demo/', universal_search_demo_view, name='universal_search_demo'),

    # Tuition Fee Management
    path('tuition-fees/', tuition_fee_dashboard, name='tuition_fee_dashboard'),
    path('tuition-fees/student/<int:student_id>/', student_tuition_fees, name='student_tuition_fees'),
    path('tuition-fees/update/<int:fee_id>/', update_tuition_fee, name='update_tuition_fee'),
    path('tuition-fees/bulk-update/', bulk_update_tuition_fees, name='bulk_update_tuition_fees'),
    path('tuition-fees/reports/', tuition_fee_reports, name='tuition_fee_reports'),
    
    # AI Predictions and Analytics
    path('ai-predictions/', ai_predictions_view, name='ai_predictions'),
    path('ai-predictions/student/<int:student_id>/', student_performance_prediction, name='student_performance_prediction'),
    
    # Prediction Pages
    path('predict-admin/', predict_admin_page, name='predict_admin_page'),
    path('predict-student/', predict_student_page, name='predict_student_page'),
    path('predict-api/', predict_api, name='predict_api'),
    
    # Attendance Management
    path('attendance/', attendance_dashboard, name='attendance_dashboard'),
    path('attendance/admin/', admin_attendance, name='admin_attendance'),
    path('attendance/lecturer/', lecturer_attendance, name='lecturer_attendance'),
    path('attendance/student/', student_attendance, name='student_attendance'),
    path('attendance/batch/<int:batch_id>/', batch_attendance, name='batch_attendance'),
    path('attendance/reports/', attendance_reports, name='attendance_reports'),
    path('attendance/detention/', detention_list, name='detention_list'),
    
    # Public Result Checking
    path('check-result/', check_result_by_enrollment, name='check_result_by_enrollment'),
]

# Add media file serving for production
if not settings.DEBUG:
    from .media_views import serve_media
    urlpatterns += [
        path('media/<path:path>', serve_media, name='serve_media'),
    ]
