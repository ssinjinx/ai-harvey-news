let currentAudio = null;
let currentArticleId = null;

function updatePlayButtons(isPlaying) {
    const featuredBtn = currentArticleId ? document.getElementById('featured-audio-btn-' + currentArticleId) : null;
    const harveyBtn = document.getElementById('harvey-play-btn');
    if (featuredBtn) {
        featuredBtn.innerHTML = isPlaying
            ? '<span class="material-symbols-outlined" data-icon="pause">pause</span> Pause'
            : '<span class="material-symbols-outlined" data-icon="volume_up">volume_up</span> Listen';
    }
    if (harveyBtn) {
        harveyBtn.innerHTML = isPlaying
            ? '<span class="material-symbols-outlined text-4xl" data-icon="pause" style="font-variation-settings: \'FILL\' 1;">pause</span>'
            : '<span class="material-symbols-outlined text-4xl" data-icon="play_arrow">play_arrow</span>';
    }
}

function playFeaturedAudio(articleId) {
    console.log('playFeaturedAudio called:', articleId);

    // If clicking the same article, toggle play/pause
    if (currentAudio && currentArticleId === articleId) {
        if (currentAudio.paused) {
            currentAudio.play();
            updatePlayButtons(true);
        } else {
            currentAudio.pause();
            updatePlayButtons(false);
        }
        return;
    }

    // If a different article is playing, stop it first
    if (currentAudio) {
        currentAudio.pause();
        currentAudio = null;
        if (currentArticleId) updatePlayButtons(false);
    }

    currentArticleId = articleId;
    const featuredStatus = document.getElementById('featured-audio-status-' + articleId);
    const harveyStatus = document.getElementById('harvey-audio-status');

    if (harveyStatus) harveyStatus.textContent = 'Loading...';

    // Check if audio exists
    fetch('/article/' + articleId + '/audio/status')
        .then(r => {
            console.log('Status response:', r.status);
            return r.json();
        })
        .then(data => {
            console.log('Status data:', data);
            if (data.available) {
                // Audio exists, play it
                console.log('Playing audio from /article/' + articleId + '/audio');
                currentAudio = new Audio('/article/' + articleId + '/audio');
                currentAudio.play()
                    .then(() => {
                        console.log('Audio started playing');
                        updatePlayButtons(true);
                        if (harveyStatus) harveyStatus.textContent = 'Playing...';
                    })
                    .catch(err => {
                        console.error('Audio play error:', err);
                        if (harveyStatus) harveyStatus.textContent = 'Play error';
                    });
                if (featuredStatus) featuredStatus.classList.add('hidden');

                currentAudio.onended = function() {
                    updatePlayButtons(false);
                    if (harveyStatus) harveyStatus.textContent = '';
                    currentAudio = null;
                    currentArticleId = null;
                };
            } else if (data.tts_available) {
                // Generate audio
                if (featuredStatus) {
                    featuredStatus.classList.remove('hidden');
                    featuredStatus.textContent = 'Generating audio...';
                }
                if (harveyStatus) harveyStatus.textContent = 'Generating...';
                fetch('/article/' + articleId + '/audio')
                    .then(r => {
                        if (r.ok) return r.blob();
                        throw new Error('Failed');
                    })
                    .then(blob => {
                        currentAudio = new Audio(URL.createObjectURL(blob));
                        currentAudio.play();
                        updatePlayButtons(true);
                        if (featuredStatus) featuredStatus.classList.add('hidden');
                        if (harveyStatus) harveyStatus.textContent = 'Playing...';

                        currentAudio.onended = function() {
                            updatePlayButtons(false);
                            if (harveyStatus) harveyStatus.textContent = '';
                            currentAudio = null;
                            currentArticleId = null;
                        };
                    })
                    .catch(err => {
                        if (featuredStatus) {
                            featuredStatus.textContent = 'Error generating audio';
                        }
                        if (harveyStatus) harveyStatus.textContent = 'Error';
                        updatePlayButtons(false);
                    });
            } else {
                if (featuredStatus) {
                    featuredStatus.classList.remove('hidden');
                    featuredStatus.textContent = 'Audio not available';
                }
                if (harveyStatus) harveyStatus.textContent = 'Not available';
            }
        })
        .catch(err => {
            console.error('Fetch error:', err);
            if (harveyStatus) harveyStatus.textContent = 'Error: ' + err.message;
        });
}
