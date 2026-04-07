(function () {
    var site = window.KinematicsSite;
    var app = window.KinematicsApp;
    var state = { settings: null, summary: null };

    function normalizeWeightSummary(summary) {
        var source = site.ensureObject(summary);
        return {
            entries: site.ensureArray(source.entries),
            latest_weight_kg: site.ensureFiniteNumber(source.latest_weight_kg),
            initial_weight_kg: site.ensureFiniteNumber(source.initial_weight_kg),
            target_weight_kg: site.ensureFiniteNumber(source.target_weight_kg),
            previous_weight_kg: site.ensureFiniteNumber(source.previous_weight_kg),
            latest_days_ago: site.ensureFiniteNumber(source.latest_days_ago),
            bmi: site.ensureFiniteNumber(source.bmi),
            bmi_label: site.ensureString(source.bmi_label, 'нет данных'),
            can_add_now: source.can_add_now === true,
            next_allowed_at: source.next_allowed_at ? String(source.next_allowed_at) : '',
            last_seven_days_delta_kg: site.ensureFiniteNumber(source.last_seven_days_delta_kg) || 0,
            last_thirty_days_delta_kg: site.ensureFiniteNumber(source.last_thirty_days_delta_kg) || 0
        };
    }

    function dateLabel(value) {
        var date = new Date(value);
        if (Number.isNaN(date.getTime())) {
            return '';
        }
        return date.toLocaleDateString('ru-RU', { day: 'numeric', month: 'short' });
    }

    function renderWeightChart(entries, unit) {
        var normalizedEntries = site.ensureArray(entries).map(function (item) {
            return {
                recorded_on_local_date: item && item.recorded_on_local_date,
                weight_kg: site.ensureFiniteNumber(item && item.weight_kg)
            };
        }).filter(function (item) {
            return item.weight_kg != null;
        });

        if (!normalizedEntries.length) {
            return '<div class="mini-chart-empty">Добавьте первое обновление веса.</div>';
        }
        var points = normalizedEntries.map(function (item) {
            return { date: item.recorded_on_local_date, weight_kg: item.weight_kg };
        });
        var width = 320;
        var height = 156;
        var padding = 14;
        var values = points.map(function (item) { return Number(item.weight_kg); });
        var min = Math.min.apply(null, values) - 0.8;
        var max = Math.max.apply(null, values) + 0.8;
        var range = Math.max(1, max - min);

        function x(index) {
            return padding + ((width - padding * 2) * index / Math.max(1, points.length - 1));
        }

        function y(value) {
            return height - padding - ((Number(value) - min) / range) * (height - padding * 2);
        }

        var polyline = points.map(function (item, index) { return x(index) + ',' + y(item.weight_kg); }).join(' ');
        return [
            '<svg class="mini-chart" viewBox="0 0 ', width, ' ', height, '">',
            '<defs><linearGradient id="weightPageGradient" x1="0%" x2="100%" y1="0%" y2="0%"><stop offset="0%" stop-color="#95e6b3"></stop><stop offset="100%" stop-color="#1ba567"></stop></linearGradient></defs>',
            '<polyline fill="none" stroke="url(#weightPageGradient)" stroke-width="5" stroke-linecap="round" stroke-linejoin="round" points="', polyline, '"></polyline>',
            points.map(function (item, index) {
                return '<circle cx="' + x(index) + '" cy="' + y(item.weight_kg) + '" r="' + (index === points.length - 1 ? 6 : 4) + '" fill="#fff" stroke="#22b573" stroke-width="3"></circle>';
            }).join(''),
            '</svg>',
            '<div class="mini-chart-labels">',
            points.slice(-4).map(function (item) {
                return '<span><strong>' + site.escapeHtml(app.formatWeight(item.weight_kg, unit)) + '</strong><small>' + site.escapeHtml(dateLabel(item.date)) + '</small></span>';
            }).join(''),
            '</div>'
        ].join('');
    }

    function render() {
        var summary = normalizeWeightSummary(state.summary);
        var settings = site.normalizeSettings(state.settings);
        var root = document.getElementById('page-root');
        root.innerHTML = [
            '<section class="glass-card">',
            '<div class="section-head"><div><span class="section-kicker">Вес</span><h3>', summary.latest_weight_kg == null ? 'Пока без записи' : app.formatWeight(summary.latest_weight_kg, settings.weight_unit), '</h3></div><span class="meta-pill">ИМТ ', summary.bmi == null ? '—' : site.escapeHtml(String(summary.bmi)), '</span></div>',
            renderWeightChart(summary.entries, settings.weight_unit),
            '<div class="weight-inline-stats">',
            '<article><span>Старт</span><strong>', summary.initial_weight_kg == null ? '—' : app.formatWeight(summary.initial_weight_kg, settings.weight_unit), '</strong></article>',
            '<article><span>7 дней</span><strong>', site.escapeHtml(String(summary.last_seven_days_delta_kg.toFixed(1))), '</strong></article>',
            '<article><span>30 дней</span><strong>', site.escapeHtml(String(summary.last_thirty_days_delta_kg.toFixed(1))), '</strong></article>',
            '</div>',
            '<p class="muted-text">Категория ИМТ: ', site.escapeHtml(summary.bmi_label || 'нет данных'), '.</p>',
            '</section>',
            '<section class="glass-card">',
            '<span class="section-kicker">Обновить вес</span>',
            summary.can_add_now
                ? '<div class="inline-weight-form"><input id="weight-page-input" class="mini-input" type="number" step="0.1" min="25" max="350" placeholder="Новый вес в ' + settings.weight_unit + '"><button id="weight-page-submit" class="primary-pill-btn" type="button">Сохранить</button></div>'
                : '<p class="muted-text">Следующее обновление веса будет доступно после ' + site.escapeHtml(new Date(summary.next_allowed_at).toLocaleString('ru-RU', { hour: '2-digit', minute: '2-digit', day: '2-digit', month: '2-digit' })) + '.</p>',
            '<p id="weight-page-message" class="inline-message" aria-live="polite"></p>',
            '</section>',
            '<section class="stack-grid">',
            summary.entries.slice().reverse().map(function (item) {
                return '<article class="glass-card"><div class="card-head-row"><h3>' + site.escapeHtml(app.formatWeight(item.weight_kg, settings.weight_unit)) + '</h3><span class="meta-pill">' + site.escapeHtml(dateLabel(item.recorded_on_local_date)) + '</span></div><p class="muted-text">Добавлено в timezone ' + site.escapeHtml(item.timezone) + '.</p></article>';
            }).join(''),
            '</section>'
        ].join('');

        var submit = document.getElementById('weight-page-submit');
        var input = document.getElementById('weight-page-input');
        var message = document.getElementById('weight-page-message');
        if (submit && input && message) {
            submit.addEventListener('click', function () {
                submit.disabled = true;
                message.textContent = 'Сохраняю вес...';
                message.classList.remove('is-error');
                site.sendJson('/api/profile/weight-history', 'POST', {
                    weight_kg: app.convertWeightToKg(input.value, settings.weight_unit)
                }, 'Не удалось сохранить вес.')
                    .then(loadPage)
                    .catch(function (error) {
                        message.textContent = error.message || 'Не удалось сохранить вес.';
                        message.classList.add('is-error');
                        submit.disabled = false;
                    });
            });
        }
    }

    function loadPage() {
        return Promise.all([
            site.requireJson('/api/profile/settings', null, 'Не удалось загрузить настройки.'),
            site.requireJson('/api/profile/weight-history', null, 'Не удалось загрузить вес.')
        ]).then(function (results) {
            state.settings = site.normalizeSettings(results[0]);
            state.summary = normalizeWeightSummary(results[1]);
            render();
        });
    }

    document.addEventListener('DOMContentLoaded', function () {
        var root = document.getElementById('page-root');
        site.renderState(root, 'Загрузка', 'Собираю график веса...', false);
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
                site.renderState(root, 'Ошибка', error.message || 'Не удалось загрузить вес.', true);
            });
    });
})();
