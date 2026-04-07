(function () {
    var site = window.KinematicsSite;
    var app = window.KinematicsApp;

    var HEIGHT_DEFAULT_CM = 169;
    var WEIGHT_DEFAULT_KG = 79.4;
    var HEIGHT_UNIT_LABELS = { cm: 'cm', ft: 'ft' };
    var WEIGHT_UNIT_LABELS = { kg: 'kg', lb: 'lb' };
    var GENDER_OPTIONS = [
        { value: 'male', label: 'Мужской' },
        { value: 'female', label: 'Женский' },
        { value: 'other_or_skip', label: 'Небинарный' }
    ];

    var state = {
        profile: null,
        settings: null,
        onboarding: null,
        weightHistory: null,
        gender: null,
        heightCm: HEIGHT_DEFAULT_CM,
        weightKg: WEIGHT_DEFAULT_KG,
        savingKey: '',
        message: '',
        messageError: false
    };

    function escapeHtml(value) {
        return site.escapeHtml(value);
    }

    function normalizeHeightScreenUnit(value) {
        return String(value || '').trim().toLowerCase() === 'cm' ? 'cm' : 'ft';
    }

    function normalizeWeightScreenUnit(value) {
        return String(value || '').trim().toLowerCase() === 'lb' ? 'lb' : 'kg';
    }

    function backendHeightUnit(screenUnit) {
        return screenUnit === 'cm' ? 'cm' : 'in';
    }

    function displayHeightFromCm(valueCm, screenUnit) {
        if (valueCm === null || valueCm === undefined || valueCm === '') {
            return null;
        }
        if (screenUnit === 'ft') {
            return Math.round((Number(valueCm) / 30.48) * 10) / 10;
        }
        return Math.round(Number(valueCm));
    }

    function displayHeightToCm(value, screenUnit) {
        if (value === null || value === undefined || value === '') {
            return null;
        }
        if (screenUnit === 'ft') {
            return Math.round(Number(value) * 30.48);
        }
        return Math.round(Number(value));
    }

    function displayWeightFromKg(valueKg, screenUnit) {
        if (valueKg === null || valueKg === undefined || valueKg === '') {
            return null;
        }
        return app.convertWeightFromKg(Number(valueKg), screenUnit);
    }

    function displayWeightToKg(value, screenUnit) {
        if (value === null || value === undefined || value === '') {
            return null;
        }
        return app.convertWeightToKg(Number(value), screenUnit);
    }

    function roundToStep(value, step) {
        var precision = step < 1 ? String(step).split('.')[1].length : 0;
        return Number((Math.round(Number(value) / step) * step).toFixed(precision));
    }

    function clamp(value, min, max) {
        return Math.max(min, Math.min(max, value));
    }

    function setMessage(text, isError) {
        state.message = text || '';
        state.messageError = !!isError;
        var node = document.getElementById('profile-sheet-message');
        if (!node) {
            return;
        }
        node.textContent = state.message;
        node.classList.toggle('is-error', state.messageError);
    }

    function currentHeightScreenUnit() {
        return normalizeHeightScreenUnit(state.settings && state.settings.height_unit);
    }

    function currentWeightScreenUnit() {
        return normalizeWeightScreenUnit(state.settings && state.settings.weight_unit);
    }

    function currentHeightDisplayValue() {
        return displayHeightFromCm(state.heightCm, currentHeightScreenUnit());
    }

    function currentWeightDisplayValue() {
        return displayWeightFromKg(state.weightKg, currentWeightScreenUnit());
    }

    function formatDisplayNumber(value, forceDecimal) {
        if (value === null || value === undefined || Number.isNaN(Number(value))) {
            return '—';
        }
        if (!forceDecimal && Math.abs(Number(value) - Math.round(Number(value))) < 0.001) {
            return String(Math.round(Number(value)));
        }
        return Number(value).toFixed(1);
    }

    function metricConfig(kind, unit) {
        if (kind === 'height') {
            if (unit === 'ft') {
                return { min: 4.6, max: 6.9, step: 0.1, labelStep: 0.5, visibleCount: 31, decimals: 1 };
            }
            return { min: 140, max: 210, step: 1, labelStep: 10, visibleCount: 33, decimals: 0 };
        }
        if (unit === 'lb') {
            return { min: 55, max: 400, step: 0.1, labelStep: 5, visibleCount: 35, decimals: 1 };
        }
        return { min: 25, max: 180, step: 0.1, labelStep: 1, visibleCount: 35, decimals: 1 };
    }

    function isMajorTick(value, labelStep) {
        var quotient = Number(value) / Number(labelStep);
        return Math.abs(quotient - Math.round(quotient)) < 0.001;
    }

    function metricRangeAttributes(kind) {
        var unit = kind === 'height' ? currentHeightScreenUnit() : currentWeightScreenUnit();
        var config = metricConfig(kind, unit);
        var value = kind === 'height' ? currentHeightDisplayValue() : currentWeightDisplayValue();
        return {
            min: config.min,
            max: config.max,
            step: config.step,
            value: clamp(roundToStep(value, config.step), config.min, config.max),
            config: config
        };
    }

    function renderRulerScale(kind) {
        var unit = kind === 'height' ? currentHeightScreenUnit() : currentWeightScreenUnit();
        var attrs = metricRangeAttributes(kind);
        var value = attrs.value;
        var config = attrs.config;
        var count = config.visibleCount;
        var centerIndex = Math.floor(count / 2);
        var start = roundToStep(value - centerIndex * config.step, config.step);
        var cells = [];
        var index;

        for (index = 0; index < count; index += 1) {
            var tickValue = roundToStep(start + index * config.step, config.step);
            var major = isMajorTick(tickValue, config.labelStep);
            var label = major ? formatDisplayNumber(tickValue, config.decimals > 0) : '';
            cells.push(
                '<span class="profile-ruler-cell ' + (major ? 'is-major' : '') + '">' +
                    '<i class="profile-ruler-tick"></i>' +
                    (label ? '<span class="profile-ruler-label">' + escapeHtml(label) + '</span>' : '<span class="profile-ruler-label"></span>') +
                '</span>'
            );
        }

        return '<div class="profile-ruler-scale" style="grid-template-columns: repeat(' + count + ', minmax(0, 1fr));">' + cells.join('') + '</div>';
    }

    function renderMetricBlock(kind, title) {
        var unit = kind === 'height' ? currentHeightScreenUnit() : currentWeightScreenUnit();
        var displayValue = kind === 'height' ? currentHeightDisplayValue() : currentWeightDisplayValue();
        var attrs = metricRangeAttributes(kind);
        var valueText = formatDisplayNumber(displayValue, kind === 'weight' || unit === 'ft');
        var unitLabel = kind === 'height' ? HEIGHT_UNIT_LABELS[unit] : WEIGHT_UNIT_LABELS[unit];
        var inputId = kind === 'height' ? 'profile-height-range' : 'profile-weight-range';
        var prefix = kind === 'height' ? 'profile-height' : 'profile-weight';

        return [
            '<div class="profile-metric-value"><strong id="' + prefix + '-value">' + escapeHtml(valueText) + '</strong><span id="' + prefix + '-unit">' + escapeHtml(unitLabel) + '</span></div>',
            '<div class="profile-ruler-shell">',
            '<div class="profile-ruler-center-line"></div>',
            '<div id="' + prefix + '-scale">' + renderRulerScale(kind) + '</div>',
            '<input id="' + inputId + '" class="profile-ruler-range" type="range" min="' + attrs.min + '" max="' + attrs.max + '" step="' + attrs.step + '" value="' + attrs.value + '">',
            '</div>'
        ].join('');
    }

    function paintMetricVisuals(kind) {
        var prefix = kind === 'height' ? 'profile-height' : 'profile-weight';
        var unit = kind === 'height' ? currentHeightScreenUnit() : currentWeightScreenUnit();
        var displayValue = kind === 'height' ? currentHeightDisplayValue() : currentWeightDisplayValue();
        var attrs = metricRangeAttributes(kind);
        var valueNode = document.getElementById(prefix + '-value');
        var unitNode = document.getElementById(prefix + '-unit');
        var scaleNode = document.getElementById(prefix + '-scale');
        var inputNode = document.getElementById(prefix + '-range');

        if (valueNode) {
            valueNode.textContent = formatDisplayNumber(displayValue, kind === 'weight' || unit === 'ft');
        }
        if (unitNode) {
            unitNode.textContent = kind === 'height' ? HEIGHT_UNIT_LABELS[unit] : WEIGHT_UNIT_LABELS[unit];
        }
        if (scaleNode) {
            scaleNode.innerHTML = renderRulerScale(kind);
        }
        if (inputNode) {
            inputNode.min = String(attrs.min);
            inputNode.max = String(attrs.max);
            inputNode.step = String(attrs.step);
            inputNode.value = String(attrs.value);
        }
    }

    function renderSegmentedButtons(kind, activeValue) {
        if (kind === 'gender') {
            return GENDER_OPTIONS.map(function (option) {
                return '<button class="profile-pill-btn ' + (activeValue === option.value ? 'is-active' : '') + '" type="button" data-gender-value="' + option.value + '">' + escapeHtml(option.label) + '</button>';
            }).join('');
        }
        if (kind === 'height-unit') {
            return ['ft', 'cm'].map(function (unit) {
                return '<button class="profile-unit-btn ' + (activeValue === unit ? 'is-active' : '') + '" type="button" data-height-unit="' + unit + '">' + escapeHtml(HEIGHT_UNIT_LABELS[unit]) + '</button>';
            }).join('');
        }
        return ['lb', 'kg'].map(function (unit) {
            return '<button class="profile-unit-btn ' + (activeValue === unit ? 'is-active' : '') + '" type="button" data-weight-unit="' + unit + '">' + escapeHtml(WEIGHT_UNIT_LABELS[unit]) + '</button>';
        }).join('');
    }

    function syncButtonLabel() {
        return state.profile && state.profile.telegram_linked ? 'Готово' : 'Войти';
    }

    function renderPage() {
        var root = document.getElementById('page-root');
        root.innerHTML = [
            '<section class="profile-sheet">',
            '<header class="profile-sheet-head">',
            '<button id="profile-sheet-back" class="profile-sheet-back" type="button" aria-label="Назад">',
            '<svg viewBox="0 0 24 24" fill="none"><path d="M14.5 5L8 11.5L14.5 18" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"></path></svg>',
            '</button>',
            '<h1 class="profile-sheet-title">Профиль</h1>',
            '<span class="profile-sheet-spacer"></span>',
            '</header>',
            '<section class="profile-sync-row">',
            '<h2 class="profile-sheet-label profile-sync-title">Синхронизировать Аккаунт</h2>',
            '<button id="profile-sync-btn" class="profile-sync-btn" type="button">' + escapeHtml(syncButtonLabel()) + '</button>',
            '</section>',
            '<section class="profile-sheet-section">',
            '<h2 class="profile-sheet-label">Пол</h2>',
            '<div id="profile-gender-row" class="profile-pill-row">' + renderSegmentedButtons('gender', state.gender) + '</div>',
            '</section>',
            '<section class="profile-sheet-section">',
            '<div class="profile-section-head">',
            '<h2 class="profile-sheet-label">Рост</h2>',
            '<div id="profile-height-units" class="profile-unit-toggle">' + renderSegmentedButtons('height-unit', currentHeightScreenUnit()) + '</div>',
            '</div>',
            '<div id="profile-height-metric">' + renderMetricBlock('height', 'Рост') + '</div>',
            '</section>',
            '<section class="profile-sheet-section">',
            '<div class="profile-section-head">',
            '<h2 class="profile-sheet-label">Текущий Вес</h2>',
            '<div id="profile-weight-units" class="profile-unit-toggle">' + renderSegmentedButtons('weight-unit', currentWeightScreenUnit()) + '</div>',
            '</div>',
            '<div id="profile-weight-metric">' + renderMetricBlock('weight', 'Текущий Вес') + '</div>',
            '</section>',
            '<p id="profile-sheet-message" class="profile-sheet-message ' + (state.messageError ? 'is-error' : '') + '" aria-live="polite">' + escapeHtml(state.message) + '</p>',
            '</section>'
        ].join('');
    }

    function refreshMetricBlock(kind) {
        var container = document.getElementById(kind === 'height' ? 'profile-height-metric' : 'profile-weight-metric');
        if (!container) {
            return;
        }
        container.innerHTML = renderMetricBlock(kind);
        bindMetricControl(kind);
    }

    function patchOnboarding(data) {
        return site.sendJson('/api/onboarding', 'PATCH', data, 'Не удалось обновить onboarding.');
    }

    function currentProfilePayload(nextHeightCm) {
        return {
            height_cm: nextHeightCm,
            weight_kg: state.profile && state.profile.weight_kg != null
                ? Number(state.profile.weight_kg)
                : (state.weightKg != null ? Math.round(Number(state.weightKg)) : null),
            age: state.profile ? state.profile.age : null,
            level: state.profile ? state.profile.level : null
        };
    }

    function saveGender(value) {
        var previous = state.gender;
        state.gender = value;
        renderPage();
        bindPage();
        setMessage('Сохраняю пол…', false);
        return patchOnboarding({ gender: value })
            .then(function (response) {
                state.onboarding = response;
                state.gender = response.data.gender || value;
                setMessage('Пол обновлён.', false);
                renderPage();
                bindPage();
            })
            .catch(function (error) {
                state.gender = previous;
                setMessage(error.message || 'Не удалось обновить пол.', true);
                renderPage();
                bindPage();
            });
    }

    function saveHeight() {
        var heightCm = state.heightCm;
        var previousHeightCm = state.profile && state.profile.height_cm
            ? Number(state.profile.height_cm)
            : ((state.onboarding && state.onboarding.data && state.onboarding.data.height_cm) ? Number(state.onboarding.data.height_cm) : HEIGHT_DEFAULT_CM);
        if (!heightCm) {
            return Promise.resolve();
        }
        state.savingKey = 'height';
        setMessage('Сохраняю рост…', false);
        return site.sendJson('/api/profile', 'PUT', currentProfilePayload(heightCm), 'Не удалось сохранить рост.')
            .then(function (profile) {
                state.profile = profile;
                site.setUserShell(profile);
                return patchOnboarding({ height_cm: heightCm }).catch(function () {
                    return null;
                });
            })
            .then(function (onboarding) {
                if (onboarding) {
                    state.onboarding = onboarding;
                }
                state.savingKey = '';
                setMessage('Рост обновлён.', false);
            })
            .catch(function (error) {
                state.savingKey = '';
                state.heightCm = previousHeightCm;
                setMessage(error.message || 'Не удалось сохранить рост.', true);
                refreshMetricBlock('height');
            });
    }

    function saveWeight() {
        var weightKg = Math.round(Number(state.weightKg) * 10) / 10;
        if (!weightKg || Number.isNaN(weightKg)) {
            return Promise.resolve();
        }
        state.savingKey = 'weight';
        setMessage('Обновляю вес…', false);
        return site.sendJson('/api/profile/weight-history', 'POST', { weight_kg: weightKg }, 'Не удалось обновить вес.')
            .then(function (weightHistory) {
                state.weightHistory = weightHistory;
                state.weightKg = weightHistory.latest_weight_kg || weightKg;
                if (state.profile) {
                    state.profile.weight_kg = Math.round(state.weightKg);
                }
                return patchOnboarding({ current_weight_kg: state.weightKg }).catch(function () {
                    return null;
                });
            })
            .then(function (onboarding) {
                if (onboarding) {
                    state.onboarding = onboarding;
                }
                state.savingKey = '';
                setMessage('Вес обновлён.', false);
                refreshMetricBlock('weight');
            })
            .catch(function (error) {
                state.savingKey = '';
                setMessage(error.message || 'Не удалось обновить вес.', true);
                if (state.weightHistory && state.weightHistory.latest_weight_kg != null) {
                    state.weightKg = state.weightHistory.latest_weight_kg;
                }
                refreshMetricBlock('weight');
            });
    }

    function saveSettingsPatch(payload, successText, errorText, revert) {
        setMessage('Сохраняю настройки…', false);
        return site.sendJson('/api/profile/settings', 'PATCH', payload, errorText)
            .then(function (settings) {
                state.settings = settings;
                setMessage(successText, false);
                renderPage();
                bindPage();
            })
            .catch(function (error) {
                if (typeof revert === 'function') {
                    revert();
                }
                setMessage(error.message || errorText, true);
                renderPage();
                bindPage();
            });
    }

    function handleSyncAccount() {
        if (state.profile && state.profile.telegram_linked) {
            setMessage('Аккаунт уже синхронизирован.', false);
            return;
        }
        if (site.isTelegramMiniApp()) {
            setMessage('Синхронизирую аккаунт…', false);
            site.linkTelegramIfPossible()
                .then(function () {
                    return Promise.all([
                        site.requireJson('/api/profile', null, 'Не удалось обновить профиль.'),
                        site.requireJson('/api/profile/settings', null, 'Не удалось обновить настройки.')
                    ]);
                })
                .then(function (results) {
                    state.profile = results[0];
                    state.settings = results[1];
                    site.setUserShell(state.profile);
                    setMessage(state.profile.telegram_linked ? 'Аккаунт синхронизирован.' : 'Откройте экран в Telegram, чтобы завершить синхронизацию.', !state.profile.telegram_linked);
                    renderPage();
                    bindPage();
                })
                .catch(function (error) {
                    setMessage(error.message || 'Не удалось синхронизировать аккаунт.', true);
                });
            return;
        }
        if (state.settings && state.settings.telegram_bot_username) {
            window.location.assign('https://t.me/' + state.settings.telegram_bot_username);
            return;
        }
        site.redirectToLogin();
    }

    function bindMetricControl(kind) {
        var input = document.getElementById(kind === 'height' ? 'profile-height-range' : 'profile-weight-range');
        if (!input) {
            return;
        }
        input.addEventListener('input', function () {
            var raw = Number(input.value);
            if (kind === 'height') {
                state.heightCm = displayHeightToCm(raw, currentHeightScreenUnit());
            } else {
                state.weightKg = displayWeightToKg(raw, currentWeightScreenUnit());
            }
            paintMetricVisuals(kind);
        });
        input.addEventListener('change', function () {
            if (kind === 'height') {
                saveHeight();
            } else {
                saveWeight();
            }
        });
    }

    function bindPage() {
        var back = document.getElementById('profile-sheet-back');
        if (back) {
            back.addEventListener('click', function () {
                if (window.history.length > 1) {
                    window.history.back();
                    return;
                }
                window.location.assign('/app/profile');
            });
        }

        var syncButton = document.getElementById('profile-sync-btn');
        if (syncButton) {
            syncButton.addEventListener('click', handleSyncAccount);
        }

        document.querySelectorAll('[data-gender-value]').forEach(function (button) {
            button.addEventListener('click', function () {
                var value = button.getAttribute('data-gender-value');
                if (!value || value === state.gender) {
                    return;
                }
                saveGender(value);
            });
        });

        document.querySelectorAll('[data-height-unit]').forEach(function (button) {
            button.addEventListener('click', function () {
                var value = button.getAttribute('data-height-unit');
                if (!value || value === currentHeightScreenUnit()) {
                    return;
                }
                var previous = state.settings.height_unit;
                state.settings.height_unit = backendHeightUnit(value);
                saveSettingsPatch(
                    { height_unit: backendHeightUnit(value) },
                    'Единицы роста обновлены.',
                    'Не удалось обновить единицы роста.',
                    function () {
                        state.settings.height_unit = previous;
                    }
                );
            });
        });

        document.querySelectorAll('[data-weight-unit]').forEach(function (button) {
            button.addEventListener('click', function () {
                var value = button.getAttribute('data-weight-unit');
                if (!value || value === currentWeightScreenUnit()) {
                    return;
                }
                var previous = state.settings.weight_unit;
                state.settings.weight_unit = value;
                saveSettingsPatch(
                    { weight_unit: value },
                    'Единицы веса обновлены.',
                    'Не удалось обновить единицы веса.',
                    function () {
                        state.settings.weight_unit = previous;
                    }
                );
            });
        });

        bindMetricControl('height');
        bindMetricControl('weight');
    }

    function bootstrapState(results) {
        state.profile = results[0];
        state.settings = site.normalizeSettings(results[1]);
        state.onboarding = results[2];
        state.weightHistory = results[3];

        var onboardingData = state.onboarding && state.onboarding.data ? state.onboarding.data : {};
        state.gender = onboardingData.gender || null;
        state.heightCm = state.profile.height_cm || onboardingData.height_cm || HEIGHT_DEFAULT_CM;
        state.weightKg = state.weightHistory.latest_weight_kg || onboardingData.current_weight_kg || state.profile.weight_kg || WEIGHT_DEFAULT_KG;
    }

    document.addEventListener('DOMContentLoaded', function () {
        var root = document.getElementById('page-root');
        site.renderState(root, 'Загрузка', 'Подготавливаю профиль…', false);
        site.ensureOnboardingAccess()
            .then(function () {
                return Promise.all([
                    site.requireJson('/api/profile', null, 'Не удалось загрузить профиль.'),
                    site.requireJson('/api/profile/settings', null, 'Не удалось загрузить настройки.'),
                    site.requireJson('/api/onboarding', null, 'Не удалось загрузить onboarding.'),
                    site.requireJson('/api/profile/weight-history', null, 'Не удалось загрузить историю веса.')
                ]);
            })
            .then(function (results) {
                bootstrapState(results);
                site.setUserShell(state.profile);
                renderPage();
                bindPage();
            })
            .catch(function (error) {
                if (error && (error.code === 'AUTH_REQUIRED' || error.code === 'ONBOARDING_REQUIRED')) {
                    return;
                }
                site.renderState(root, 'Ошибка', error.message || 'Не удалось загрузить профиль.', true);
            });
    });
})();
