(function () {
    var site = window.KinematicsSite;
    var activeRouteToken = 0;
    var currentPlanCacheKey = '';
    var pendingRetryTimer = 0;
    var currentRenderedPlan = null;
    var currentRenderFeedback = '';
    var currentSelectedDayNumber = null;
    var isDayModalOpen = false;
    var PLAN_HANDOFF_STORAGE_KEY = 'kinematics-personal-plan-handoff-v4';
    var PLAN_CACHE_KEY_PREFIX = 'kinematics-personal-plan:latest-v10:';
    var LEGACY_PLAN_CACHE_KEYS = [
        'kinematics-personal-plan:latest-v1',
        'kinematics-personal-plan:latest-v2',
        'kinematics-personal-plan:latest-v3',
        'kinematics-personal-plan:latest-v4'
    ];
    var LEGACY_PLAN_CACHE_PREFIXES = [
        'kinematics-personal-plan:latest-v5:',
        'kinematics-personal-plan:latest-v6:',
        'kinematics-personal-plan:latest-v7:',
        'kinematics-personal-plan:latest-v8:',
        'kinematics-personal-plan:latest-v9:'
    ];
    var MAX_GENERATION_ATTEMPTS = 20;
    var GENERATION_RETRY_DELAY_MS = 2500;
    var ALLOWED_PLAN_SOURCES = {
        mistral: true,
        fallback: true
    };
    function currentRouteToken() {
        return window.KinematicsShell ? Number(window.KinematicsShell.routeToken || 0) : 0;
    }

    function isActiveRoute(routeToken) {
        return activeRouteToken === routeToken && currentRouteToken() === routeToken;
    }

    function clearPendingRetry() {
        if (!pendingRetryTimer) {
            return;
        }
        window.clearTimeout(pendingRetryTimer);
        pendingRetryTimer = 0;
    }

    function removeStorageKey(key) {
        if (!key) {
            return;
        }
        try {
            window.localStorage.removeItem(key);
        } catch (_error) {
            return;
        }
    }

    function clearLegacyPlanCaches() {
        LEGACY_PLAN_CACHE_KEYS.forEach(removeStorageKey);
        try {
            var keysToRemove = [];
            for (var index = 0; index < window.localStorage.length; index += 1) {
                var key = window.localStorage.key(index);
                if (!key) {
                    continue;
                }
                if (LEGACY_PLAN_CACHE_PREFIXES.some(function (prefix) { return key.indexOf(prefix) === 0; })) {
                    keysToRemove.push(key);
                }
            }
            keysToRemove.forEach(removeStorageKey);
        } catch (_error) {
            return;
        }
    }

    function normalizeProfile(profile) {
        return site.normalizePublicUser
            ? site.normalizePublicUser(site.ensureObject(profile))
            : site.ensureObject(profile);
    }

    function getBootstrapPayload() {
        return site.ensureObject(window.KinematicsBootstrap);
    }

    function getBootstrappedProfile() {
        return normalizeProfile(getBootstrapPayload().profile);
    }

    function getBootstrappedPlan() {
        var plan = site.ensureObject(getBootstrapPayload().plan);
        return isCompletePlan(plan) ? plan : null;
    }

    function resolvePlanCacheKey(profile) {
        var source = normalizeProfile(profile);
        var userId = site.ensureFiniteNumber(source.user_id);
        if (userId != null) {
            return PLAN_CACHE_KEY_PREFIX + 'user:' + String(userId);
        }
        var email = site.ensureString(source.email, '');
        if (email) {
            return PLAN_CACHE_KEY_PREFIX + 'email:' + email.toLowerCase();
        }
        var telegramUserId = site.ensureString(source.telegram_user_id, '');
        if (telegramUserId) {
            return PLAN_CACHE_KEY_PREFIX + 'tg:' + telegramUserId;
        }
        return PLAN_CACHE_KEY_PREFIX + 'anonymous';
    }

    function setCurrentPlanCacheKey(profile) {
        currentPlanCacheKey = resolvePlanCacheKey(profile);
    }

    function clearCachedPlan() {
        removeStorageKey(currentPlanCacheKey);
    }

    function readPlanHandoff() {
        var raw;
        var parsed;

        if (!site.safeGetSessionStorage) {
            return null;
        }
        raw = site.safeGetSessionStorage(PLAN_HANDOFF_STORAGE_KEY);
        if (!raw) {
            return null;
        }
        try {
            parsed = JSON.parse(raw);
        } catch (_error) {
            if (site.safeRemoveSessionStorage) {
                site.safeRemoveSessionStorage(PLAN_HANDOFF_STORAGE_KEY);
            }
            return null;
        }
        if (!isCompletePlan(parsed)) {
            if (site.safeRemoveSessionStorage) {
                site.safeRemoveSessionStorage(PLAN_HANDOFF_STORAGE_KEY);
            }
            return null;
        }
        return parsed;
    }

    function clearPlanHandoff() {
        if (site.safeRemoveSessionStorage) {
            site.safeRemoveSessionStorage(PLAN_HANDOFF_STORAGE_KEY);
        }
    }

    function hasFreshPlanFlag() {
        try {
            var params = new window.URLSearchParams(window.location.search || '');
            return !!site.ensureString(params.get('fresh_plan'), '');
        } catch (_error) {
            return false;
        }
    }

    function consumeFreshPlanFlag() {
        try {
            var params = new window.URLSearchParams(window.location.search || '');
            if (!params.has('fresh_plan')) {
                return;
            }
            params.delete('fresh_plan');
            var nextSearch = params.toString();
            var nextUrl = window.location.pathname + (nextSearch ? '?' + nextSearch : '') + window.location.hash;
            window.history.replaceState(window.history.state || {}, document.title, nextUrl);
        } catch (_error) {
            return;
        }
    }

    function isCompleteExercise(item) {
        var source = site.ensureObject(item);
        return !!site.ensureString(source.title, '')
            && (site.ensureFiniteNumber(source.sets) || 0) > 0
            && (site.ensureFiniteNumber(source.reps) || 0) > 0;
    }

    function isCompletePlan(plan) {
        var source = site.ensureObject(plan);
        var stages = site.ensureArray(source.stages);
        var totalDays = 0;

        if (!ALLOWED_PLAN_SOURCES[site.ensureString(source.source, '')]) {
            return false;
        }
        if (!site.ensureString(source.headline, '') || !site.ensureString(source.subheadline, '')) {
            return false;
        }
        if (!site.ensureStringArray(source.tags).length) {
            return false;
        }
        if (!site.ensureArray(source.summary_items).length) {
            return false;
        }
        if (stages.length !== 1) {
            return false;
        }

        return stages.every(function (stage) {
            var days = site.ensureArray(stage && stage.days);
            if (!days.length) {
                return false;
            }
            totalDays += days.length;
            return days.every(function (day) {
                var exercises = site.ensureArray(day && day.exercises);
                return !!site.ensureString(day && day.title, '')
                    && exercises.length > 0
                    && exercises.every(isCompleteExercise);
            });
        }) && totalDays === 10;
    }

    function loadCachedPlan() {
        var raw;
        var parsed;

        if (!currentPlanCacheKey) {
            return null;
        }
        raw = site.safeGetStorage(currentPlanCacheKey);
        if (!raw) {
            return null;
        }
        try {
            parsed = JSON.parse(raw);
        } catch (_error) {
            clearCachedPlan();
            return null;
        }
        if (!isCompletePlan(parsed)) {
            clearCachedPlan();
            return null;
        }
        return parsed;
    }

    function saveCachedPlan(plan) {
        if (!currentPlanCacheKey) {
            return;
        }
        if (!isCompletePlan(plan)) {
            clearCachedPlan();
            return;
        }
        try {
            window.localStorage.setItem(currentPlanCacheKey, JSON.stringify(plan));
        } catch (_error) {
            return;
        }
    }

    function normalizeSummaryItem(item) {
        var source = site.ensureObject(item);
        return {
            label: site.ensureString(source.label, 'Параметр'),
            value: site.ensureString(source.value, '—')
        };
    }

    function normalizeDay(day) {
        var source = site.ensureObject(day);
        return {
            day_number: site.ensureFiniteNumber(source.day_number) || 0,
            stage_number: site.ensureFiniteNumber(source.stage_number) || 1,
            date_label: site.ensureString(source.date_label, ''),
            title: site.ensureString(source.title, 'День'),
            subtitle: site.ensureString(source.subtitle, ''),
            duration_min: site.ensureFiniteNumber(source.duration_min) || 0,
            estimated_kcal: site.ensureFiniteNumber(source.estimated_kcal) || 0,
            intensity: site.ensureString(source.intensity, ''),
            emphasis: site.ensureString(source.emphasis, ''),
            note: site.ensureString(source.note, ''),
            kind: site.ensureString(source.kind, 'workout'),
            exercises: site.ensureArray(source.exercises).map(function (item) {
                var exercise = site.ensureObject(item);
                return {
                    slug: site.ensureString(exercise.slug, ''),
                    title: site.ensureString(exercise.title, 'Упражнение'),
                    details: site.ensureString(exercise.details, ''),
                    sets: site.ensureFiniteNumber(exercise.sets) || 0,
                    reps: site.ensureFiniteNumber(exercise.reps) || 0,
                    rest_sec: site.ensureFiniteNumber(exercise.rest_sec) || 0
                };
            }),
            is_highlighted: source.is_highlighted === true
        };
    }

    function normalizeStage(stage) {
        var source = site.ensureObject(stage);
        var days = site.ensureArray(source.days).map(function (item) {
            return normalizeDay(item);
        });
        days.sort(function (left, right) {
            return (left.day_number || 0) - (right.day_number || 0);
        });
        return {
            stage_number: site.ensureFiniteNumber(source.stage_number) || 1,
            title: site.ensureString(source.title, 'Этап 1'),
            subtitle: site.ensureString(source.subtitle, ''),
            badge: site.ensureString(source.badge, 'Этап 1'),
            days: days
        };
    }

    function normalizePlan(plan) {
        var source = site.ensureObject(plan);
        return {
            signature: site.ensureString(source.signature, ''),
            source: site.ensureString(source.source, ''),
            generated_at: site.ensureString(source.generated_at, ''),
            headline: site.ensureString(source.headline, 'Мой план'),
            subheadline: site.ensureString(source.subheadline, ''),
            tags: site.ensureStringArray(source.tags),
            summary_items: site.ensureArray(source.summary_items).map(normalizeSummaryItem),
            stages: site.ensureArray(source.stages).map(normalizeStage)
        };
    }

    function totalDaysForPlan(plan) {
        return plan.stages.reduce(function (total, stage) {
            return total + stage.days.length;
        }, 0);
    }

    function findPlanDay(plan, dayNumber) {
        var match = null;
        plan.stages.some(function (stage) {
            return stage.days.some(function (day) {
                if (day.day_number === dayNumber) {
                    match = day;
                    return true;
                }
                return false;
            });
        });
        return match;
    }

    function resolveSelectedDay(stage) {
        var preferred = currentSelectedDayNumber ? findPlanDay({ stages: [stage] }, currentSelectedDayNumber) : null;
        if (preferred) {
            return preferred;
        }
        return site.ensureArray(stage.days)[0] || null;
    }

    function renderTag(tag) {
        return '<span class="plan-pill-tag">' + site.escapeHtml(tag) + '</span>';
    }

    function renderExerciseRow(exercise, index) {
        return [
            '<article class="plan-exercise-row">',
            '<div class="plan-exercise-order">', index + 1, '</div>',
            '<div class="plan-exercise-copy">',
            '<h4>', site.escapeHtml(exercise.title), '</h4>',
            exercise.details ? '<p>' + site.escapeHtml(exercise.details) + '</p>' : '',
            '<div class="plan-exercise-stats">',
            '<span>', exercise.sets, ' подхода</span>',
            '<span>', exercise.reps, ' повторов</span>',
            '<span>', exercise.rest_sec, 'с отдых</span>',
            '</div>',
            '</div>',
            '</article>'
        ].join('');
    }

    function renderDayOverviewModal(day) {
        return [
            '<div class="plan-day-modal">',
            '<div class="plan-day-modal-backdrop" data-plan-modal-close></div>',
            '<section class="plan-day-modal-sheet" role="dialog" aria-modal="true" aria-label="Обзор дня">',
            '<div class="plan-day-modal-head">',
            '<div class="plan-day-modal-copy">',
            '<span class="plan-day-focus-kicker">День ', day.day_number, ' · обзор</span>',
            '<h3>', site.escapeHtml(day.title), '</h3>',
            '<p>', site.escapeHtml(day.subtitle || day.date_label || ''), '</p>',
            '</div>',
            '<button class="plan-day-modal-close" type="button" data-plan-modal-close aria-label="Закрыть">×</button>',
            '</div>',
            day.date_label ? '<p class="plan-day-focus-subtitle">' + site.escapeHtml(day.date_label) + '</p>' : '',
            day.note ? '<p class="plan-day-focus-note">' + site.escapeHtml(day.note) + '</p>' : '',
            '<div class="plan-exercise-list">',
            day.exercises.map(renderExerciseRow).join(''),
            '</div>',
            '</section>'
        ].join('');
    }

    function renderDayTimelineMarker(isSelected) {
        return [
            '<div class="plan-day-marker ', isSelected ? 'is-selected' : '', '">',
            '<span></span>',
            '</div>'
        ].join('');
    }

    function dayKindClass(kind) {
        var normalized = site.ensureString(kind, '').toLowerCase();
        if (normalized === 'workout' || normalized === 'recovery' || normalized === 'rest') {
            return normalized;
        }
        return 'default';
    }

    function dayKindLabel(kind) {
        var normalized = site.ensureString(kind, '').toLowerCase();
        if (normalized === 'recovery') {
            return 'Восстановление';
        }
        if (normalized === 'rest') {
            return 'Отдых';
        }
        if (normalized === 'workout') {
            return 'Тренировка';
        }
        return 'День плана';
    }

    function renderFeaturedDayCard(day) {
        var lead = day.note || day.subtitle || '';
        return [
            '<article class="plan-day-card plan-day-card--featured is-active">',
            '<div class="plan-day-card-accent plan-day-card-accent--', dayKindClass(day.kind), '">',
            '<div class="plan-day-card-accent-head">',
            '<span class="plan-day-focus-kicker">Выбрано сейчас</span>',
            '<span class="plan-day-card-number">День ', day.day_number, '</span>',
            '</div>',
            '<h3>', site.escapeHtml(day.title), '</h3>',
            lead ? '<p class="plan-day-card-lead">' + site.escapeHtml(lead) + '</p>' : '',
            '</div>',
            '<div class="plan-day-card-body">',
            '<button class="plan-day-cta" type="button" data-plan-open-day="', day.day_number, '">Обзор</button>',
            '</div>',
            '</article>'
        ].join('');
    }

    function renderCompactDayCard(day, isSelected) {
        var description = day.note || day.subtitle || '';
        return [
            '<article class="plan-day-card plan-day-card--compact ', isSelected ? 'is-active' : '', '" data-plan-open-day="', day.day_number, '" role="button" tabindex="0">',
            '<div class="plan-day-card-ribbon plan-day-card-accent--', dayKindClass(day.kind), '">',
            '<span class="plan-day-card-number">День ', day.day_number, '</span>',
            '</div>',
            '<div class="plan-day-card-body">',
            '<h3>', site.escapeHtml(day.title), '</h3>',
            description ? '<p>' + site.escapeHtml(description) + '</p>' : '',
            '</div>',
            '</article>'
        ].join('');
    }

    function renderDayTimeline(stage, selectedDayNumber) {
        return [
            '<section class="plan-day-timeline">',
            site.ensureArray(stage.days).map(function (day) {
                var isSelected = selectedDayNumber === day.day_number;
                return [
                    '<div class="plan-day-timeline-item ', isSelected ? 'is-selected' : '', '">',
                    renderDayTimelineMarker(isSelected),
                    isSelected ? renderFeaturedDayCard(day) : renderCompactDayCard(day, isSelected),
                    '</div>'
                ].join('');
            }).join(''),
            '</section>'
        ].join('');
    }

    function bindModalActions(root) {
        root.querySelectorAll('[data-plan-modal-close]').forEach(function (node) {
            node.addEventListener('click', function (event) {
                event.preventDefault();
                isDayModalOpen = false;
                if (!currentRenderedPlan) {
                    return;
                }
                renderPlan(root, currentRenderedPlan, {
                    isRefreshing: false,
                    feedback: currentRenderFeedback
                });
            });
        });
    }

    function bindDayActions(root) {
        root.querySelectorAll('[data-plan-open-day]').forEach(function (node) {
            node.addEventListener('click', function (event) {
                var dayNumber = Number(node.getAttribute('data-plan-open-day'));
                if (!Number.isFinite(dayNumber) || !currentRenderedPlan) {
                    return;
                }
                event.preventDefault();
                currentSelectedDayNumber = dayNumber;
                isDayModalOpen = true;
                renderPlan(root, currentRenderedPlan, {
                    isRefreshing: false,
                    feedback: currentRenderFeedback
                });
            });
            node.addEventListener('keydown', function (event) {
                if (event.key !== 'Enter' && event.key !== ' ') {
                    return;
                }
                event.preventDefault();
                node.click();
            });
        });
    }

    function renderPlan(root, plan, options) {
        var normalizedPlan = normalizePlan(plan);
        var stage = normalizedPlan.stages[0];
        var selectedDay = resolveSelectedDay(stage);
        var stageLine = site.ensureString(stage.subtitle, '') || site.ensureString(stage.title, '') || 'Персональный блок';
        var feedback = site.ensureString(options && options.feedback, '');

        clearPendingRetry();
        currentRenderedPlan = plan;
        currentRenderFeedback = feedback;
        currentSelectedDayNumber = selectedDay ? selectedDay.day_number : null;
        root.innerHTML = [
            '<section class="plan-screen-shell">',
            feedback ? '<p class="plan-inline-message is-error">' + site.escapeHtml(feedback) + '</p>' : '',
            '<header class="plan-hero-head">',
            '<p class="plan-hero-focus">', site.escapeHtml(String(normalizedPlan.headline || '').toUpperCase()), '</p>',
            '<h1 class="plan-hero-goal">', site.escapeHtml(String(normalizedPlan.subheadline || '').toUpperCase()), '</h1>',
            '<div class="plan-pill-row">',
            normalizedPlan.tags.map(renderTag).join(''),
            '</div>',
            '</header>',
            '<section class="plan-stage-copy">',
            '<h2>', site.escapeHtml(stage.badge || ('Этап ' + stage.stage_number)), '</h2>',
            '<p>', site.escapeHtml(stageLine), '</p>',
            '</section>',
            renderDayTimeline(stage, selectedDay ? selectedDay.day_number : null),
            isDayModalOpen && selectedDay ? renderDayOverviewModal(selectedDay) : '',
            '</section>'
        ].join('');

        bindDayActions(root);
        bindModalActions(root);
    }

    function renderGeneratingState(root, options) {
        var attempt = Math.max(1, Number(options && options.attempt) || 1);
        var autoRetryScheduled = options && options.autoRetryScheduled === true;
        var message = autoRetryScheduled
            ? 'Пробую снова. Следующая проверка через пару секунд.'
            : 'План еще не готов. Можно запустить генерацию вручную.';

        root.innerHTML = [
            '<section class="plan-screen-shell">',
            '<header class="plan-hero-head">',
            '<p class="plan-hero-focus">МОЙ ПЛАН</p>',
            '<h1 class="plan-hero-goal">СОБИРАЕМ МАРШРУТ</h1>',
            '<div class="plan-pill-row">',
            '<span class="plan-pill-tag">Mistral</span>',
            '<span class="plan-pill-tag">10 дней</span>',
            '<span class="plan-pill-tag">Индивидуально</span>',
            '</div>',
            '</header>',
            '<section class="plan-generation-sheet">',
            '<h2>Готовим персональный план</h2>',
            '<p>Mistral собирает один цельный 10-дневный маршрут на основе первого интервью. Как только JSON будет готов, этот экран сам исчезнет.</p>',
            '<div class="plan-generation-status">',
            '<strong>Попытка ', attempt, ' из ', MAX_GENERATION_ATTEMPTS, '</strong>',
            '<span>', site.escapeHtml(message), '</span>',
            '</div>',
            '<button id="plan-generation-retry-btn" class="plan-day-cta plan-day-cta--static" type="button">Повторить сейчас</button>',
            '</section>',
            '</section>'
        ].join('');
    }

    function isOnboardingMissingError(error) {
        var message = site.ensureString(error && error.message, '').toLowerCase();
        return Number(error && error.status) === 404 && message.indexOf('onboarding') >= 0;
    }

    function bindGenerationRetry(root, routeToken) {
        var retryButton = document.getElementById('plan-generation-retry-btn');
        if (!retryButton) {
            return;
        }
        retryButton.addEventListener('click', function () {
            requestPlan(routeToken, root, {
                refresh: true,
                cachedPlan: loadCachedPlan(),
                generationAttempt: 1,
                allowAutoRetry: true
            });
        });
    }

    function scheduleGenerationRetry(routeToken, root, options) {
        var nextAttempt = Number(options && options.nextAttempt) || 0;

        clearPendingRetry();
        if (nextAttempt <= 0 || nextAttempt > MAX_GENERATION_ATTEMPTS) {
            return;
        }
        pendingRetryTimer = window.setTimeout(function () {
            if (!isActiveRoute(routeToken)) {
                return;
            }
            requestPlan(routeToken, root, {
                refresh: false,
                cachedPlan: loadCachedPlan(),
                generationAttempt: nextAttempt,
                allowAutoRetry: true
            });
        }, GENERATION_RETRY_DELAY_MS);
    }

    function requestPlan(routeToken, root, options) {
        var refresh = options && options.refresh === true;
        var generationAttempt = Math.max(1, Number(options && options.generationAttempt) || 1);
        var cachedPlan = options && isCompletePlan(options.cachedPlan) ? options.cachedPlan : loadCachedPlan();
        var url = refresh ? '/api/plan?refresh=1' : '/api/plan';

        clearPendingRetry();

        return site.requireJson(url, null, 'Не удалось собрать персональный план.')
            .then(function (plan) {
                var incompleteError;

                if (!isActiveRoute(routeToken)) {
                    return;
                }
                if (!isCompletePlan(plan)) {
                    incompleteError = new Error('План еще не готов.');
                    incompleteError.code = 'PLAN_GENERATION_UNAVAILABLE';
                    incompleteError.status = 503;
                    throw incompleteError;
                }
                if (!currentPlanCacheKey && site.ensureFiniteNumber(plan && plan.user_id) != null) {
                    currentPlanCacheKey = resolvePlanCacheKey(plan);
                }
                saveCachedPlan(plan);
                renderPlan(root, plan, { isRefreshing: false });
            })
            .catch(function (error) {
                var autoRetryAllowed = options && options.allowAutoRetry === true;
                var hasMoreAttempts = autoRetryAllowed && generationAttempt < MAX_GENERATION_ATTEMPTS;

                if (!isActiveRoute(routeToken)) {
                    return;
                }
                if (cachedPlan && error && error.code === 'AUTH_REQUIRED') {
                    renderPlan(root, cachedPlan, {
                        isRefreshing: false,
                        feedback: 'Показана последняя сохраненная версия плана. Обновление сессии не удалось.'
                    });
                    return;
                }
                if (error && error.code === 'AUTH_REQUIRED') {
                    site.renderState(root, 'Требуется авторизация', 'Не удалось восстановить сессию Mini App.', true);
                    return;
                }
                if (error && error.code === 'ONBOARDING_REQUIRED') {
                    throw error;
                }
                if (cachedPlan) {
                    renderPlan(root, cachedPlan, {
                        isRefreshing: false,
                        feedback: refresh ? (error.message || 'Не удалось обновить план. Показана последняя сохраненная версия.') : ''
                    });
                    return;
                }
                if (error && error.code === 'PLAN_GENERATION_UNAVAILABLE') {
                    renderGeneratingState(root, {
                        attempt: generationAttempt,
                        autoRetryScheduled: hasMoreAttempts
                    });
                    bindGenerationRetry(root, routeToken);
                    if (hasMoreAttempts) {
                        scheduleGenerationRetry(routeToken, root, {
                            nextAttempt: generationAttempt + 1
                        });
                    }
                    return;
                }
                if (isOnboardingMissingError(error)) {
                    site.redirectToOnboarding();
                    return;
                }
                site.renderState(root, 'Ошибка', error.message || 'Не удалось загрузить мой план.', true);
            });
    }

    function loadProfile(routeToken, bootstrappedProfile) {
        if (bootstrappedProfile && site.ensureFiniteNumber(bootstrappedProfile.user_id) != null) {
            site.setUserShell(bootstrappedProfile);
            setCurrentPlanCacheKey(bootstrappedProfile);
            return Promise.resolve(bootstrappedProfile);
        }

        return site.requireJson('/api/profile', null, 'Не удалось загрузить профиль.')
            .then(function (profile) {
                if (!isActiveRoute(routeToken)) {
                    return null;
                }
                site.setUserShell(profile);
                setCurrentPlanCacheKey(profile);
                return profile;
            })
            .catch(function () {
                return null;
            });
    }

    function mountProgramsPage() {
        var routeToken = currentRouteToken();
        var root = document.getElementById('page-root');
        var bootstrappedProfile = getBootstrappedProfile();
        var bootstrappedPlan = getBootstrappedPlan();
        var handoffPlan = readPlanHandoff();
        var freshPlanRequested = hasFreshPlanFlag();
        var cachedPlan;
        var initialPlan = handoffPlan || bootstrappedPlan || null;

        activeRouteToken = routeToken;
        clearPendingRetry();
        clearLegacyPlanCaches();
        currentPlanCacheKey = '';
        currentSelectedDayNumber = null;
        isDayModalOpen = false;
        site.renderState(root, 'Загрузка', 'Собираю ваш персональный план...', false);

        if (bootstrappedProfile && site.ensureFiniteNumber(bootstrappedProfile.user_id) != null) {
            site.setUserShell(bootstrappedProfile);
            setCurrentPlanCacheKey(bootstrappedProfile);
        }

        cachedPlan = freshPlanRequested ? null : loadCachedPlan();

        if (initialPlan) {
            if (currentPlanCacheKey) {
                saveCachedPlan(initialPlan);
            }
            clearPlanHandoff();
            cachedPlan = initialPlan;
            renderPlan(root, initialPlan, { isRefreshing: false });
        } else if (cachedPlan) {
            renderPlan(root, cachedPlan, { isRefreshing: true });
        }

        loadProfile(routeToken, bootstrappedProfile)
            .then(function () {
                if (!isActiveRoute(routeToken)) {
                    return;
                }
                if (initialPlan) {
                    saveCachedPlan(initialPlan);
                    clearPlanHandoff();
                    cachedPlan = initialPlan;
                    return;
                }
                cachedPlan = freshPlanRequested ? null : loadCachedPlan();
                if (cachedPlan) {
                    renderPlan(root, cachedPlan, { isRefreshing: true });
                }
            })
            .then(function () {
                if (!isActiveRoute(routeToken)) {
                    return;
                }
                consumeFreshPlanFlag();
                return requestPlan(routeToken, root, {
                    refresh: false,
                    cachedPlan: cachedPlan,
                    generationAttempt: 1,
                    allowAutoRetry: true
                });
            })
            .catch(function (error) {
                if (!isActiveRoute(routeToken)) {
                    return;
                }
                if (error && error.code === 'ONBOARDING_REQUIRED') {
                    site.redirectToOnboarding();
                    return;
                }
                if (isOnboardingMissingError(error)) {
                    site.redirectToOnboarding();
                    return;
                }
                if (cachedPlan) {
                    renderPlan(root, cachedPlan, {
                        isRefreshing: false,
                        feedback: error && error.message ? error.message : 'Не удалось обновить план. Показана последняя сохраненная версия.'
                    });
                    return;
                }
                site.renderState(root, 'Ошибка', error && error.message ? error.message : 'Не удалось загрузить мой план.', true);
            });
    }

    window.KinematicsPages = window.KinematicsPages || {};
    window.KinematicsPages.plan = mountProgramsPage;

    document.addEventListener('DOMContentLoaded', mountProgramsPage);
})();
