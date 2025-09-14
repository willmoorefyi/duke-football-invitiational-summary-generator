// Client-side logo validation with fallback to poop emoji
document.addEventListener('DOMContentLoaded', function() {
    // Function to replace failed logo with poop emoji
    function replaceWithPoop(imgElement) {
        const teamName = imgElement.alt || 'Team';
        const poopSpan = document.createElement('span');
        poopSpan.className = 'team-logo emoji-logo';
        poopSpan.textContent = '💩';
        poopSpan.title = `Logo failed to load for ${teamName}`;
        imgElement.parentNode.replaceChild(poopSpan, imgElement);
    }

    // Find all team logo images and add enhanced error handling
    const logoImages = document.querySelectorAll('img.team-logo');

    logoImages.forEach(function(img) {
        // Set a timeout to handle slow-loading images
        const timeout = setTimeout(function() {
            replaceWithPoop(img);
        }, 10000); // 10 second timeout

        // Clear timeout if image loads successfully
        img.addEventListener('load', function() {
            clearTimeout(timeout);
        });

        // Handle immediate errors
        img.addEventListener('error', function() {
            clearTimeout(timeout);
            replaceWithPoop(this);
        });

        // Check if image is already broken (in case it loaded before DOM was ready)
        if (img.complete && img.naturalWidth === 0) {
            clearTimeout(timeout);
            replaceWithPoop(img);
        }
    });
});