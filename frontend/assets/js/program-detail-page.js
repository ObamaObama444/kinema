(function () {
    var site = window.KinematicsSite;

    function normalizeProgram(program) {
        var source = site.ensureObject(program);
        return {
            id: site.ensureFiniteNumber(source.id),
            title: site.ensureString(source.title, 'Программа'),
            description: site.ensureString(source.description, 'Описание появится позже.'),
            level: site.ensureString(source.level, 'beginner'),
            duration_weeks: site.ensureFiniteNumber(source.duration_weeks) || 0,
            is_favorite: source.is_favorite === true,
            exercises: site.ensureArray(source.exercises).map(function (item) {
                var exercise = site.ensureObject(item);
                return {
                    id: site.ensureFiniteNumber(exercise.id),
                    order: site.ensureFiniteNumber(exercise.order) || 0,
                    sets: site.ensureFiniteNumber(exercise.sets) || 0,
                    reps: site.ensureFiniteNumber(exercise.reps) || 0,
                    rest_sec: site.ensureFiniteNumber(exercise.rest_sec) || 0,
                    tempo: site.ensureString(exercise.tempo, '—'),
                    exercise_name: site.ensureString(exercise.exercise_name, 'Упражнение'),
                    exercise_description: site.ensureString(exercise.exercise_description, 'Описание появится позже.')
                };
            })
        };
    }

    function getProgramId() {
        var segments = site.getPathSegments();
        var raw = segments.length ? segments[segments.length - 1] : '';
        var value = Number(raw);
        return Number.isFinite(value) && value > 0 ? value : null;
    }

    function render(program, profile) {
        var root = document.getElementById('page-root');
        var normalizedProgram = normalizeProgram(program);
        var activeProgram = profile.active_program;
        var defaultFrequency = activeProgram && activeProgram.program_id === normalizedProgram.id ? activeProgram.workouts_per_week : 3;

        root.innerHTML = [
            '<section class="hero-card">',
            '<div class="hero-card-copy">',
            '<div class="card-head-row"><span class="hero-kicker">Детали плана</span><button id="program-favorite-toggle" class="favorite-toggle ', normalizedProgram.is_favorite ? 'is-active' : '', '" type="button" aria-label="Избранное">❤</button></div>',
            '<h2 class="hero-title">', site.escapeHtml(normalizedProgram.title), '</h2>',
            '<p class="hero-text">', site.escapeHtml(normalizedProgram.description), '</p>',
            '<div class="program-meta-row"><span class="meta-pill">', site.escapeHtml(site.levelLabel(normalizedProgram.level)), '</span><span class="meta-pill">', normalizedProgram.duration_weeks, ' нед.</span>', activeProgram && activeProgram.program_id === normalizedProgram.id ? '<span class="meta-pill is-accent">Активный план</span>' : '', '</div>',
            '</div>',
            '<div class="hero-card-side">',
            '<div class="segmented-pills" id="detail-frequency-control">',
            [1, 2, 3].map(function (value) {
                return '<button class="segmented-pill ' + (defaultFrequency === value ? 'is-active' : '') + '" type="button" data-frequency="' + value + '">' + value + 'x</button>';
            }).join(''),
            '</div>',
            '<button id="activate-program-btn" class="primary-pill-btn" type="button">Сделать активной</button>',
            '<button id="start-program-workout-btn" class="secondary-pill-btn" type="button">Начать тренировку</button>',
            '</div>',
            '</section>',
            '<p id="program-detail-feedback" class="inline-message" aria-live="polite"></p>',
            '<section class="stack-grid">',
            normalizedProgram.exercises.length === 0
                ? '<article class="glass-card empty-card">Для этой программы пока нет упражнений.</article>'
                : normalizedProgram.exercises.map(function (item) {
                return [
                    '<article class="glass-card exercise-line-card">',
                    '<div class="card-head-row"><h3>', item.order, '. ', site.escapeHtml(item.exercise_name), '</h3><span class="meta-pill">', site.escapeHtml(item.tempo), '</span></div>',
                    '<p class="muted-text">', site.escapeHtml(item.exercise_description), '</p>',
                    '<div class="metric-grid-inline">',
                    '<article><span>Подходы</span><strong>', item.sets, '</strong></article>',
                    '<article><span>Повторы</span><strong>', item.reps, '</strong></article>',
                    '<article><span>Отдых</span><strong>', item.rest_sec, 'с</strong></article>',
                    '</div>',
                    '</article>'
                ].join('');
            }).join(''),
            '</section>',
            '<div class="bottom-link-row"><a class="text-link-btn" href="/app/programs">← Назад к планам</a></div>'
        ].join('');

        var feedback = document.getElementById('program-detail-feedback');
        var selectedFrequency = defaultFrequency;

        document.querySelectorAll('#detail-frequency-control [data-frequency]').forEach(function (button) {
            button.addEventListener('click', function () {
                selectedFrequency = Number(button.getAttribute('data-frequency'));
                document.querySelectorAll('#detail-frequency-control .segmented-pill').forEach(function (pill) {
                    pill.classList.remove('is-active');
                });
                button.classList.add('is-active');
            });
        });

        document.getElementById('activate-program-btn').addEventListener('click', function (event) {
            var button = event.currentTarget;
            button.disabled = true;
            feedback.textContent = 'Сохраняю активный план...';
            feedback.classList.remove('is-error');
            site.sendJson('/api/programs/select', 'POST', {
                program_id: normalizedProgram.id,
                workouts_per_week: selectedFrequency
            }, 'Не удалось выбрать программу.')
                .then(function () {
                    window.location.reload();
                })
                .catch(function (error) {
                    if (error && error.code === 'AUTH_REQUIRED') {
                        return;
                    }
                    feedback.textContent = error.message || 'Не удалось выбрать программу.';
                    feedback.classList.add('is-error');
                    button.disabled = false;
                });
        });

        document.getElementById('start-program-workout-btn').addEventListener('click', function (event) {
            var button = event.currentTarget;
            button.disabled = true;
            feedback.textContent = 'Запускаю тренировку...';
            feedback.classList.remove('is-error');
            site.sendJson('/api/workouts/start', 'POST', { program_id: normalizedProgram.id }, 'Не удалось запустить тренировку.')
                .then(function (data) {
                    window.location.assign('/app/workout/' + data.session_id);
                })
                .catch(function (error) {
                    if (error && error.code === 'AUTH_REQUIRED') {
                        return;
                    }
                    feedback.textContent = error.message || 'Не удалось запустить тренировку.';
                    feedback.classList.add('is-error');
                    button.disabled = false;
                });
        });

        document.getElementById('program-favorite-toggle').addEventListener('click', function (event) {
            var button = event.currentTarget;
            var method = button.classList.contains('is-active') ? 'DELETE' : 'POST';
            button.disabled = true;
            site.fetchJson('/api/favorites/programs/' + normalizedProgram.id, { method: method })
                .then(function (result) {
                    button.disabled = false;
                    if (!result.response.ok) {
                        throw new Error(site.parseApiError(result.data, 'Не удалось обновить избранное.'));
                    }
                    button.classList.toggle('is-active');
                })
                .catch(function (error) {
                    button.disabled = false;
                    feedback.textContent = error.message || 'Не удалось обновить избранное.';
                    feedback.classList.add('is-error');
                });
        });
    }

    document.addEventListener('DOMContentLoaded', function () {
        var root = document.getElementById('page-root');
        var programId = getProgramId();
        if (!programId) {
            site.renderState(root, 'Ошибка', 'Не удалось определить plan id.', true);
            return;
        }

        site.renderState(root, 'Загрузка', 'Открываю детали плана...', false);
        site.ensureOnboardingAccess()
            .then(function () {
                return Promise.all([
                    site.requireJson('/api/profile', null, 'Не удалось загрузить профиль.'),
                    site.requireJson('/api/programs/' + programId, null, 'Не удалось загрузить программу.')
                ]);
            })
            .then(function (results) {
                site.setUserShell(results[0]);
                render(results[1], results[0]);
            })
            .catch(function (error) {
                if (error && (error.code === 'AUTH_REQUIRED' || error.code === 'ONBOARDING_REQUIRED')) {
                    return;
                }
                site.renderState(root, 'Ошибка', error.message || 'Не удалось загрузить детали плана.', true);
            });
    });
})();
