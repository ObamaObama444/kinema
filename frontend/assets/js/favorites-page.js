(function () {
    var site = window.KinematicsSite;
    var state = {
        tab: 'programs',
        data: null
    };
    var ICONS = {
        arrow: '<svg viewBox="0 0 24 24" fill="none" aria-hidden="true"><path d="M9 5l7 7-7 7" stroke="currentColor" stroke-width="2.1" stroke-linecap="round" stroke-linejoin="round"></path></svg>'
    };

    function normalizeFavoritesData(data) {
        var source = site.ensureObject(data);
        return {
            programs: site.ensureArray(source.programs).map(function (item) {
                var program = site.ensureObject(item);
                return {
                    id: site.ensureFiniteNumber(program.id),
                    title: site.ensureString(program.title, 'Программа'),
                    description: site.ensureString(program.description, 'Описание появится позже.'),
                    level: site.ensureString(program.level, 'beginner'),
                    duration_weeks: site.ensureFiniteNumber(program.duration_weeks) || 0
                };
            }).filter(function (item) {
                return item.id != null;
            }),
            exercises: site.ensureArray(source.exercises).map(function (item) {
                var exercise = site.ensureObject(item);
                return {
                    id: site.ensureFiniteNumber(exercise.id),
                    title: site.ensureString(exercise.title, 'Упражнение'),
                    description: site.ensureString(exercise.description, 'Описание появится позже.'),
                    tags: site.ensureStringArray(exercise.tags)
                };
            }).filter(function (item) {
                return item.id != null;
            })
        };
    }

    function activeItems() {
        if (!state.data) {
            return [];
        }
        return state.tab === 'programs' ? state.data.programs : state.data.exercises;
    }

    function emptyText() {
        return state.tab === 'programs'
            ? 'Пока нет сохранённых тренировок.'
            : 'Пока нет сохранённых упражнений.';
    }

    function renderProgramRow(item) {
        return [
            '<article class="favorites-row">',
            '<a class="favorites-row-link" href="/app/programs/', item.id, '">',
            '<div class="favorites-row-copy">',
            '<h3>', site.escapeHtml(item.title), '</h3>',
            '<p>', site.escapeHtml(item.description), '</p>',
            '<div class="favorites-row-meta">',
            '<span>', site.escapeHtml(site.levelLabel(item.level)), '</span>',
            '<span>', item.duration_weeks, ' нед.</span>',
            '</div>',
            '</div>',
            '<span class="favorites-row-arrow">', ICONS.arrow, '</span>',
            '</a>',
            '</article>'
        ].join('');
    }

    function renderExerciseRow(item) {
        return [
            '<article class="favorites-row">',
            '<a class="favorites-row-link" href="/app/catalog">',
            '<div class="favorites-row-copy">',
            '<h3>', site.escapeHtml(item.title), '</h3>',
            '<p>', site.escapeHtml(item.description), '</p>',
            site.ensureStringArray(item.tags).length
                ? '<div class="favorites-row-tags">' + site.ensureStringArray(item.tags).slice(0, 3).map(function (tag) {
                    return '<span>' + site.escapeHtml(tag) + '</span>';
                }).join('') + '</div>'
                : '',
            '</div>',
            '<span class="favorites-row-arrow">', ICONS.arrow, '</span>',
            '</a>',
            '</article>'
        ].join('');
    }

    function renderRows() {
        var body = document.getElementById('favorites-body');
        var items = activeItems();

        if (!body) {
            return;
        }

        if (!items.length) {
            body.innerHTML = '<div class="favorites-empty">' + emptyText() + '</div>';
            return;
        }

        body.innerHTML = items.map(function (item) {
            return state.tab === 'programs' ? renderProgramRow(item) : renderExerciseRow(item);
        }).join('');
    }

    function render() {
        var root = document.getElementById('page-root');

        if (!root) {
            return;
        }

        root.innerHTML = [
            '<section class="favorites-page">',
            '<header class="favorites-page-head">',
            '<h1>Избранное</h1>',
            '<p>Тренировки и упражнения, которые вы сохранили.</p>',
            '</header>',
            '<div class="favorites-switcher" role="tablist" aria-label="Тип избранного">',
            '<button class="favorites-switch ', state.tab === 'programs' ? 'is-active' : '', '" type="button" data-favorites-tab="programs">Тренировки</button>',
            '<button class="favorites-switch ', state.tab === 'exercises' ? 'is-active' : '', '" type="button" data-favorites-tab="exercises">Упражнения</button>',
            '</div>',
            '<section id="favorites-body" class="favorites-list"></section>',
            '</section>'
        ].join('');

        Array.prototype.forEach.call(root.querySelectorAll('[data-favorites-tab]'), function (button) {
            button.addEventListener('click', function () {
                state.tab = button.getAttribute('data-favorites-tab') || 'programs';
                render();
            });
        });

        renderRows();
    }

    document.addEventListener('DOMContentLoaded', function () {
        var root = document.getElementById('page-root');

        if (!root) {
            return;
        }

        site.renderState(root, 'Загрузка', 'Открываю избранное...', false);
        site.ensureOnboardingAccess()
            .then(function () {
                return Promise.all([
                    site.requireJson('/api/profile', null, 'Не удалось загрузить профиль.'),
                    site.requireJson('/api/favorites', null, 'Не удалось загрузить избранное.')
                ]);
            })
            .then(function (results) {
                site.setUserShell(results[0]);
                state.data = normalizeFavoritesData(results[1]);
                render();
            })
            .catch(function (error) {
                if (error && (error.code === 'AUTH_REQUIRED' || error.code === 'ONBOARDING_REQUIRED')) {
                    return;
                }
                site.renderState(root, 'Ошибка', error.message || 'Не удалось загрузить избранное.', true);
            });
    });
})();
