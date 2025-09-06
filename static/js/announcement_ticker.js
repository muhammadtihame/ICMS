document.addEventListener('DOMContentLoaded', function () {
    const tickerContainer = document.getElementById('announcement-ticker');
    if (!tickerContainer) return;

    const announcements = tickerContainer.querySelectorAll('.ticker-item');
    if (announcements.length === 0) return;

    let currentIndex = 0;
    const totalAnnouncements = announcements.length;

    // Show the first announcement
    if (announcements.length > 0) {
        announcements[0].style.display = 'inline-flex';
    }

    // Function to cycle through announcements
    function cycleAnnouncements() {
        // Hide current announcement
        announcements[currentIndex].style.display = 'none';

        // Move to next announcement
        currentIndex = (currentIndex + 1) % totalAnnouncements;

        // Show next announcement
        announcements[currentIndex].style.display = 'inline-flex';
    }

    // Start cycling every 8 seconds (matching CSS animation duration)
    const cycleInterval = setInterval(cycleAnnouncements, 8000);

    // Pause cycling on hover
    tickerContainer.addEventListener('mouseenter', function () {
        clearInterval(cycleInterval);
        // Pause all animations
        announcements.forEach(announcement => {
            announcement.style.animationPlayState = 'paused';
        });
    });

    // Resume cycling when mouse leaves
    tickerContainer.addEventListener('mouseleave', function () {
        // Resume all animations
        announcements.forEach(announcement => {
            announcement.style.animationPlayState = 'running';
        });

        // Restart cycling
        cycleAnnouncements();
        const newCycleInterval = setInterval(cycleAnnouncements, 8000);

        // Store the new interval ID for cleanup
        tickerContainer.cycleInterval = newCycleInterval;
    });

    // Store interval ID for potential cleanup
    tickerContainer.cycleInterval = cycleInterval;
});
