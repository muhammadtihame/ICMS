// Dashboard JavaScript functionality
$(document).ready(function() {
    // Initialize dashboard components
    console.log('Dashboard initialized');
    
    // Chart initialization (if using charts)
    if (typeof Chart !== 'undefined') {
        // Initialize any charts here
    }
    
    // Dashboard refresh functionality
    function refreshDashboard() {
        // Refresh dashboard data
        location.reload();
    }
    
    // Auto-refresh every 5 minutes (300000 ms)
    setInterval(refreshDashboard, 300000);
    
    // Handle dashboard notifications
    $('.notification-toggle').on('click', function() {
        $(this).next('.notification-content').toggle();
    });
    
    // Handle quick actions
    $('.quick-action').on('click', function() {
        var action = $(this).data('action');
        if (action) {
            window.location.href = action;
        }
    });
    
    // Initialize tooltips
    if (typeof bootstrap !== 'undefined') {
        var tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
        var tooltipList = tooltipTriggerList.map(function (tooltipTriggerEl) {
            return new bootstrap.Tooltip(tooltipTriggerEl);
        });
    }
});
