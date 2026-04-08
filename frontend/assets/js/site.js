(function () {
    var GOAL_TYPE_LABELS = {
        weight_loss: 'Похудение',
        muscle_gain: 'Набор массы',
        endurance: 'Выносливость'
    };

    var LEVEL_LABELS = {
        beginner: 'Начинающий',
        intermediate: 'Средний',
        advanced: 'Продвинутый'
    };

    var PENDING_ONBOARDING_RESET_KEY = 'kinematics-pending-onboarding-reset';
    var RESET_START_PARAM_CAPTURED_KEY = 'kinematics-reset-start-param-captured';
    var ONBOARDING_COMPLETED_KEY_PREFIX = 'kinematics-onboarding-completed:v4:';
    var JUST_COMPLETED_ONBOARDING_KEY = 'kinematics-just-completed-onboarding-v4';
    var TELEGRAM_INIT_DATA_KEY = 'kinematics-telegram-init-data';
    var tgInstance = null;
    var telegramAuthPromise = null;

    function isSyntheticTelegramEmail(email) {
        var value = String(email || '').trim().toLowerCase();
        return value.indexOf('tg_') === 0 && value.slice(-15) === '@telegram.local';
    }

    function safeGetStorage(key) {
        try {
            return window.localStorage.getItem(key);
        } catch (error) {
            return null;
        }
    }

    function safeSetStorage(key, value) {
        try {
            window.localStorage.setItem(key, value);
        } catch (error) {
            return;
        }
    }

    function safeGetSessionStorage(key) {
        try {
            return window.sessionStorage.getItem(key);
        } catch (error) {
            return null;
        }
    }

    function safeSetSessionStorage(key, value) {
        try {
            window.sessionStorage.setItem(key, value);
        } catch (error) {
            return;
        }
    }

    function safeRemoveSessionStorage(key) {
        try {
            window.sessionStorage.removeItem(key);
        } catch (error) {
            return;
        }
    }

    function initTelegram() {
        var tg = window.Telegram && window.Telegram.WebApp ? window.Telegram.WebApp : null;
        if (!tg) {
            return null;
        }

        tgInstance = tg;

        try {
            tg.ready();
            tg.expand();
        } catch (error) {
            if (tg.initData) {
                safeSetSessionStorage(TELEGRAM_INIT_DATA_KEY, tg.initData);
            }
            return tg;
        }

        if (tg.initData) {
            safeSetSessionStorage(TELEGRAM_INIT_DATA_KEY, tg.initData);
        }
        applyTelegramTheme(tg.themeParams || {});
        captureResetStartParam(tg);
        document.documentElement.classList.add('telegram-webapp-ready');
        return tg;
    }

    function getTelegramInitData() {
        var tg = tgInstance || initTelegram();
        if (tg && tg.initData) {
            safeSetSessionStorage(TELEGRAM_INIT_DATA_KEY, tg.initData);
            return tg.initData;
        }
        return safeGetSessionStorage(TELEGRAM_INIT_DATA_KEY) || '';
    }

    function captureResetStartParam(tg) {
        var instance = tg || tgInstance || null;
        var startParam = instance && instance.initDataUnsafe
            ? String(instance.initDataUnsafe.start_param || '').trim()
            : '';
        var params = new window.URLSearchParams(window.location.search || '');
        var queryReset = params.get('reset_onboarding') === '1' || params.get('reset_onboarding') === 'true';
        if ((startParam === 'reset_onboarding' || queryReset) && safeGetSessionStorage(RESET_START_PARAM_CAPTURED_KEY) !== '1') {
            safeSetSessionStorage(PENDING_ONBOARDING_RESET_KEY, '1');
            safeSetSessionStorage(RESET_START_PARAM_CAPTURED_KEY, '1');
            if (queryReset) {
                try {
                    params.delete('reset_onboarding');
                    var nextSearch = params.toString();
                    var nextUrl = window.location.pathname + (nextSearch ? '?' + nextSearch : '') + window.location.hash;
                    window.history.replaceState({}, document.title, nextUrl);
                } catch (error) {
                    return startParam || 'reset_onboarding';
                }
            }
        }
        return startParam || (queryReset ? 'reset_onboarding' : '');
    }

    function applyTelegramTheme(themeParams) {
        var params = themeParams || {};
        var root = document.documentElement;

        if (params.bg_color) {
            root.style.setProperty('--tg-bg-color', params.bg_color);
        }
        if (params.secondary_bg_color) {
            root.style.setProperty('--tg-secondary-bg-color', params.secondary_bg_color);
        }
        if (params.text_color) {
            root.style.setProperty('--tg-text-color', params.text_color);
        }
        if (params.link_color) {
            root.style.setProperty('--tg-link-color', params.link_color);
        }
        if (params.button_color) {
            root.style.setProperty('--tg-button-color', params.button_color);
        }
        if (params.button_text_color) {
            root.style.setProperty('--tg-button-text-color', params.button_text_color);
        }
    }

    function getTelegramUser() {
        var tg = tgInstance || initTelegram();
        if (!tg || !tg.initDataUnsafe || !tg.initDataUnsafe.user) {
            return null;
        }
        return tg.initDataUnsafe.user;
    }

    function getOnboardingCompletionStorageKey() {
        var telegramUser = getTelegramUser();
        if (telegramUser && telegramUser.username) {
            return ONBOARDING_COMPLETED_KEY_PREFIX + 'username:' + String(telegramUser.username).trim().toLowerCase();
        }
        if (telegramUser && telegramUser.id) {
            return ONBOARDING_COMPLETED_KEY_PREFIX + 'id:' + String(telegramUser.id).trim();
        }
        return null;
    }

    function markOnboardingCompletedLocally() {
        var key = getOnboardingCompletionStorageKey();
        safeSetSessionStorage(JUST_COMPLETED_ONBOARDING_KEY, '1');
        if (!key) {
            return;
        }
        safeSetStorage(key, '1');
    }

    function clearOnboardingCompletedLocally() {
        var key = getOnboardingCompletionStorageKey();
        safeRemoveSessionStorage(JUST_COMPLETED_ONBOARDING_KEY);
        if (!key) {
            return;
        }
        try {
            window.localStorage.removeItem(key);
        } catch (error) {
            return;
        }
    }

    function hasCompletedOnboardingLocally() {
        var key = getOnboardingCompletionStorageKey();
        if (!key) {
            return false;
        }
        return safeGetStorage(key) === '1';
    }

    function hasJustCompletedOnboarding() {
        return safeGetSessionStorage(JUST_COMPLETED_ONBOARDING_KEY) === '1';
    }

    function hasOnboardingCompletionHint() {
        return hasJustCompletedOnboarding() || hasCompletedOnboardingLocally();
    }

    function ensureArray(value) {
        return Array.isArray(value) ? value : [];
    }

    function ensureObject(value) {
        return value && typeof value === 'object' && !Array.isArray(value) ? value : {};
    }

    function ensureString(value, fallback) {
        var normalized = typeof value === 'string' ? value.trim() : '';
        return normalized || String(fallback || '');
    }

    function ensureBoolean(value) {
        return value === true;
    }

    function ensureFiniteNumber(value) {
        var normalized = Number(value);
        return Number.isFinite(normalized) ? normalized : null;
    }

    function ensureStringArray(value) {
        return ensureArray(value).map(function (item) {
            return typeof item === 'string' ? item.trim() : '';
        }).filter(function (item) {
            return !!item;
        });
    }

    function normalizeSettings(settings) {
        var source = ensureObject(settings);
        return {
            theme_preference: ensureString(source.theme_preference, 'system'),
            language: ensureString(source.language, 'ru'),
            weight_unit: ensureString(source.weight_unit, 'kg'),
            height_unit: ensureString(source.height_unit, 'cm'),
            timezone: ensureString(source.timezone, 'UTC'),
            telegram_linked: ensureBoolean(source.telegram_linked),
            telegram_username: ensureString(source.telegram_username, ''),
            telegram_first_name: ensureString(source.telegram_first_name, ''),
            telegram_user_id: ensureString(source.telegram_user_id, ''),
            telegram_bot_username: ensureString(source.telegram_bot_username, '')
        };
    }

    function isTelegramMiniApp() {
        return !!getTelegramUser();
    }

    function renderTelegramContext() {
        var target = document.getElementById('telegram-context');
        if (!target) {
            return;
        }

        var user = getTelegramUser();
        if (!user) {
            target.textContent = 'Telegram WebApp SDK не передал пользователя. Это нормально при открытии страницы вне Telegram.';
            return;
        }

        var label = user.first_name || user.username || String(user.id);
        target.textContent = 'Telegram: ' + label;
    }

    function escapeHtml(text) {
        return String(text == null ? '' : text)
            .replace(/&/g, '&amp;')
            .replace(/</g, '&lt;')
            .replace(/>/g, '&gt;')
            .replace(/\"/g, '&quot;')
            .replace(/'/g, '&#039;');
    }

    function parseJsonSafe(response) {
        return response.json().catch(function () {
            return {};
        });
    }

    function parseApiError(data, fallbackMessage) {
        if (!data) {
            return fallbackMessage;
        }

        if (typeof data.detail === 'string') {
            return data.detail;
        }

        if (data.detail && typeof data.detail === 'object') {
            if (typeof data.detail.message === 'string' && data.detail.message.trim()) {
                return data.detail.message.trim();
            }
            if (typeof data.detail.error === 'string' && data.detail.error.trim()) {
                return data.detail.error.trim();
            }
        }

        if (Array.isArray(data.detail) && data.detail.length > 0) {
            var first = data.detail[0];
            if (first && typeof first.msg === 'string') {
                return first.msg;
            }
        }

        return fallbackMessage;
    }

    function buildApiError(data, fallbackMessage, status) {
        var apiError = new Error(parseApiError(data, fallbackMessage));
        apiError.status = Number(status) || 0;
        if (data && data.detail && typeof data.detail === 'object') {
            apiError.detail = data.detail;
            if (typeof data.detail.code === 'string' && data.detail.code.trim()) {
                apiError.code = data.detail.code.trim();
            }
        }
        return apiError;
    }

    function withDefaultOptions(options) {
        var next = Object.assign({ credentials: 'include' }, options || {});
        var tg = tgInstance || initTelegram();
        var headers = Object.assign({}, next.headers || {});
        var isApiRequest = typeof next.url === 'string' ? next.url.indexOf('/api/') === 0 : false;
        if (!isApiRequest && typeof options === 'object' && options && typeof options.__requestUrl === 'string') {
            isApiRequest = options.__requestUrl.indexOf('/api/') === 0;
        }
        if (isApiRequest && !headers['X-Telegram-Init-Data']) {
            var telegramInitData = getTelegramInitData();
            if (telegramInitData) {
                headers['X-Telegram-Init-Data'] = telegramInitData;
            }
        }
        next.headers = headers;
        return next;
    }

    function fetchJson(url, options) {
        var mergedOptions = withDefaultOptions(Object.assign({}, options || {}, { __requestUrl: url }));
        delete mergedOptions.__requestUrl;
        return fetch(url, mergedOptions).then(function (response) {
            return parseJsonSafe(response).then(function (data) {
                return { response: response, data: data };
            });
        });
    }

    function delay(ms) {
        return new Promise(function (resolve) {
            window.setTimeout(resolve, ms);
        });
    }

    function isRetryableStatus(status) {
        return status === 502 || status === 503 || status === 504;
    }

    function fetchJsonWithRetry(url, options, retryOptions) {
        var config = Object.assign({
            retries: 0,
            delayMs: 350,
            backoffMultiplier: 2
        }, retryOptions || {});

        var attempt = 0;

        function run() {
            return fetchJson(url, options)
                .then(function (result) {
                    if (!isRetryableStatus(result.response.status) || attempt >= config.retries) {
                        return result;
                    }
                    attempt += 1;
                    return delay(config.delayMs * Math.pow(config.backoffMultiplier, attempt - 1)).then(run);
                })
                .catch(function (error) {
                    if (attempt >= config.retries) {
                        throw error;
                    }
                    attempt += 1;
                    return delay(config.delayMs * Math.pow(config.backoffMultiplier, attempt - 1)).then(run);
                });
        }

        return run();
    }

    function redirectToLogin() {
        if (isTelegramMiniApp()) {
            if (window.location.pathname === '/') {
                return;
            }
            window.location.replace('/');
            return;
        }
        if (window.location.pathname === '/login') {
            return;
        }
        window.location.assign('/login');
    }

    function redirectToApp() {
        if (window.location.pathname === '/app/programs') {
            return;
        }
        window.location.assign('/app/programs');
    }

    function redirectToOnboarding() {
        if (window.location.pathname === '/app/onboarding') {
            return;
        }
        window.location.replace('/app/onboarding');
    }

    function buildAuthRequiredError() {
        var authError = new Error('AUTH_REQUIRED');
        authError.code = 'AUTH_REQUIRED';
        return authError;
    }

    function requireJson(url, options, fallbackMessage) {
        function runRequest() {
            return fetchJson(url, options);
        }

        return runRequest().then(function (result) {
            if (result.response.status === 401) {
                if (isTelegramMiniApp()) {
                    return authenticateWithTelegram().then(function (user) {
                        if (!user) {
                            redirectToLogin();
                            throw buildAuthRequiredError();
                        }
                        return runRequest().then(function (retryResult) {
                            if (retryResult.response.status === 401) {
                                redirectToLogin();
                                throw buildAuthRequiredError();
                            }
                            if (!retryResult.response.ok) {
                                throw buildApiError(retryResult.data, fallbackMessage || 'Не удалось выполнить запрос.', retryResult.response.status);
                            }
                            return retryResult.data;
                        });
                    });
                }
                redirectToLogin();
                throw buildAuthRequiredError();
            }

            if (!result.response.ok) {
                throw buildApiError(result.data, fallbackMessage || 'Не удалось выполнить запрос.', result.response.status);
            }

            return result.data;
        });
    }

    function requireJsonWithRetry(url, options, fallbackMessage, retryOptions) {
        function runRequest() {
            return fetchJsonWithRetry(url, options, retryOptions);
        }

        return runRequest().then(function (result) {
            if (result.response.status === 401) {
                if (isTelegramMiniApp()) {
                    return authenticateWithTelegram().then(function (user) {
                        if (!user) {
                            redirectToLogin();
                            throw buildAuthRequiredError();
                        }
                        return runRequest().then(function (retryResult) {
                            if (retryResult.response.status === 401) {
                                redirectToLogin();
                                throw buildAuthRequiredError();
                            }
                            if (!retryResult.response.ok) {
                                throw buildApiError(retryResult.data, fallbackMessage || 'Не удалось выполнить запрос.', retryResult.response.status);
                            }
                            return retryResult.data;
                        });
                    });
                }
                redirectToLogin();
                throw buildAuthRequiredError();
            }

            if (!result.response.ok) {
                throw buildApiError(result.data, fallbackMessage || 'Не удалось выполнить запрос.', result.response.status);
            }

            return result.data;
        });
    }

    function sendJson(url, method, payload, fallbackMessage) {
        return requireJson(
            url,
            {
                method: method,
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(payload)
            },
            fallbackMessage
        );
    }

    function ensureAuthenticatedSession(options) {
        var config = Object.assign({
            allowTelegram: true,
            redirectOnFail: true
        }, options || {});

        function failWithAuthRedirect() {
            if (config.redirectOnFail) {
                redirectToLogin();
            }
            throw buildAuthRequiredError();
        }

        function tryTelegramAuth() {
            if (!config.allowTelegram) {
                return failWithAuthRedirect();
            }
            return authenticateWithTelegram().then(function (user) {
                if (user) {
                    return user;
                }
                return failWithAuthRedirect();
            });
        }

        return fetchJsonWithRetry('/api/auth/me', null, { retries: 2, delayMs: 350, backoffMultiplier: 2 })
            .then(function (result) {
                if (result.response.ok) {
                    return result.data;
                }
                if (result.response.status === 401) {
                    return tryTelegramAuth();
                }
                return tryTelegramAuth().catch(function () {
                    throw new Error(parseApiError(result.data, 'Не удалось проверить сессию.'));
                });
            })
            .catch(function (error) {
                if (error && error.code === 'AUTH_REQUIRED') {
                    throw error;
                }
                return tryTelegramAuth().catch(function () {
                    if (error instanceof Error) {
                        throw error;
                    }
                    throw new Error('Не удалось проверить сессию.');
                });
            });
    }

    function hasPendingOnboardingReset() {
        return safeGetSessionStorage(PENDING_ONBOARDING_RESET_KEY) === '1';
    }

    function clearPendingOnboardingReset() {
        safeRemoveSessionStorage(PENDING_ONBOARDING_RESET_KEY);
        safeRemoveSessionStorage(RESET_START_PARAM_CAPTURED_KEY);
    }

    function shouldConsumeOnboardingReset(options) {
        return !!(options && options.allowReset === true);
    }

    function fetchOnboardingState() {
        return ensureAuthenticatedSession({ allowTelegram: true, redirectOnFail: true })
            .then(function () {
                return requireJsonWithRetry(
                    '/api/onboarding',
                    null,
                    'Не удалось загрузить onboarding.',
                    { retries: 4, delayMs: 500, backoffMultiplier: 1.8 }
                );
            })
            .then(function (state) {
                if (state && state.is_completed) {
                    markOnboardingCompletedLocally();
                }
                return state;
            });
    }

    function authenticateWithTelegram() {
        if (telegramAuthPromise) {
            return telegramAuthPromise;
        }

        var tg = tgInstance || initTelegram();
        var initData = getTelegramInitData();
        if (!initData || !tg || !tg.initDataUnsafe || !tg.initDataUnsafe.user) {
            return Promise.resolve(null);
        }

        telegramAuthPromise = fetchJsonWithRetry('/api/auth/telegram', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ init_data: initData })
        }, { retries: 2, delayMs: 400, backoffMultiplier: 2 }).then(function (result) {
            if (result.response.ok) {
                return result.data;
            }
            telegramAuthPromise = null;
            return null;
        }).catch(function () {
            telegramAuthPromise = null;
            return null;
        });

        return telegramAuthPromise;
    }

    function linkTelegramIfPossible() {
        var tg = tgInstance || initTelegram();
        if (!tg || !tg.initData || !tg.initDataUnsafe || !tg.initDataUnsafe.user) {
            return Promise.resolve(null);
        }

        var telegramUserId = String(tg.initDataUnsafe.user.id || '').trim();
        if (!telegramUserId) {
            return Promise.resolve(null);
        }

        var cacheKey = 'kinematics-telegram-link:' + telegramUserId;
        if (safeGetSessionStorage(cacheKey) === '1') {
            return Promise.resolve(null);
        }

        return fetchJsonWithRetry('/api/telegram/link', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ init_data: tg.initData })
        }, { retries: 2, delayMs: 400, backoffMultiplier: 2 }).then(function (result) {
            if (result.response.ok) {
                safeSetSessionStorage(cacheKey, '1');
                return result.data;
            }

            if (result.response.status === 401) {
                return null;
            }

            if (result.response.status === 400 || result.response.status === 409 || result.response.status === 503) {
                safeSetSessionStorage(cacheKey, '1');
                return null;
            }

            return null;
        }).catch(function () {
            return null;
        });
    }

    function consumePendingOnboardingReset() {
        if (!hasPendingOnboardingReset()) {
            return Promise.resolve(false);
        }

        return requireJson(
            '/api/onboarding/reset',
            { method: 'POST' },
            'Не удалось очистить onboarding.'
        ).then(function () {
            clearPendingOnboardingReset();
            clearOnboardingCompletedLocally();
            return true;
        });
    }

    function ensureOnboardingAccess() {
        if (hasOnboardingCompletionHint() && !hasPendingOnboardingReset()) {
            return ensureAuthenticatedSession({ allowTelegram: true, redirectOnFail: true })
                .then(function () {
                    return {
                        is_completed: true,
                        status: 'completed'
                    };
                });
        }
        return fetchOnboardingState().then(function (state) {
            if (!state.is_completed) {
                redirectToOnboarding();
                var onboardingError = new Error('ONBOARDING_REQUIRED');
                onboardingError.code = 'ONBOARDING_REQUIRED';
                throw onboardingError;
            }
            return state;
        });
    }

    function prepareOnboardingPage() {
        var resetResolver = hasPendingOnboardingReset()
            ? consumePendingOnboardingReset().catch(function () {
                clearPendingOnboardingReset();
                throw new Error('Не удалось очистить onboarding.');
            })
            : Promise.resolve(false);

        return resetResolver.then(function () {
            if (hasOnboardingCompletionHint() && !hasPendingOnboardingReset()) {
                redirectToApp();
                var localCompletedError = new Error('ONBOARDING_COMPLETED');
                localCompletedError.code = 'ONBOARDING_COMPLETED';
                return Promise.reject(localCompletedError);
            }
            return fetchOnboardingState().then(function (state) {
                if (state.is_completed) {
                    redirectToApp();
                    var completedError = new Error('ONBOARDING_COMPLETED');
                    completedError.code = 'ONBOARDING_COMPLETED';
                    throw completedError;
                }
                return state;
            });
        });
    }

    function resolveAppEntryUrl(options) {
        if (!shouldConsumeOnboardingReset(options) && hasOnboardingCompletionHint()) {
            return Promise.resolve('/app');
        }
        var resolver = shouldConsumeOnboardingReset(options)
            ? consumePendingOnboardingReset()
            : Promise.resolve(false);
        return resolver.then(function (didReset) {
            if (didReset) {
                return '/app/onboarding';
            }
            if (hasOnboardingCompletionHint()) {
                return '/app';
            }
            return fetchOnboardingState().then(function (state) {
                if (!state.is_completed) {
                    return '/app/onboarding';
                }
                clearPendingOnboardingReset();
                return '/app';
            });
        });
    }

    function resolveDisplayName(user) {
        var normalized = normalizePublicUser(user);
        if (normalized && normalized.name && String(normalized.name).trim()) {
            return String(normalized.name).trim();
        }
        if (normalized && normalized.telegram_first_name && String(normalized.telegram_first_name).trim()) {
            return String(normalized.telegram_first_name).trim();
        }
        if (normalized && normalized.telegram_username && String(normalized.telegram_username).trim()) {
            return '@' + String(normalized.telegram_username).trim();
        }
        if (normalized && normalized.email) {
            return String(normalized.email).split('@', 1)[0];
        }
        return 'Пользователь';
    }

    function resolveInitial(user) {
        var displayName = resolveDisplayName(user).trim();
        return displayName ? displayName.charAt(0).toUpperCase() : '?';
    }

    function setAvatarNode(node, user) {
        if (!node) {
            return;
        }

        if (user && user.avatar_url) {
            node.classList.add('has-image');
            node.innerHTML = "<img src='" + escapeHtml(user.avatar_url) + "' alt='Аватар пользователя'>";
            return;
        }

        node.classList.remove('has-image');
        node.textContent = resolveInitial(user);
    }

    function setUserShell(user) {
        var normalized = normalizePublicUser(user);
        var displayName = resolveDisplayName(normalized);
        var email = isTelegramMiniApp() ? '' : (normalized && normalized.email ? String(normalized.email) : '');

        document.querySelectorAll('.status-user-name').forEach(function (node) {
            node.textContent = displayName;
        });

        document.querySelectorAll('.status-user-email').forEach(function (node) {
            node.textContent = email;
            node.hidden = !email;
        });

        document.querySelectorAll('.avatar-circle').forEach(function (node) {
            setAvatarNode(node, user);
        });
    }

    function normalizePublicUser(user) {
        if (!user || typeof user !== 'object') {
            return user;
        }
        var normalized = Object.assign({}, user);
        if (isSyntheticTelegramEmail(normalized.email)) {
            normalized.email = null;
        }
        return normalized;
    }

    function formatDateTime(isoString) {
        var date = new Date(isoString);
        if (Number.isNaN(date.getTime())) {
            return '';
        }
        return date.toLocaleString('ru-RU', {
            day: '2-digit',
            month: '2-digit',
            year: 'numeric',
            hour: '2-digit',
            minute: '2-digit'
        });
    }

    function parseLocalDate(value) {
        if (value instanceof Date && !Number.isNaN(value.getTime())) {
            return value;
        }
        if (typeof value === 'string' && /^\d{4}-\d{2}-\d{2}$/.test(value)) {
            var parts = value.split('-');
            return new Date(Number(parts[0]), Number(parts[1]) - 1, Number(parts[2]));
        }
        var date = new Date(value);
        return Number.isNaN(date.getTime()) ? new Date() : date;
    }

    function formatShortDateTime(isoString) {
        var date = new Date(isoString);
        if (Number.isNaN(date.getTime())) {
            return '';
        }
        return date.toLocaleString('ru-RU', {
            day: '2-digit',
            month: '2-digit',
            hour: '2-digit',
            minute: '2-digit'
        });
    }

    function goalTypeLabel(value) {
        return GOAL_TYPE_LABELS[value] || value || 'Не указана';
    }

    function levelLabel(value) {
        return LEVEL_LABELS[value] || value || 'Не указан';
    }

    function getPathSegments() {
        return window.location.pathname.split('/').filter(Boolean);
    }

    function renderState(container, title, message, isError) {
        if (!container) {
            return;
        }

        if (!isError) {
            container.innerHTML = [
                "<div class='page-loading-hint' aria-live='polite' aria-label='Загрузка'>",
                "<span class='page-loading-line page-loading-line-primary'></span>",
                "<span class='page-loading-line page-loading-line-secondary'></span>",
                '</div>'
            ].join('');
            return;
        }

        container.innerHTML = [
            "<section class='surface-card'>",
            "<h2>", escapeHtml(title || (isError ? 'Ошибка' : 'Загрузка')), "</h2>",
            "<p class='", isError ? 'inline-message is-error' : 'muted-text', "'>", escapeHtml(message || ''), "</p>",
            '</section>'
        ].join('');
    }

    function loadScript(src) {
        return new Promise(function (resolve, reject) {
            var existing = document.querySelector('script[data-src="' + src + '"]');
            if (existing) {
                if (existing.getAttribute('data-loaded') === '1') {
                    resolve();
                    return;
                }
                existing.addEventListener('load', function () { resolve(); }, { once: true });
                existing.addEventListener('error', function () { reject(new Error('Не удалось загрузить ' + src)); }, { once: true });
                return;
            }

            var script = document.createElement('script');
            script.src = src;
            script.defer = true;
            script.setAttribute('data-src', src);
            script.addEventListener('load', function () {
                script.setAttribute('data-loaded', '1');
                resolve();
            }, { once: true });
            script.addEventListener('error', function () {
                reject(new Error('Не удалось загрузить ' + src));
            }, { once: true });
            document.body.appendChild(script);
        });
    }

    window.KinematicsSite = {
        escapeHtml: escapeHtml,
        fetchJson: fetchJson,
        fetchJsonWithRetry: fetchJsonWithRetry,
        requireJson: requireJson,
        requireJsonWithRetry: requireJsonWithRetry,
        sendJson: sendJson,
        ensureAuthenticatedSession: ensureAuthenticatedSession,
        parseApiError: parseApiError,
        redirectToLogin: redirectToLogin,
        redirectToApp: redirectToApp,
        resolveDisplayName: resolveDisplayName,
        resolveInitial: resolveInitial,
        setUserShell: setUserShell,
        formatDateTime: formatDateTime,
        formatShortDateTime: formatShortDateTime,
        parseLocalDate: parseLocalDate,
        goalTypeLabel: goalTypeLabel,
        levelLabel: levelLabel,
        getPathSegments: getPathSegments,
        renderState: renderState,
        loadScript: loadScript,
        getTelegramUser: getTelegramUser,
        isTelegramMiniApp: isTelegramMiniApp,
        initTelegram: initTelegram,
        authenticateWithTelegram: authenticateWithTelegram,
        linkTelegramIfPossible: linkTelegramIfPossible,
        renderTelegramContext: renderTelegramContext,
        normalizePublicUser: normalizePublicUser,
        safeGetStorage: safeGetStorage,
        safeSetStorage: safeSetStorage,
        safeGetSessionStorage: safeGetSessionStorage,
        safeSetSessionStorage: safeSetSessionStorage,
        safeRemoveSessionStorage: safeRemoveSessionStorage,
        ensureArray: ensureArray,
        ensureObject: ensureObject,
        ensureString: ensureString,
        ensureBoolean: ensureBoolean,
        ensureFiniteNumber: ensureFiniteNumber,
        ensureStringArray: ensureStringArray,
        normalizeSettings: normalizeSettings,
        hasPendingOnboardingReset: hasPendingOnboardingReset,
        clearPendingOnboardingReset: clearPendingOnboardingReset,
        markOnboardingCompletedLocally: markOnboardingCompletedLocally,
        clearOnboardingCompletedLocally: clearOnboardingCompletedLocally,
        hasCompletedOnboardingLocally: hasCompletedOnboardingLocally,
        hasJustCompletedOnboarding: hasJustCompletedOnboarding,
        consumePendingOnboardingReset: consumePendingOnboardingReset,
        fetchOnboardingState: fetchOnboardingState,
        ensureOnboardingAccess: ensureOnboardingAccess,
        prepareOnboardingPage: prepareOnboardingPage,
        resolveAppEntryUrl: resolveAppEntryUrl,
        redirectToOnboarding: redirectToOnboarding,
    };

    document.addEventListener('DOMContentLoaded', function () {
        initTelegram();
        renderTelegramContext();
    });
})();
