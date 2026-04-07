(function () {
    var site = window.KinematicsSite;

    function getSessionId() {
        var segments = site.getPathSegments();
        var raw = segments.length ? segments[segments.length - 1] : '';
        var value = Number(raw);
        return Number.isFinite(value) && value > 0 ? value : null;
    }

    function render(profile, sessionState, sessionId) {
        var root = document.getElementById('page-root');
        var activeProgram = profile.active_program;

        window.KINEMATICS_WORKOUT_CONFIG = {
            session_id: sessionId,
            program_id: sessionState.program_id,
            status: sessionState.status || 'started',
            hints: [
                'Держите корпус собранным',
                'Сохраняйте плавный темп',
                'Дышите стабильно и не спешите',
                'Следите за амплитудой без рывков'
            ]
        };

        root.innerHTML = [
            '<section class="hero-card workout-hero">',
            '<div class="hero-card-copy">',
            '<span class="hero-kicker">Workout Flow</span>',
            '<h2 class="hero-title">Сессия #', sessionId, '</h2>',
            '<p class="hero-text">', activeProgram ? 'План «' + site.escapeHtml(activeProgram.title) + '» активен. Ниже — mock поток камеры и состояние сессии.' : 'Тренировочная сессия уже запущена. Ниже — mock поток камеры и состояние сессии.', '</p>',
            '</div>',
            '<div class="hero-stat-cluster">',
            '<article class="hero-stat-chip"><span>Статус</span><strong id="session-status-value">Идет</strong><small>синхронизировано</small></article>',
            '<article class="hero-stat-chip"><span>Таймер</span><strong id="timer-value">00:00</strong><small>внутри сессии</small></article>',
            '<article class="hero-stat-chip"><span>Повторы</span><strong id="reps-value">0</strong><small>mock count</small></article>',
            '</div>',
            '</section>',
            '<section class="workout-mobile-layout">',
            '<article class="glass-card workout-camera-card">',
            '<div class="card-head-row"><h3>Камера</h3><button id="camera-toggle-btn" class="secondary-pill-btn" type="button">Включить</button></div>',
            '<div id="webcam-feed" class="workout-feed-modern">',
            '<div class="workout-feed-placeholder">Поднимите камеру, чтобы увидеть mock-скелет и live-подсказки.</div>',
            '<svg id="skeleton-overlay" class="workout-skeleton" viewBox="0 0 100 100" aria-hidden="true">',
            '<line id="bone-a" x1="50" y1="18" x2="50" y2="42"></line><line id="bone-b" x1="50" y1="30" x2="30" y2="46"></line><line id="bone-c" x1="50" y1="30" x2="70" y2="46"></line><line id="bone-d" x1="50" y1="42" x2="38" y2="68"></line><line id="bone-e" x1="50" y1="42" x2="62" y2="68"></line>',
            '<circle id="kp-head" cx="50" cy="14" r="4"></circle><circle id="kp-neck" cx="50" cy="24" r="2"></circle><circle id="kp-l-shoulder" cx="30" cy="46" r="2"></circle><circle id="kp-r-shoulder" cx="70" cy="46" r="2"></circle><circle id="kp-hip" cx="50" cy="42" r="2"></circle><circle id="kp-l-knee" cx="38" cy="68" r="2"></circle><circle id="kp-r-knee" cx="62" cy="68" r="2"></circle>',
            '</svg>',
            '<span class="mock-float-chip">MOCK</span>',
            '</div>',
            '</article>',
            '<article class="glass-card workout-control-card">',
            '<div class="metric-grid-inline">',
            '<article><span>Score</span><strong id="score-value">--</strong></article>',
            '<article><span>Статус</span><strong id="workout-session-copy">', sessionId, '</strong></article>',
            '</div>',
            '<div class="workout-button-stack">',
            '<button id="pause-btn" class="primary-pill-btn" type="button">Пауза</button>',
            '<button id="rep-plus-btn" class="secondary-pill-btn" type="button">+1 повтор</button>',
            '<button id="rep-reset-btn" class="secondary-pill-btn" type="button">Сбросить</button>',
            '<button id="stop-btn" class="danger-pill-btn" type="button">Завершить</button>',
            '</div>',
            '<div class="glass-inner-panel"><h3>Подсказки</h3><ul id="hints-list" class="workout-hints-list"></ul></div>',
            '<p id="workout-status" class="inline-message"></p>',
            '</article>',
            '</section>',
            '<section class="glass-card">',
            '<div class="section-head"><div><span class="section-kicker">Логи</span><h3>История подходов</h3></div></div>',
            '<ul id="log-history-list" class="workout-log-list"></ul>',
            '</section>'
        ].join('');
    }

    document.addEventListener('DOMContentLoaded', function () {
        var root = document.getElementById('page-root');
        var sessionId = getSessionId();
        if (!sessionId) {
            site.renderState(root, 'Ошибка', 'Не удалось определить session id.', true);
            return;
        }

        site.renderState(root, 'Загрузка', 'Подготавливаю workout flow...', false);

        site.ensureOnboardingAccess()
            .then(function () {
                return Promise.all([
                    site.requireJson('/api/profile', null, 'Не удалось загрузить профиль.'),
                    site.requireJson('/api/workouts/' + sessionId, null, 'Не удалось загрузить сессию.')
                ]);
            })
            .then(function (results) {
                site.setUserShell(results[0]);
                render(results[0], results[1], sessionId);
            })
            .catch(function (error) {
                if (error && (error.code === 'AUTH_REQUIRED' || error.code === 'ONBOARDING_REQUIRED')) {
                    return;
                }
                site.renderState(root, 'Ошибка', error.message || 'Не удалось загрузить workout flow.', true);
            });
    });
})();
