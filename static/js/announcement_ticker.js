document.addEventListener('DOMContentLoaded', function () {
    const tickerContainer = document.getElementById('announcement-ticker');
    if (!tickerContainer) return;

    const tickerContent = tickerContainer.querySelector('.ticker-content');
    if (!tickerContent) return;

    const announcements = tickerContainer.querySelectorAll('.ticker-item');
    if (announcements.length === 0) return;

    // Show all announcements (they will scroll horizontally)
    announcements.forEach(announcement => {
        announcement.style.display = 'inline-flex';
    });

    // Pause scrolling on hover
    tickerContainer.addEventListener('mouseenter', function () {
        tickerContent.style.animationPlayState = 'paused';
    });

    // Resume scrolling when mouse leaves
    tickerContainer.addEventListener('mouseleave', function () {
        tickerContent.style.animationPlayState = 'running';
    });
});
