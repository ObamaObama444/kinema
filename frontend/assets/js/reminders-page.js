(function () {
    var site = window.KinematicsSite;
    var state = { settings: null, reminders: [] };

    function dayChip(label, value, active) {
        return '<button class="day-pill ' + (active ? 'is-active' : '') + '" type="button" data-reminder-day="' + value + '">' + label + '</button>';
    }

    function renderReminderList() {
        var list = document.getElementById('reminders-list');
        if (!list) {
            return;
        }
        if (!state.reminders.length) {
            list.innerHTML = '<div class="glass-card empty-card">Пока нет правил. Создайте первое напоминание ниже.</div>';
            return;
        }
        list.innerHTML = state.reminders.map(function (item) {
            return [
                '<article class="glass-card reminder-item-card">',
                '<div class="card-head-row"><div><span class="section-kicker">', site.escapeHtml(item.kind), '</span><h3>', site.escapeHtml(item.title), '</h3></div><span class="meta-pill ', item.status === 'needs_link' ? '' : 'is-accent', '">', item.status === 'needs_link' ? 'Нужен link' : (item.enabled ? 'Активно' : 'Выключено'), '</span></div>',
                '<p class="muted-text">', site.escapeHtml(item.message), '</p>',
                '<div class="program-meta-row"><span class="meta-pill">', site.escapeHtml(item.time_local), '</span><span class="meta-pill">', item.days.length ? site.escapeHtml(item.days.join(', ')) : 'ежедневно', '</span></div>',
                '<div class="card-actions-row"><button class="secondary-pill-btn" type="button" data-reminder-toggle="', item.id, '" data-reminder-enabled="', item.enabled ? '1' : '0', '">', item.enabled ? 'Выключить' : 'Включить', '</button><button class="danger-pill-btn" type="button" data-reminder-delete="', item.id, '">Удалить</button></div>',
                '</article>'
            ].join('');
        }).join('');

        document.querySelectorAll('[data-reminder-toggle]').forEach(function (button) {
            button.addEventListener('click', function () {
                var id = Number(button.getAttribute('data-reminder-toggle'));
                var enabled = button.getAttribute('data-reminder-enabled') === '1';
                site.sendJson('/api/profile/reminders/' + id, 'PATCH', { enabled: !enabled }, 'Не удалось обновить напоминание.')
                    .then(loadPage)
                    .catch(function (error) {
                        document.getElementById('reminders-message').textContent = error.message || 'Не удалось обновить напоминание.';
                        document.getElementById('reminders-message').classList.add('is-error');
                    });
            });
        });

        document.querySelectorAll('[data-reminder-delete]').forEach(function (button) {
            button.addEventListener('click', function () {
                var id = Number(button.getAttribute('data-reminder-delete'));
                site.fetchJson('/api/profile/reminders/' + id, { method: 'DELETE' })
                    .then(function (result) {
                        if (!result.response.ok) {
                            throw new Error(site.parseApiError(result.data, 'Не удалось удалить напоминание.'));
                        }
                        loadPage();
                    })
                    .catch(function (error) {
                        document.getElementById('reminders-message').textContent = error.message || 'Не удалось удалить напоминание.';
                        document.getElementById('reminders-message').classList.add('is-error');
                    });
            });
        });
    }

    function render() {
        var root = document.getElementById('page-root');
        var normalizedSettings = site.normalizeSettings(state.settings);
        root.innerHTML = [
            '<section class="glass-card">',
            '<span class="section-kicker">Напоминания</span>',
            '<h3>Telegram delivery</h3>',
            '<p class="muted-text">', normalizedSettings.telegram_linked ? 'Аккаунт Telegram привязан. Напоминания будут уходить прямо в бот.' : 'Сначала откройте mini app из Telegram и дайте ему привязать ваш аккаунт.', '</p>',
            normalizedSettings.telegram_bot_username ? '<p class="muted-text">Бот: @' + site.escapeHtml(normalizedSettings.telegram_bot_username) + '</p>' : '',
            '</section>',
            '<section class="glass-card">',
            '<span class="section-kicker">Новое правило</span>',
            '<form id="reminder-form" class="stack-form" novalidate>',
            '<label class="field"><span>Тип</span><select id="reminder-kind"><option value="workout">workout</option><option value="water">water</option><option value="custom">custom</option></select></label>',
            '<label class="field"><span>Заголовок</span><input id="reminder-title" type="text" maxlength="140" placeholder="Например: Тренировка"></label>',
            '<label class="field"><span>Сообщение</span><textarea id="reminder-message-input" class="textarea-field" maxlength="500" placeholder="Текст, который бот отправит в Telegram"></textarea></label>',
            '<label class="field"><span>Время</span><input id="reminder-time" type="time" value="07:30"></label>',
            '<div class="week-planner-row">',
            dayChip('Пн', 'mon', false), dayChip('Вт', 'tue', false), dayChip('Ср', 'wed', false), dayChip('Чт', 'thu', false), dayChip('Пт', 'fri', false), dayChip('Сб', 'sat', false), dayChip('Вс', 'sun', false),
            '</div>',
            '<button class="primary-pill-btn" type="submit">Сохранить правило</button>',
            '</form>',
            '<p id="reminders-message" class="inline-message" aria-live="polite"></p>',
            '</section>',
            '<section id="reminders-list" class="stack-grid"></section>'
        ].join('');

        var selectedDays = [];
        document.querySelectorAll('[data-reminder-day]').forEach(function (button) {
            button.addEventListener('click', function () {
                var value = button.getAttribute('data-reminder-day');
                var index = selectedDays.indexOf(value);
                if (index >= 0) {
                    selectedDays.splice(index, 1);
                } else {
                    selectedDays.push(value);
                }
                button.classList.toggle('is-active');
            });
        });

        document.getElementById('reminder-form').addEventListener('submit', function (event) {
            event.preventDefault();
            var message = document.getElementById('reminders-message');
            message.textContent = 'Сохраняю правило...';
            message.classList.remove('is-error');
            site.sendJson('/api/profile/reminders', 'POST', {
                kind: document.getElementById('reminder-kind').value,
                title: document.getElementById('reminder-title').value,
                message: document.getElementById('reminder-message-input').value,
                time_local: document.getElementById('reminder-time').value,
                days: selectedDays,
                enabled: true,
                timezone: normalizedSettings.timezone
            }, 'Не удалось сохранить напоминание.')
                .then(loadPage)
                .catch(function (error) {
                    message.textContent = error.message || 'Не удалось сохранить напоминание.';
                    message.classList.add('is-error');
                });
        });

        renderReminderList();
    }

    function loadPage() {
        return Promise.all([
            site.requireJson('/api/profile/settings', null, 'Не удалось загрузить настройки.'),
            site.requireJson('/api/profile/reminders', null, 'Не удалось загрузить напоминания.')
        ]).then(function (results) {
            state.settings = site.normalizeSettings(results[0]);
            state.reminders = site.ensureArray(results[1] && results[1].items);
            render();
        });
    }

    document.addEventListener('DOMContentLoaded', function () {
        var root = document.getElementById('page-root');
        site.renderState(root, 'Загрузка', 'Подключаю напоминания...', false);
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
                site.renderState(root, 'Ошибка', error.message || 'Не удалось загрузить напоминания.', true);
            });
    });
})();
