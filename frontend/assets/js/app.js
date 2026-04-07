(function () {
    var site = window.KinematicsSite;
    var THEME_STORAGE_KEY = 'kinematics-theme-preference';

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

    function normalizeThemePreference(value) {
        var normalized = String(value || '').trim().toLowerCase();
        if (normalized === 'light' || normalized === 'dark' || normalized === 'system') {
            return normalized;
        }
        if (normalized === 'day') {
            return 'light';
        }
        if (normalized === 'night') {
            return 'dark';
        }
        return 'system';
    }

    function resolveEffectiveTheme(preference) {
        var pref = normalizeThemePreference(preference);
        if (pref === 'system') {
            return window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light';
        }
        return pref;
    }

    function themeLabel(preference) {
        if (preference === 'light') {
            return 'Светлая';
        }
        if (preference === 'dark') {
            return 'Тёмная';
        }
        return 'Системная';
    }

    function applyThemePreference(preference) {
        var normalized = normalizeThemePreference(preference);
        var effective = resolveEffectiveTheme(normalized);
        document.documentElement.setAttribute('data-theme-preference', normalized);
        document.documentElement.setAttribute('data-theme', effective);
        safeSetStorage(THEME_STORAGE_KEY, normalized);

        var toggle = document.getElementById('theme-toggle');
        if (toggle) {
            toggle.textContent = 'Тема: ' + themeLabel(normalized);
        }
    }

    function cycleThemePreference() {
        var current = normalizeThemePreference(document.documentElement.getAttribute('data-theme-preference') || safeGetStorage(THEME_STORAGE_KEY) || 'system');
        if (current === 'system') {
            return 'light';
        }
        if (current === 'light') {
            return 'dark';
        }
        return 'system';
    }

    function initThemeControls() {
        applyThemePreference(safeGetStorage(THEME_STORAGE_KEY) || 'system');
        var toggle = document.getElementById('theme-toggle');
        if (!toggle) {
            return;
        }
        toggle.addEventListener('click', function () {
            applyThemePreference(cycleThemePreference());
        });
    }

    function initSystemThemeListener() {
        if (!window.matchMedia) {
            return;
        }
        var media = window.matchMedia('(prefers-color-scheme: dark)');
        var syncTheme = function () {
            if (normalizeThemePreference(document.documentElement.getAttribute('data-theme-preference')) === 'system') {
                applyThemePreference('system');
            }
        };
        if (typeof media.addEventListener === 'function') {
            media.addEventListener('change', syncTheme);
        } else if (typeof media.addListener === 'function') {
            media.addListener(syncTheme);
        }
    }

    function initLogoutButtons() {
        document.querySelectorAll('[data-logout]').forEach(function (button) {
            button.addEventListener('click', function () {
                button.disabled = true;
                site.fetchJson('/api/auth/logout', { method: 'POST' })
                    .finally(function () {
                        site.redirectToLogin();
                    });
            });
        });
    }

    function initRouterButtons() {
        document.querySelectorAll('[data-open-route]').forEach(function (node) {
            node.addEventListener('click', function () {
                var href = node.getAttribute('data-open-route');
                if (href) {
                    window.location.assign(href);
                }
            });
        });
    }

    function convertWeightFromKg(valueKg, unit) {
        if (valueKg === null || valueKg === undefined || valueKg === '') {
            return null;
        }
        if (normalizeWeightUnit(unit) === 'lb') {
            return Math.round((Number(valueKg) * 2.2046226218) * 10) / 10;
        }
        return Math.round(Number(valueKg) * 10) / 10;
    }

    function convertWeightToKg(value, unit) {
        if (value === null || value === undefined || value === '') {
            return null;
        }
        if (normalizeWeightUnit(unit) === 'lb') {
            return Math.round((Number(value) / 2.2046226218) * 10) / 10;
        }
        return Math.round(Number(value) * 10) / 10;
    }

    function convertHeightFromCm(valueCm, unit) {
        if (valueCm === null || valueCm === undefined || valueCm === '') {
            return null;
        }
        if (normalizeHeightUnit(unit) === 'in') {
            return Math.round((Number(valueCm) / 2.54) * 10) / 10;
        }
        return Math.round(Number(valueCm));
    }

    function convertHeightToCm(value, unit) {
        if (value === null || value === undefined || value === '') {
            return null;
        }
        if (normalizeHeightUnit(unit) === 'in') {
            return Math.round(Number(value) * 2.54);
        }
        return Math.round(Number(value));
    }

    function normalizeWeightUnit(unit) {
        return String(unit || '').trim().toLowerCase() === 'lb' ? 'lb' : 'kg';
    }

    function normalizeHeightUnit(unit) {
        return String(unit || '').trim().toLowerCase() === 'in' ? 'in' : 'cm';
    }

    function formatWeight(valueKg, unit) {
        var normalizedUnit = normalizeWeightUnit(unit);
        var value = convertWeightFromKg(valueKg, normalizedUnit);
        if (value === null) {
            return '—';
        }
        return value.toFixed(normalizedUnit === 'lb' ? 1 : 1) + ' ' + normalizedUnit;
    }

    function formatHeight(valueCm, unit) {
        var normalizedUnit = normalizeHeightUnit(unit);
        var value = convertHeightFromCm(valueCm, normalizedUnit);
        if (value === null) {
            return '—';
        }
        return (normalizedUnit === 'in' ? value.toFixed(1) : String(Math.round(value))) + ' ' + normalizedUnit;
    }

    function hydrateThemeFromSettings() {
        if (!window.location.pathname.startsWith('/app') || window.location.pathname === '/app/onboarding') {
            return;
        }
        site.fetchJson('/api/profile/settings')
            .then(function (result) {
                if (!result.response.ok) {
                    return;
                }
                applyThemePreference(result.data.theme_preference || 'system');
            })
            .catch(function () {
                return;
            });
    }

    function initTelegramLinking() {
        if (!window.location.pathname.startsWith('/app')) {
            return;
        }
        site.linkTelegramIfPossible();
    }

    window.KinematicsApp = {
        applyThemePreference: applyThemePreference,
        normalizeThemePreference: normalizeThemePreference,
        normalizeWeightUnit: normalizeWeightUnit,
        normalizeHeightUnit: normalizeHeightUnit,
        convertWeightFromKg: convertWeightFromKg,
        convertWeightToKg: convertWeightToKg,
        convertHeightFromCm: convertHeightFromCm,
        convertHeightToCm: convertHeightToCm,
        formatWeight: formatWeight,
        formatHeight: formatHeight
    };

    document.addEventListener('DOMContentLoaded', function () {
        initThemeControls();
        initSystemThemeListener();
        initLogoutButtons();
        initRouterButtons();
        hydrateThemeFromSettings();
        initTelegramLinking();
    });
})();
