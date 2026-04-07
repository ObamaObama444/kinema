(function () {
    var site = window.KinematicsSite;
    var app = window.KinematicsApp;
    var state = { settings: null };

    function segmented(name, current, items) {
        return '<div class="segmented-tabs">' + items.map(function (item) {
            return '<button class="segmented-pill ' + (current === item.value ? 'is-active' : '') + '" type="button" data-setting-name="' + name + '" data-setting-value="' + item.value + '">' + item.label + '</button>';
        }).join('') + '</div>';
    }

    function renderHeader(title) {
        return [
            '<header class="settings-sheet-head">',
            '<button id="settings-general-back" class="settings-back-btn" type="button" aria-label="Назад">',
            '<svg viewBox="0 0 24 24" fill="none"><path d="M14.5 5L8 11.5L14.5 18" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"></path></svg>',
            '</button>',
            '<h1 class="settings-sheet-title">' + site.escapeHtml(title) + '</h1>',
            '<span class="settings-sheet-spacer"></span>',
            '</header>'
        ].join('');
    }

    function render() {
        var root = document.getElementById('page-root');
        state.settings = site.normalizeSettings(state.settings);
        root.innerHTML = [
            '<section class="settings-detail-sheet">',
            renderHeader('Общие Настройки'),
            '<section class="glass-card settings-detail-card">',
            '<span class="section-kicker">Интерфейс</span>',
            '<h3>Оформление и язык</h3>',
            '<div class="settings-row"><span>Тема</span>', segmented('theme_preference', state.settings.theme_preference, [{ value: 'system', label: 'Система' }, { value: 'light', label: 'Светлая' }, { value: 'dark', label: 'Тёмная' }]), '</div>',
            '<div class="settings-row"><span>Язык</span>', segmented('language', state.settings.language, [{ value: 'ru', label: 'Рус' }, { value: 'en', label: 'Eng' }]), '</div>',
            '<div class="settings-row"><span>Вес</span>', segmented('weight_unit', state.settings.weight_unit, [{ value: 'kg', label: 'kg' }, { value: 'lb', label: 'lb' }]), '</div>',
            '<div class="settings-row"><span>Рост</span>', segmented('height_unit', state.settings.height_unit, [{ value: 'cm', label: 'cm' }, { value: 'in', label: 'in' }]), '</div>',
            '<label class="field"><span>Timezone</span><input id="settings-timezone" type="text" value="', site.escapeHtml(state.settings.timezone || 'UTC'), '" placeholder="Europe/Samara"></label>',
            '<button id="save-timezone-btn" class="primary-pill-btn" type="button">Сохранить timezone</button>',
            '<p id="settings-message" class="inline-message" aria-live="polite"></p>',
            '</section>',
            '<section class="glass-card settings-detail-card">',
            '<span class="section-kicker">Telegram</span>',
            '<h3>', state.settings.telegram_linked ? 'Привязка активна' : 'Требуется привязка', '</h3>',
            '<p class="muted-text">', state.settings.telegram_linked ? 'Сообщения будут отправляться на подключённый Telegram account.' : 'Откройте mini app в Telegram, чтобы система могла отправлять напоминания в чат.', '</p>',
            state.settings.telegram_username ? '<p class="muted-text">@' + site.escapeHtml(state.settings.telegram_username) + '</p>' : '',
            '<button id="telegram-link-btn" class="secondary-pill-btn" type="button">Обновить привязку</button>',
            '</section>',
            '</section>'
        ].join('');

        var back = document.getElementById('settings-general-back');
        if (back) {
            back.addEventListener('click', function () {
                if (window.history.length > 1) {
                    window.history.back();
                    return;
                }
                window.location.assign('/app/profile/settings');
            });
        }

        document.querySelectorAll('[data-setting-name]').forEach(function (button) {
            button.addEventListener('click', function () {
                var payload = {};
                payload[button.getAttribute('data-setting-name')] = button.getAttribute('data-setting-value');
                site.sendJson('/api/profile/settings', 'PATCH', payload, 'Не удалось сохранить настройки.')
                    .then(function (data) {
                        state.settings = data;
                        if (payload.theme_preference) {
                            app.applyThemePreference(payload.theme_preference);
                        }
                        render();
                    })
                    .catch(function (error) {
                        document.getElementById('settings-message').textContent = error.message || 'Не удалось сохранить настройки.';
                        document.getElementById('settings-message').classList.add('is-error');
                    });
            });
        });

        document.getElementById('save-timezone-btn').addEventListener('click', function () {
            var message = document.getElementById('settings-message');
            message.textContent = 'Сохраняю timezone...';
            message.classList.remove('is-error');
            site.sendJson('/api/profile/settings', 'PATCH', { timezone: document.getElementById('settings-timezone').value }, 'Не удалось сохранить настройки.')
                .then(function (data) {
                    state.settings = data;
                    render();
                })
                .catch(function (error) {
                    message.textContent = error.message || 'Не удалось сохранить настройки.';
                    message.classList.add('is-error');
                });
        });

        document.getElementById('telegram-link-btn').addEventListener('click', function () {
            site.linkTelegramIfPossible().then(loadPage);
        });
    }

    function loadPage() {
        return site.requireJson('/api/profile/settings', null, 'Не удалось загрузить настройки.')
            .then(function (data) {
                state.settings = site.normalizeSettings(data);
                render();
            });
    }

    document.addEventListener('DOMContentLoaded', function () {
        var root = document.getElementById('page-root');
        site.renderState(root, 'Загрузка', 'Подгружаю настройки...', false);
        site.ensureOnboardingAccess()
            .then(function () {
                return site.requireJson('/api/profile', null, 'Не удалось загрузить профиль.');
            })
            .then(function (profile) {
                site.setUserShell(profile);
                return loadPage();
            })
            .catch(function (error) {
                if (error && (error.code === 'AUTH_REQUIRED' || error.code === 'ONBOARDING_REQUIRED')) {
                    return;
                }
                site.renderState(root, 'Ошибка', error.message || 'Не удалось загрузить настройки.', true);
            });
    });
})();
