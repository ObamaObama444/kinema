(function () {
    var site = window.KinematicsSite;
    var TECHNIQUE_GUIDES = {
        squat: {
            stance: 'Встаньте боком к камере, стопы полностью в кадре.',
            camera: 'Телефон на уровне таза или груди, в кадре голова, таз, колени и стопы.',
            steps: ['Опускайтесь тазом назад и вниз.', 'Колени идут по линии стоп.', 'Вставайте без рывка и не отрывайте пятки.'],
            mistakes: ['Пятки отрываются', 'Корпус заваливается', 'Слишком короткая амплитуда'],
            pose: 'standing'
        },
        pushup: {
            stance: 'Примите упор лёжа боком к камере.',
            camera: 'Телефон сбоку на уровне корпуса, в кадре плечи, таз, колени и стопы.',
            steps: ['Держите тело одной линией.', 'Опускайтесь за счёт локтей.', 'Поднимайтесь плавно без провала таза.'],
            mistakes: ['Таз провисает', 'Локти почти не сгибаются', 'Ноги сильно согнуты'],
            pose: 'prone'
        },
        lunge: {
            stance: 'Встаньте боком к камере, рабочая нога ближе к центру кадра.',
            camera: 'Телефон на уровне таза, в кадре корпус, таз, оба колена и стопы.',
            steps: ['Сделайте шаг назад.', 'Опуститесь вертикально вниз.', 'Вернитесь в стойку без перекоса таза.'],
            mistakes: ['Колено уходит внутрь', 'Корпус заваливается', 'Шаг слишком короткий'],
            pose: 'standing'
        },
        glute_bridge: {
            stance: 'Лягте на спину боком к камере, колени согнуты.',
            camera: 'Телефон низко сбоку, в кадре плечи, таз, колени и стопы.',
            steps: ['Поднимайте таз вверх.', 'Фиксируйте верхнюю точку.', 'Опускайтесь плавно на коврик.'],
            mistakes: ['Таз поднимается низко', 'Есть перекос в стороны', 'Движение рывком'],
            pose: 'supine'
        },
        leg_raise: {
            stance: 'Лягте на спину боком к камере, ноги прямые или слегка согнуты.',
            camera: 'Телефон низко сбоку, в кадре плечи, таз, колени и стопы.',
            steps: ['Поднимайте ноги без рывка.', 'Не раскачивайте корпус.', 'Опускайте ноги под контролем.'],
            mistakes: ['Рывок ногами', 'Поясница резко прогибается', 'Ноги уходят из кадра'],
            pose: 'supine'
        },
        crunch: {
            stance: 'Лягте на спину боком к камере, колени согнуты.',
            camera: 'Телефон низко сбоку, в кадре плечи, таз и колени.',
            steps: ['Поднимайте плечи короткой амплитудой.', 'Не тяните шею руками.', 'Возвращайтесь вниз плавно.'],
            mistakes: ['Рывок шеей', 'Слишком высокая амплитуда', 'Корпус уходит из кадра'],
            pose: 'supine'
        }
    };

    function renderGuideDiagram(pose) {
        var body;

        if (pose === 'prone') {
            body = [
                '<line x1="48" y1="76" x2="86" y2="66" />',
                '<line x1="86" y1="66" x2="134" y2="68" />',
                '<line x1="134" y1="68" x2="174" y2="82" />',
                '<line x1="74" y1="70" x2="64" y2="98" />',
                '<line x1="158" y1="76" x2="188" y2="96" />'
            ].join('');
        } else if (pose === 'supine') {
            body = [
                '<line x1="50" y1="88" x2="92" y2="88" />',
                '<line x1="92" y1="88" x2="132" y2="78" />',
                '<line x1="132" y1="78" x2="176" y2="88" />',
                '<line x1="92" y1="88" x2="124" y2="48" />',
                '<line x1="124" y1="48" x2="164" y2="38" />'
            ].join('');
        } else {
            body = [
                '<line x1="92" y1="38" x2="96" y2="78" />',
                '<line x1="96" y1="78" x2="74" y2="118" />',
                '<line x1="96" y1="78" x2="132" y2="112" />',
                '<line x1="74" y1="118" x2="48" y2="124" />',
                '<line x1="132" y1="112" x2="162" y2="124" />'
            ].join('');
        }

        return [
            '<svg class="tech-guide-diagram" viewBox="0 0 220 140" role="img" aria-label="Схема бокового ракурса">',
            '<rect x="12" y="42" width="24" height="54" rx="5" class="tech-guide-camera" />',
            '<path d="M40 68 C68 46 112 36 190 52" class="tech-guide-ray" />',
            '<line x1="34" y1="124" x2="194" y2="124" class="tech-guide-floor" />',
            '<g class="tech-guide-person">',
            '<circle cx="88" cy="28" r="10" />',
            body,
            '</g>',
            '</svg>'
        ].join('');
    }

    function renderGuideList(items) {
        return (items || []).map(function (item) {
            return '<li>' + site.escapeHtml(item) + '</li>';
        }).join('');
    }

    function renderTechniqueGuide(exercise) {
        var slug = site.ensureString(exercise.slug, 'squat');
        var guide = TECHNIQUE_GUIDES[slug] || TECHNIQUE_GUIDES.squat;

        return [
            '<section id="tech-guide-section" class="technique-guide-card">',
            '<div class="tech-guide-copy">',
            '<span class="tech-guide-kicker">Инструкция</span>',
            '<h2>Встаньте к камере</h2>',
            '<p>', site.escapeHtml(guide.stance), '</p>',
            '<p>', site.escapeHtml(guide.camera), '</p>',
            '<div class="tech-guide-columns">',
            '<div><strong>Движение</strong><ul>', renderGuideList(guide.steps), '</ul></div>',
            '<div><strong>Не допускайте</strong><ul>', renderGuideList(guide.mistakes), '</ul></div>',
            '</div>',
            '<button id="tech-guide-ready-btn" class="primary-btn" type="button">Понятно, включить камеру</button>',
            '</div>',
            renderGuideDiagram(guide.pose),
            '</section>'
        ].join('');
    }

    function renderScreen(session) {
        var exercise = site.ensureObject(session.exercise);

        return [
            '<section class="technique-compact-page">',
            '<header class="technique-compact-head">',
            '<a id="tech-back-link" class="technique-back-link" href="/app/catalog">Назад</a>',
            '<h1 id="tech-exercise-name">', site.escapeHtml(site.ensureString(exercise.title, 'Упражнение')), '</h1>',
            '</header>',
            renderTechniqueGuide(exercise),
            '<section id="tech-stage-shell" class="technique-stage-shell" hidden>',
            '<div class="technique-camera-stage">',
            '<video id="tech-video" class="tech-video" playsinline muted autoplay></video>',
            '<canvas id="tech-overlay" class="tech-overlay"></canvas>',
            '<span id="tech-camera-badge" class="tech-camera-badge is-loading">Подключаю камеру...</span>',
            '</div>',
            '</section>',
            '<section id="tech-inline-status" class="technique-inline-status" hidden>',
            '<span class="tech-inline-metric"><strong id="tech-rep-counter">0</strong><small>повторы</small></span>',
            '<span class="tech-inline-metric"><strong id="tech-last-score">-</strong><small>score</small></span>',
            '<span class="tech-inline-metric"><strong id="tech-timer">00:00</strong><small>время</small></span>',
            '<span id="tech-quality-pill" class="status-pill">Ожидание</span>',
            '</section>',
            '<p id="tech-live-hint" class="tech-live-hint is-low" hidden>Развернитесь боком к камере и нажмите «Начать».</p>',
            '<section id="tech-controls-inline" class="technique-controls-inline" hidden>',
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
