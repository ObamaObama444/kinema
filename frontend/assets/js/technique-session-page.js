(function () {
    var site = window.KinematicsSite;

    function renderScreen(session) {
        var exercise = site.ensureObject(session.exercise);

        return [
            '<section class="technique-compact-page">',
            '<header class="technique-compact-head">',
            '<a id="tech-back-link" class="technique-back-link" href="/app/catalog">Назад</a>',
            '<h1 id="tech-exercise-name">', site.escapeHtml(site.ensureString(exercise.title, 'Упражнение')), '</h1>',
            '</header>',
            '<section class="technique-stage-shell">',
            '<div class="technique-camera-stage">',
            '<video id="tech-video" class="tech-video" playsinline muted autoplay></video>',
            '<canvas id="tech-overlay" class="tech-overlay"></canvas>',
            '<span id="tech-camera-badge" class="tech-camera-badge is-loading">Подключаю камеру...</span>',
            '</div>',
            '</section>',
            '<section class="technique-inline-status">',
            '<span class="tech-inline-metric"><strong id="tech-rep-counter">0</strong><small>повторы</small></span>',
            '<span class="tech-inline-metric"><strong id="tech-last-score">-</strong><small>score</small></span>',
            '<span class="tech-inline-metric"><strong id="tech-timer">00:00</strong><small>время</small></span>',
            '<span id="tech-quality-pill" class="status-pill">Ожидание</span>',
            '</section>',
            '<p id="tech-live-hint" class="tech-live-hint is-low">Развернитесь боком к камере и нажмите «Начать».</p>',
            '<section class="technique-controls-inline">',
            '<button id="tech-start-btn" class="primary-btn" type="button">Начать</button>',
            '<button id="tech-voice-btn" class="secondary-btn" type="button" aria-pressed="true">Голос: вкл</button>',
            '<button id="tech-stop-btn" class="secondary-btn" type="button">Стоп</button>',
            '</section>',
            '<section id="tech-summary-section" class="technique-result-sheet" hidden>',
            '<div id="tech-summary"></div>',
            '</section>',
            '</section>'
        ].join('');
    }

    function mountTechniquePage() {
        var root = document.getElementById('page-root');
        var segments = site.getPathSegments();
        var sessionId = Number(segments[segments.length - 1]);

        if (!root) {
            return;
        }
        if (!Number.isFinite(sessionId) || sessionId <= 0) {
            site.renderState(root, 'Ошибка', 'Не удалось определить technique-сессию.', true);
            return;
        }

        root.innerHTML = [
            '<section class="technique-compact-page">',
            '<header class="technique-compact-head">',
            '<a class="technique-back-link" href="/app/catalog">Назад</a>',
            '<h1>Упражнение</h1>',
            '</header>',
            '<p class="tech-live-hint is-low">Открываю камеру и технику...</p>',
            '</section>'
        ].join('');
        site.ensureOnboardingAccess()
            .then(function () {
                return Promise.all([
                    site.requireJson('/api/profile', null, 'Не удалось загрузить профиль.'),
                    site.requireJson('/api/technique/sessions/' + sessionId, null, 'Не удалось загрузить technique-сессию.')
                ]);
            })
            .then(function (results) {
                var profile = results[0];
                var session = results[1];
                var exercise = site.ensureObject(session.exercise);

                site.setUserShell(profile);
                root.innerHTML = renderScreen(session);

                if (!window.KinematicsTechniqueRuntime || typeof window.KinematicsTechniqueRuntime.mount !== 'function') {
                    throw new Error('Technique runtime не загрузился.');
                }

                window.KinematicsTechniqueRuntime.mount({
                    sessionId: sessionId,
                    exerciseSlug: site.ensureString(exercise.slug, 'squat'),
                    exerciseTitle: site.ensureString(exercise.title, 'Упражнение'),
                    motionFamily: site.ensureString(exercise.motion_family, 'squat_like'),
                    viewType: site.ensureString(exercise.view_type, 'side'),
                    profileId: site.ensureFiniteNumber(exercise.profile_id),
                    referenceBased: exercise.reference_based === true
                });
            })
            .catch(function (error) {
                if (error && (error.code === 'AUTH_REQUIRED' || error.code === 'ONBOARDING_REQUIRED')) {
                    return;
                }
                site.renderState(root, 'Ошибка', error.message || 'Не удалось открыть проверку техники.', true);
            });
    }

    document.addEventListener('DOMContentLoaded', mountTechniquePage);
})();
