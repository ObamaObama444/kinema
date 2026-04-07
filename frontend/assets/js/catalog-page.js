(function () {
    var site = window.KinematicsSite;
    var PUSHUP_UNLOCK_STORAGE_KEY = 'kinematics-catalog-pushup-unlocked-v4';
    var CATALOG_NOTICE_STORAGE_KEY = 'kinematics-catalog-notice';
    var activeRouteToken = 0;
    var FALLBACK_ITEMS = [
        {
            id: 1,
            slug: 'squat',
            title: 'Приседания',
            description: 'Базовое упражнение на ноги и корпус для развития силы и выносливости.',
            tags: ['Без инвентаря', 'Новичкам', 'Ноги / Ягодицы'],
            technique_available: true,
            is_favorite: false
        },
        {
            id: null,
            slug: 'pushup',
            title: 'Отжимания',
            description: 'Классическое упражнение для груди, плеч и стабилизаторов корпуса.',
            tags: ['Без инвентаря', 'Новичкам', 'Грудь / Трицепс'],
            technique_available: true,
            is_favorite: false
        },
        {
            id: 3,
            slug: 'plank',
            title: 'Планка',
            description: 'Статическое упражнение для стабилизации корпуса и поясницы.',
            tags: ['Без инвентаря', 'Кора', 'Лёгкий уровень'],
            technique_available: false,
            is_favorite: false
        },
        {
            id: 4,
            slug: 'lunge',
            title: 'Выпады',
            description: 'Развивает силу ног и баланс, хорошо дополняет приседания.',
            tags: ['Без инвентаря', 'Ноги / Ягодицы', 'Средний уровень'],
            technique_available: false,
            is_favorite: false
        },
        {
            id: 5,
            slug: 'burpee',
            title: 'Берпи',
            description: 'Интенсивное кардио-упражнение для выносливости всего тела.',
            tags: ['Кардио', 'Все тело', 'Продвинутый уровень'],
            technique_available: false,
            is_favorite: false
        },
        {
            id: 6,
            slug: 'band_row',
            title: 'Тяга резинки к поясу',
            description: 'Упражнение на спину и осанку с фитнес-резинкой.',
            tags: ['Резинка', 'Спина', 'Средний уровень'],
            technique_available: false,
            is_favorite: false
        },
        {
            id: 7,
            slug: 'glute_bridge',
            title: 'Ягодичный мост',
            description: 'Акцентированно включает ягодицы и заднюю поверхность бедра.',
            tags: ['Без инвентаря', 'Ягодицы', 'Лёгкий уровень'],
            technique_available: false,
            is_favorite: false
        },
        {
            id: 8,
            slug: 'crunch',
            title: 'Скручивания',
            description: 'Базовое упражнение на мышцы пресса и контроль корпуса.',
            tags: ['Без инвентаря', 'Пресс', 'Лёгкий уровень'],
            technique_available: false,
            is_favorite: false
        },
        {
            id: 9,
            slug: 'calf_raise',
            title: 'Подъемы на носки',
            description: 'Укрепляет икроножные мышцы и устойчивость голеностопа.',
            tags: ['Без инвентаря', 'Икры', 'Лёгкий уровень'],
            technique_available: false,
            is_favorite: false
        },
        {
            id: 10,
            slug: 'superman',
            title: 'Супермен',
            description: 'Укрепляет разгибатели спины и заднюю цепь мышц.',
            tags: ['Без инвентаря', 'Спина', 'Лёгкий уровень'],
            technique_available: false,
            is_favorite: false
        }
    ];
    var state = {
        profile: null,
        items: [],
        notice: ''
    };

    function isPushupUnlocked() {
        return site.safeGetStorage(PUSHUP_UNLOCK_STORAGE_KEY) === '1';
    }

    function consumeCatalogNotice() {
        var value = site.safeGetSessionStorage(CATALOG_NOTICE_STORAGE_KEY) || '';
        if (value) {
            site.safeRemoveSessionStorage(CATALOG_NOTICE_STORAGE_KEY);
        }
        return String(value || '');
    }

    function currentRouteToken() {
        return window.KinematicsShell ? Number(window.KinematicsShell.routeToken || 0) : 0;
    }

    function isActiveRoute(routeToken) {
        return activeRouteToken === routeToken && currentRouteToken() === routeToken;
    }

    function normalizeCatalogItem(item) {
        var source = site.ensureObject(item);
        return {
            id: site.ensureFiniteNumber(source.id),
            slug: site.ensureString(source.slug, ''),
            title: site.ensureString(source.title, 'Упражнение'),
            description: site.ensureString(source.description, 'Описание появится позже.'),
            tags: site.ensureStringArray(source.tags),
            technique_available: source.technique_available === true,
            technique_launch_url: site.ensureString(source.technique_launch_url, ''),
            is_favorite: source.is_favorite === true,
            favorite_busy: false,
            session_busy: false
        };
    }

    function buildFallbackItems() {
        return FALLBACK_ITEMS
            .filter(function (item) {
                return item.slug !== 'pushup' || isPushupUnlocked();
            })
            .map(normalizeCatalogItem);
    }

    function resolveCatalogItems(rawItems) {
        var candidates = site.ensureArray(rawItems);
        var source = site.ensureObject(rawItems);
        var fallbackItems = buildFallbackItems();
        var mergedBySlug = {};

        if (!candidates.length) {
            candidates = site.ensureArray(source.items);
        }

        fallbackItems.forEach(function (item) {
            mergedBySlug[item.slug] = item;
        });

        candidates.map(normalizeCatalogItem).forEach(function (item) {
            var base = mergedBySlug[item.slug] || null;

            if (base) {
                mergedBySlug[item.slug] = Object.assign({}, base, item, {
                    tags: item.tags.length ? item.tags : base.tags,
                    title: item.title || base.title,
                    description: item.description || base.description,
                    technique_available: item.technique_available === true || base.technique_available === true
                });
                return;
            }

            if (item.slug) {
                mergedBySlug[item.slug] = item;
            }
        });

        return Object.keys(mergedBySlug).map(function (slug) {
            return mergedBySlug[slug];
        });
    }

    function exerciseBySlug(slug) {
        return state.items.find(function (item) {
            return item.slug === slug;
        }) || null;
    }

    function exerciseById(id) {
        return state.items.find(function (item) {
            return item.id === id;
        }) || null;
    }

    function renderFavoriteButton(exercise) {
        if (exercise.id == null) {
            return '';
        }

        return [
            '<button class="favorite-toggle ', exercise.is_favorite ? 'is-active' : '', '" type="button" data-exercise-favorite="', exercise.id, '" aria-label="Избранное" ', exercise.favorite_busy ? 'disabled' : '', '>',
            exercise.favorite_busy ? '…' : '❤',
            '</button>'
        ].join('');
    }

    function renderTryButton(exercise) {
        var canLaunchTechnique = exercise.technique_available;

        return [
            '<button class="primary-btn exercise-try-btn" type="button" ',
            canLaunchTechnique ? 'data-exercise-try="' + site.escapeHtml(exercise.slug) + '" ' : '',
            canLaunchTechnique && exercise.session_busy ? 'disabled ' : '',
            'aria-label="Попробовать ', site.escapeHtml(exercise.title), '">',
            canLaunchTechnique && exercise.session_busy ? 'Открываю...' : 'Попробовать',
            '</button>'
        ].join('');
    }

    function renderExerciseCard(exercise) {
        return [
            '<article class="exercise-row" data-exercise-slug="', site.escapeHtml(exercise.slug), '">',
            '<div class="exercise-row-main">',
            '<h3>', site.escapeHtml(exercise.title), '</h3>',
            '</div>',
            '<div class="exercise-row-actions">',
            renderFavoriteButton(exercise),
            renderTryButton(exercise),
            '</div>',
            '</article>'
        ].join('');
    }

    function render() {
        var root = document.getElementById('page-root');
        var items = state.items.length ? state.items : buildFallbackItems();

        if (!root) {
            return;
        }

        root.innerHTML = [
            '<section class="exercise-stream-page">',
            state.notice ? '<p class="inline-message exercise-catalog-notice" aria-live="polite">' + site.escapeHtml(state.notice) + '</p>' : '',
            '<section class="exercise-row-list">' + items.map(renderExerciseCard).join('') + '</section>',
            '<div class="exercise-cta-stack">',
            '<button class="exercise-plan-cta" type="button" data-edit-plan>редактировать текущий план</button>',
            '<button class="exercise-add-cta" type="button" data-create-exercise>добавить упражнение</button>',
            '</div>',
            '</section>'
        ].join('');

        bindActions();
    }

    function setItemState(slug, patch) {
        var exercise = exerciseBySlug(slug);
        if (!exercise) {
            return;
        }
        Object.keys(patch || {}).forEach(function (key) {
            exercise[key] = patch[key];
        });
    }

    function handleFavoriteToggle(exerciseId) {
        var exercise = exerciseById(exerciseId);
        var method;

        if (!exercise || exercise.id == null || exercise.favorite_busy) {
            return;
        }

        exercise.favorite_busy = true;
        render();

        method = exercise.is_favorite ? 'DELETE' : 'POST';
        site.requireJson(
            '/api/favorites/exercises/' + exercise.id,
            { method: method },
            'Не удалось обновить избранное.'
        )
            .then(function () {
                exercise.is_favorite = !exercise.is_favorite;
                exercise.favorite_busy = false;
                render();
            })
            .catch(function (error) {
                exercise.favorite_busy = false;
                state.notice = error.message || '';
                render();
            });
    }

    function handleTry(exerciseSlug) {
        var exercise = exerciseBySlug(exerciseSlug);

        if (!exercise || !exercise.technique_available || exercise.session_busy) {
            return;
        }

        if (exercise.technique_launch_url) {
            window.location.assign(exercise.technique_launch_url);
            return;
        }

        setItemState(exercise.slug, { session_busy: true });
        render();

        site.sendJson(
            '/api/technique/sessions/start',
            'POST',
            { exercise_slug: exercise.slug },
            'Не удалось открыть сессию проверки техники.'
        )
            .then(function (response) {
                window.location.assign(site.ensureString(response.redirect_url, '/app/catalog'));
            })
            .catch(function (error) {
                setItemState(exercise.slug, { session_busy: false });
                state.notice = error.message || '';
                render();
            });
    }

    function bindActions() {
        document.querySelectorAll('[data-edit-plan]').forEach(function (button) {
            button.addEventListener('click', function () {
                window.location.assign('/app/programs');
            });
        });

        document.querySelectorAll('[data-create-exercise]').forEach(function (button) {
            button.addEventListener('click', function () {
                window.location.assign('/app/catalog/new');
            });
        });

        document.querySelectorAll('[data-exercise-favorite]').forEach(function (button) {
            button.addEventListener('click', function () {
                handleFavoriteToggle(Number(button.getAttribute('data-exercise-favorite')));
            });
        });

        document.querySelectorAll('[data-exercise-try]').forEach(function (button) {
            button.addEventListener('click', function () {
                handleTry(button.getAttribute('data-exercise-try') || '');
            });
        });
    }

    function mountCatalogPage() {
        var routeToken = currentRouteToken();
        var root = document.getElementById('page-root');

        if (!root) {
            return;
        }

        activeRouteToken = routeToken;
        state.items = buildFallbackItems();
        state.notice = consumeCatalogNotice();
        render();

        site.ensureOnboardingAccess()
            .then(function () {
                return site.requireJson('/api/profile', null, 'Не удалось загрузить профиль.');
            })
            .then(function (profile) {
                return site.requireJson('/api/exercises/catalog', null, 'Не удалось загрузить упражнения.')
                    .catch(function () {
                        return buildFallbackItems();
                    })
                    .then(function (items) {
                        return [profile, items];
                    });
            })
            .then(function (results) {
                if (!isActiveRoute(routeToken)) {
                    return;
                }

                state.profile = results[0];
                state.items = resolveCatalogItems(results[1]);
                site.setUserShell(state.profile);
                render();
            })
            .catch(function (error) {
                if (!isActiveRoute(routeToken)) {
                    return;
                }
                if (error && (error.code === 'AUTH_REQUIRED' || error.code === 'ONBOARDING_REQUIRED')) {
                    return;
                }
                render();
            });
    }

    window.KinematicsPages = window.KinematicsPages || {};
    window.KinematicsPages.workouts = mountCatalogPage;

    document.addEventListener('DOMContentLoaded', mountCatalogPage);
})();
