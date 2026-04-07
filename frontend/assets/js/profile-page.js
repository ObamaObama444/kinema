(function () {
    var site = window.KinematicsSite;
    var app = window.KinematicsApp;
    var activeRouteToken = 0;
    var MONTH_NAMES_RU = [
        'января', 'февраля', 'марта', 'апреля', 'мая', 'июня',
        'июля', 'августа', 'сентября', 'октября', 'ноября', 'декабря'
    ];
    var WEEKDAY_HEADERS = ['п', 'в', 'с', 'ч', 'п', 'с', 'в'];
    var TRAINING_DAY_TO_JS = {
        mon: 1,
        tue: 2,
        wed: 3,
        thu: 4,
        fri: 5,
        sat: 6,
        sun: 0
    };
    var TRAINING_DAY_FALLBACKS = {
        1: ['wed'],
        2: ['tue', 'fri'],
        3: ['mon', 'wed', 'fri'],
        4: ['mon', 'tue', 'thu', 'sat'],
        5: ['mon', 'tue', 'wed', 'fri', 'sat'],
        6: ['mon', 'tue', 'wed', 'thu', 'sat', 'sun']
    };
    var state = {
        profile: null,
        settings: null,
        progress: null,
        onboarding: null,
        weight: null,
        monthKey: null,
        weightFormOpen: false,
        weightDraft: '',
        calendarMessage: '',
        calendarError: false,
        weightMessage: '',
        weightError: false,
        pendingDate: '',
        pendingWeight: false
    };

    var ICONS = {
        avatar: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="8" r="3.6"></circle><path d="M5.5 18.2c1.9-3.3 4.3-5 6.5-5s4.6 1.7 6.5 5"></path></svg>',
        settings: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><path d="M12 3.9 18.6 7v10L12 20.1 5.4 17V7L12 3.9Z"></path><circle cx="12" cy="12" r="2.6"></circle></svg>',
        profile: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="8" r="3.5"></circle><path d="M5.5 19c1.8-3.2 4.1-4.8 6.5-4.8s4.7 1.6 6.5 4.8"></path></svg>',
        favorite: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><path d="M12 19.4 5.6 13c-1.6-1.6-1.6-4.1 0-5.7 1.4-1.4 3.6-1.6 5.2-.4l1.2.9 1.2-.9c1.6-1.2 3.8-1 5.2.4 1.6 1.6 1.6 4.1 0 5.7L12 19.4Z"></path></svg>',
        chevronLeft: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"><path d="m14.5 5-7 7 7 7"></path></svg>',
        chevronRight: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"><path d="m9.5 5 7 7-7 7"></path></svg>'
    };

    function currentRouteToken() {
        return window.KinematicsShell ? Number(window.KinematicsShell.routeToken || 0) : 0;
    }

    function isActiveRoute(routeToken) {
        return activeRouteToken === routeToken && currentRouteToken() === routeToken;
    }

    function escapeHtml(value) {
        return site.escapeHtml(value);
    }

    function ensureObject(value) {
        return site.ensureObject(value);
    }

    function ensureArray(value) {
        return site.ensureArray(value);
    }

    function ensureNumber(value) {
        return site.ensureFiniteNumber(value);
    }

    function displayName(profile) {
        return site.resolveDisplayName(profile);
    }

    function avatarMarkup(profile) {
        if (profile && profile.avatar_url) {
            return '<img src="' + escapeHtml(profile.avatar_url) + '" alt="' + escapeHtml(displayName(profile)) + '">';
        }
        return ICONS.avatar;
    }

    function monthLabel(monthKey) {
        if (!monthKey) {
            return '';
        }
        var parts = String(monthKey).split('-');
        if (parts.length !== 2) {
            return monthKey;
        }
        var monthIndex = Number(parts[1]) - 1;
        var year = parts[0];
        return (MONTH_NAMES_RU[monthIndex] || '') + ' ' + year;
    }

    function monthDate(monthKey) {
        if (!monthKey) {
            return new Date();
        }
        var parts = String(monthKey).split('-');
        return new Date(Number(parts[0]), Number(parts[1]) - 1, 1);
    }

    function shiftMonthKey(monthKey, delta) {
        var base = monthDate(monthKey);
        base.setMonth(base.getMonth() + delta, 1);
        return base.getFullYear() + '-' + String(base.getMonth() + 1).padStart(2, '0');
    }

    function weekdayOffset(dateValue) {
        var date = new Date(dateValue);
        if (Number.isNaN(date.getTime())) {
            return 0;
        }
        return (date.getDay() + 6) % 7;
    }

    function formatDelta(value) {
        var normalized = ensureNumber(value);
        if (normalized == null) {
            return '0.0';
        }
        return normalized.toFixed(1);
    }

    function formatWeightValue(valueKg, unit) {
        var formatted = app.formatWeight(valueKg, unit);
        return formatted === '—' ? '—' : escapeHtml(formatted);
    }

    function weightInputLabel(unit) {
        return app.normalizeWeightUnit(unit) === 'lb' ? 'lb' : 'kg';
    }

    function normalizeProgress(progress) {
        var source = ensureObject(progress);
        return {
            month_key: site.ensureString(source.month_key, ''),
            month_label: site.ensureString(source.month_label, ''),
            calendar_days: ensureArray(source.calendar_days),
            completed_this_month: ensureNumber(source.completed_this_month) || 0
        };
    }

    function normalizeWeight(weight) {
        var source = ensureObject(weight);
        return {
            entries: ensureArray(source.entries),
            latest_weight_kg: ensureNumber(source.latest_weight_kg),
            initial_weight_kg: ensureNumber(source.initial_weight_kg),
            target_weight_kg: ensureNumber(source.target_weight_kg),
            previous_weight_kg: ensureNumber(source.previous_weight_kg),
            latest_days_ago: ensureNumber(source.latest_days_ago),
            bmi: ensureNumber(source.bmi),
            bmi_label: site.ensureString(source.bmi_label, ''),
            can_add_now: source.can_add_now === true,
            next_allowed_at: source.next_allowed_at ? String(source.next_allowed_at) : '',
            latest_entry_created_at: source.latest_entry_created_at ? String(source.latest_entry_created_at) : '',
            hours_until_next_entry: ensureNumber(source.hours_until_next_entry),
            last_seven_days_delta_kg: ensureNumber(source.last_seven_days_delta_kg) || 0,
            last_thirty_days_delta_kg: ensureNumber(source.last_thirty_days_delta_kg) || 0
        };
    }

    function normalizeOnboarding(onboarding) {
        var source = ensureObject(onboarding);
        return {
            data: ensureObject(source.data)
        };
    }

    function normalizeCalendarDay(day) {
        var source = ensureObject(day);
        return {
            date: source.date ? String(source.date) : '',
            day_number: ensureNumber(source.day_number) || 0,
            weekday_short: site.ensureString(source.weekday_short, ''),
            is_planned: source.is_planned === true,
            is_completed: source.is_completed === true,
            is_manual_completed: source.is_manual_completed === true,
            is_session_completed: source.is_session_completed === true,
            is_today: source.is_today === true,
            can_toggle: source.can_toggle === true
        };
    }

    function resolvedTrainingDays(onboarding) {
        var data = normalizeOnboarding(onboarding).data;
        var explicitDays = site.ensureStringArray(data.training_days).filter(function (item) {
            return Object.prototype.hasOwnProperty.call(TRAINING_DAY_TO_JS, item);
        });
        var frequency = ensureNumber(data.training_frequency) || 0;

        if (explicitDays.length) {
            return explicitDays;
        }

        return TRAINING_DAY_FALLBACKS[frequency] ? TRAINING_DAY_FALLBACKS[frequency].slice() : [];
    }

    function buildFallbackCalendarDays(monthKey, onboarding) {
        var plannedDays = resolvedTrainingDays(onboarding);
        var plannedWeekdays = {};
        var today = new Date();
        var monthStart = monthDate(monthKey);
        var current = new Date(monthStart.getFullYear(), monthStart.getMonth(), 1);
        var lastDay = new Date(monthStart.getFullYear(), monthStart.getMonth() + 1, 0).getDate();
        var result = [];

        plannedDays.forEach(function (item) {
            plannedWeekdays[TRAINING_DAY_TO_JS[item]] = true;
        });

        while (current.getDate() <= lastDay && current.getMonth() === monthStart.getMonth()) {
            result.push({
                date: current.getFullYear() + '-' + String(current.getMonth() + 1).padStart(2, '0') + '-' + String(current.getDate()).padStart(2, '0'),
                day_number: current.getDate(),
                weekday_short: '',
                is_planned: plannedWeekdays[current.getDay()] === true,
                is_completed: false,
                is_manual_completed: false,
                is_session_completed: false,
                is_today: current.toDateString() === today.toDateString(),
                can_toggle: current <= today
            });
            current = new Date(current.getFullYear(), current.getMonth(), current.getDate() + 1);
        }

        return result;
    }

    function resolvedCalendarDays(progress, onboarding) {
        var plannedDays = resolvedTrainingDays(onboarding);
        var plannedWeekdays = {};
        var days = ensureArray(progress.calendar_days).map(normalizeCalendarDay);

        plannedDays.forEach(function (item) {
            plannedWeekdays[TRAINING_DAY_TO_JS[item]] = true;
        });

        if (!days.length) {
            days = buildFallbackCalendarDays(progress.month_key || state.monthKey || '', onboarding);
        }

        if (!plannedDays.length) {
            return days;
        }

        return days.map(function (day) {
            var currentDate = parseLocalDate(day.date);
            return Object.assign({}, day, {
                is_planned: day.is_planned || plannedWeekdays[currentDate.getDay()] === true
            });
        });
    }

    function currentMonthEntries(entries, monthKey) {
        var monthPrefix = String(monthKey || '') + '-';
        var filtered = entries.filter(function (item) {
            return String(item && item.recorded_on_local_date || '').indexOf(monthPrefix) === 0;
        });
        return filtered.length ? filtered : entries.slice(-8);
    }

    function chartSeries(entries, monthKey, unit) {
        var filtered = currentMonthEntries(entries, monthKey).map(function (item, index) {
            return {
                xIndex: index,
                recorded_on_local_date: String(item.recorded_on_local_date || ''),
                dayNumber: Number(String(item.recorded_on_local_date || '').slice(-2)),
                weight: app.convertWeightFromKg(item.weight_kg, unit)
            };
        }).filter(function (item) {
            return ensureNumber(item.weight) != null;
        });
        return filtered;
    }

    function renderWeightChart(weight, settings, monthKey) {
        var unit = settings.weight_unit;
        var points = chartSeries(weight.entries, monthKey, unit);
        var targetWeight = weight.target_weight_kg == null ? null : app.convertWeightFromKg(weight.target_weight_kg, unit);
        if (!points.length) {
            return '<div class="me-weight-empty">Добавьте первое обновление веса.</div>';
        }

        var width = 332;
        var height = 188;
        var left = 42;
        var right = 12;
        var top = 24;
        var bottom = 30;
        var values = points.map(function (item) { return Number(item.weight); });
        if (targetWeight != null) {
            values.push(Number(targetWeight));
        }
        var minValue = Math.floor((Math.min.apply(null, values) - 1) * 2) / 2;
        var maxValue = Math.ceil((Math.max.apply(null, values) + 1) * 2) / 2;
        var range = Math.max(1, maxValue - minValue);
        var latestPoint = points[points.length - 1];
        var yTicks = [maxValue, minValue + (range / 2), minValue];
        var xLabels = [1, 5, 10, 15, 20, 25].filter(function (day) {
            return day <= 31;
        });

        function xPosition(index) {
            return left + ((width - left - right) * index / Math.max(1, points.length - 1));
        }

        function yPosition(value) {
            return top + ((maxValue - Number(value)) / range) * (height - top - bottom);
        }

        function bubbleMarkup(point) {
            var cx = xPosition(point.xIndex);
            var cy = yPosition(point.weight);
            return [
                '<g transform="translate(', cx - 20, ' ', cy - 26, ')">',
                '<rect width="40" height="24" rx="12" fill="#5c6270"></rect>',
                '<text x="20" y="16" text-anchor="middle" fill="#ffffff" font-size="12" font-weight="800">', escapeHtml(point.weight.toFixed(1)), '</text>',
                '</g>'
            ].join('');
        }

        return [
            '<div class="me-weight-chart-topline">',
            '<span>', escapeHtml(monthLabel(monthKey).split(' ')[0] || ''), '</span>',
            '</div>',
            '<svg class="me-weight-chart" viewBox="0 0 ', width, ' ', height, '" aria-hidden="true">',
            yTicks.map(function (tick) {
                var y = yPosition(tick);
                return '<g><line x1="' + left + '" y1="' + y + '" x2="' + (width - right) + '" y2="' + y + '" stroke="#e6e8ed" stroke-dasharray="2 4"></line><text x="0" y="' + (y + 4) + '" fill="#8b92a0" font-size="10">' + escapeHtml(tick.toFixed(1)) + ' ' + escapeHtml(unit) + '</text></g>';
            }).join(''),
            targetWeight == null ? '' : '<line x1="' + left + '" y1="' + yPosition(targetWeight) + '" x2="' + (width - right) + '" y2="' + yPosition(targetWeight) + '" stroke="#19cf7a" stroke-width="1.6" stroke-dasharray="4 4"></line>',
            targetWeight == null ? '' : '<text x="' + (left + 16) + '" y="' + (yPosition(targetWeight) - 8) + '" fill="#19cf7a" font-size="11" font-weight="700">Цель</text>',
            '<polyline points="', points.map(function (point) {
                return xPosition(point.xIndex) + ',' + yPosition(point.weight);
            }).join(' '), '" fill="none" stroke="#9ca3af" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"></polyline>',
            points.map(function (point, index) {
                var cx = xPosition(point.xIndex);
                var cy = yPosition(point.weight);
                var isLatest = index === points.length - 1;
                return [
                    '<circle cx="', cx, '" cy="', cy, '" r="', isLatest ? '4.6' : '3.2', '" fill="#ffffff" stroke="', isLatest ? '#19cf7a' : '#9ca3af', '" stroke-width="2"></circle>',
                    isLatest ? '<circle cx="' + cx + '" cy="' + (cy + 12) + '" r="3.2" fill="#19cf7a"></circle>' : ''
                ].join('');
            }).join(''),
            bubbleMarkup(latestPoint),
            '</svg>',
            '<div class="me-weight-chart-axis">',
            xLabels.map(function (label) {
                return '<span>' + label + '</span>';
            }).join(''),
            '</div>'
        ].join('');
    }

    function renderCalendar(progress, onboarding) {
        var days = resolvedCalendarDays(progress, onboarding);
        if (!days.length) {
            return '<div class="me-calendar-empty">Нет данных по месяцу.</div>';
        }

        var leading = weekdayOffset(days[0].date);
        var cells = [];
        var index;
        for (index = 0; index < leading; index += 1) {
            cells.push('<div class="me-calendar-cell me-calendar-cell--ghost" aria-hidden="true"></div>');
        }

        days.forEach(function (day) {
            var classes = ['me-calendar-cell'];
            if (day.is_planned) {
                classes.push('is-planned');
            }
            if (day.is_completed) {
                classes.push('is-completed');
            }
            if (day.is_today) {
                classes.push('is-today');
            }
            if (day.can_toggle) {
                classes.push('is-toggleable');
            }
            if (day.is_manual_completed) {
                classes.push('is-manual');
            }

            cells.push([
                '<button class="', classes.join(' '), '" type="button" data-checkin-date="', escapeHtml(day.date), '" ', day.can_toggle ? '' : 'disabled', '>',
                day.is_completed
                    ? '<span class="me-calendar-badge">' + escapeHtml(String(day.day_number)) + '</span>'
                    : '<span class="me-calendar-ring"></span><span class="me-calendar-number">' + escapeHtml(String(day.day_number)) + '</span>',
                '</button>'
            ].join(''));
        });

        return [
            '<div class="me-calendar-head">',
            '<button class="me-calendar-nav" type="button" data-calendar-shift="-1" aria-label="Предыдущий месяц">', ICONS.chevronLeft, '</button>',
            '<div class="me-calendar-title">', escapeHtml(monthLabel(progress.month_key)), '</div>',
            '<button class="me-calendar-nav" type="button" data-calendar-shift="1" aria-label="Следующий месяц">', ICONS.chevronRight, '</button>',
            '</div>',
            '<div class="me-calendar-weekdays">',
            WEEKDAY_HEADERS.map(function (label) {
                return '<span>' + escapeHtml(label) + '</span>';
            }).join(''),
            '</div>',
            '<div class="me-calendar-grid">',
            cells.join(''),
            '</div>'
        ].join('');
    }

    function render() {
        var root = document.getElementById('page-root');
        var profile = ensureObject(state.profile);
        var settings = site.normalizeSettings(state.settings || {});
        var progress = normalizeProgress(state.progress || {});
        var onboarding = normalizeOnboarding(state.onboarding || {});
        var weight = normalizeWeight(state.weight || {});
        var nextAllowedText = weight.next_allowed_at
            ? new Date(weight.next_allowed_at).toLocaleString('ru-RU', { hour: '2-digit', minute: '2-digit', day: '2-digit', month: '2-digit' })
            : '';

        root.innerHTML = [
            '<section class="me-screen">',
            '<header class="me-topbar">',
            '<div class="me-identity">',
            '<div class="me-avatar">', avatarMarkup(profile), '</div>',
            '<div class="me-identity-copy"><h1>', escapeHtml(displayName(profile)), '</h1></div>',
            '</div>',
            '<a class="me-settings-link" href="/app/profile/settings">', ICONS.settings, '<span>Настройки</span></a>',
            '</header>',
            '<section class="me-action-grid">',
            '<a class="me-action-card" href="/app/profile/edit">', ICONS.profile, '<span>Профиль</span></a>',
            '<a class="me-action-card" href="/app/profile/favorites">', ICONS.favorite, '<span>Избранное</span></a>',
            '</section>',
            '<section class="me-card me-calendar-card">',
            '<div class="me-card-title">Календарь</div>',
            renderCalendar(progress, onboarding),
            state.calendarMessage ? '<p class="me-inline-message ' + (state.calendarError ? 'is-error' : '') + '">' + escapeHtml(state.calendarMessage) + '</p>' : '',
            '</section>',
            '<section class="me-card me-weight-card">',
            '<div class="me-weight-head">',
            '<div class="me-card-title">Вес</div>',
            '<button id="me-weight-toggle" class="me-weight-update" type="button">+ Обновить</button>',
            '</div>',
            '<div class="me-weight-summary">',
            '<div class="me-weight-current"><strong>', weight.latest_weight_kg == null ? '—' : escapeHtml(app.convertWeightFromKg(weight.latest_weight_kg, settings.weight_unit).toFixed(1)), '</strong><span>', escapeHtml(weightInputLabel(settings.weight_unit)), '</span></div>',
            '<div class="me-weight-target"><span>Цель</span><strong>', weight.target_weight_kg == null ? '—' : escapeHtml(app.convertWeightFromKg(weight.target_weight_kg, settings.weight_unit).toFixed(1)) + ' ' + escapeHtml(weightInputLabel(settings.weight_unit)), '</strong></div>',
            '</div>',
            renderWeightChart(weight, settings, progress.month_key),
            '<div class="me-weight-stats">',
            '<article><span>Последние семь дней</span><strong>', escapeHtml(formatDelta(weight.last_seven_days_delta_kg)), '</strong></article>',
            '<article><span>Последние тридцать дней</span><strong>', escapeHtml(formatDelta(weight.last_thirty_days_delta_kg)), '</strong></article>',
            '<article><span>ИМТ</span><strong class="me-bmi-value"><i></i>', weight.bmi == null ? '—' : escapeHtml(String(weight.bmi)), '</strong></article>',
            '</div>',
            state.weightFormOpen ? [
                '<div class="me-weight-editor">',
                weight.can_add_now
                    ? '<div class="me-weight-form"><input id="me-weight-input" class="me-weight-input" type="number" step="0.1" min="25" max="350" placeholder="Введите вес в ' + escapeHtml(weightInputLabel(settings.weight_unit)) + '" value="' + escapeHtml(state.weightDraft) + '"><button id="me-weight-submit" class="me-weight-submit" type="button" ' + (state.pendingWeight ? 'disabled' : '') + '>Сохранить</button></div>'
                    : '<p class="me-inline-note">Вес можно обновить снова после ' + escapeHtml(nextAllowedText || 'истечения cooldown') + '.</p>',
                state.weightMessage ? '<p class="me-inline-message ' + (state.weightError ? 'is-error' : '') + '">' + escapeHtml(state.weightMessage) + '</p>' : '',
                '</div>'
            ].join('') : '',
            '</section>',
            '</section>'
        ].join('');

        bindEvents();
    }

    function bindEvents() {
        document.querySelectorAll('[data-calendar-shift]').forEach(function (button) {
            button.addEventListener('click', function () {
                loadProgressMonth(shiftMonthKey(state.monthKey, Number(button.getAttribute('data-calendar-shift') || '0')));
            });
        });

        document.querySelectorAll('[data-checkin-date]').forEach(function (button) {
            button.addEventListener('click', function () {
                if (button.disabled || state.pendingDate) {
                    return;
                }
                toggleCheckin(button.getAttribute('data-checkin-date'));
            });
        });

        var weightToggle = document.getElementById('me-weight-toggle');
        if (weightToggle) {
            weightToggle.addEventListener('click', function () {
                state.weightFormOpen = !state.weightFormOpen;
                state.weightMessage = '';
                state.weightError = false;
                render();
            });
        }

        var weightSubmit = document.getElementById('me-weight-submit');
        var weightInput = document.getElementById('me-weight-input');
        if (weightSubmit && weightInput) {
            weightInput.addEventListener('input', function () {
                state.weightDraft = weightInput.value;
            });
            weightSubmit.addEventListener('click', function () {
                submitWeight(weightInput.value);
            });
        }
    }

    function loadProgressMonth(monthKey) {
        state.calendarMessage = '';
        state.calendarError = false;
        return site.requireJson('/api/progress/summary?month=' + encodeURIComponent(monthKey), null, 'Не удалось загрузить календарь.')
            .then(function (result) {
                state.progress = result;
                state.monthKey = result.month_key;
                render();
            })
            .catch(function (error) {
                state.calendarMessage = error.message || 'Не удалось переключить месяц.';
                state.calendarError = true;
                render();
            });
    }

    function toggleCheckin(dateValue) {
        state.pendingDate = dateValue;
        state.calendarMessage = '';
        state.calendarError = false;
        var day = normalizeProgress(state.progress).calendar_days.find(function (item) {
            return item.date === dateValue;
        });
        var shouldComplete = !(day && day.is_completed);
        site.sendJson('/api/progress/checkins', 'POST', {
            date: dateValue,
            completed: shouldComplete
        }, 'Не удалось обновить отметку тренировки.')
            .then(function (result) {
                state.progress = result;
                state.monthKey = result.month_key;
                state.pendingDate = '';
                render();
            })
            .catch(function (error) {
                state.pendingDate = '';
                state.calendarMessage = error.message || 'Не удалось обновить отметку тренировки.';
                state.calendarError = true;
                render();
            });
    }

    function submitWeight(rawValue) {
        var settings = site.normalizeSettings(state.settings || {});
        var valueKg = app.convertWeightToKg(rawValue, settings.weight_unit);
        if (!valueKg || Number.isNaN(Number(valueKg))) {
            state.weightMessage = 'Введите корректный вес.';
            state.weightError = true;
            render();
            return;
        }
        state.pendingWeight = true;
        state.weightMessage = 'Сохраняю вес...';
        state.weightError = false;
        render();
        site.sendJson('/api/profile/weight-history', 'POST', { weight_kg: valueKg }, 'Не удалось сохранить вес.')
            .then(function (result) {
                state.weight = result;
                state.pendingWeight = false;
                state.weightFormOpen = false;
                state.weightDraft = '';
                state.weightMessage = '';
                state.weightError = false;
                render();
            })
            .catch(function (error) {
                state.pendingWeight = false;
                state.weightMessage = error.message || 'Не удалось сохранить вес.';
                state.weightError = true;
                render();
            });
    }

    function loadPage() {
        var progressUrl = state.monthKey
            ? '/api/progress/summary?month=' + encodeURIComponent(state.monthKey)
            : '/api/progress/summary';
        return Promise.all([
            site.requireJson('/api/profile', null, 'Не удалось загрузить профиль.'),
            site.requireJson('/api/profile/settings', null, 'Не удалось загрузить настройки.'),
            site.requireJson(progressUrl, null, 'Не удалось загрузить календарь.'),
            site.requireJson('/api/profile/weight-history', null, 'Не удалось загрузить вес.'),
            site.requireJson('/api/onboarding', null, 'Не удалось загрузить onboarding.').catch(function () {
                return { data: {} };
            })
        ]).then(function (results) {
            state.profile = results[0];
            state.settings = results[1];
            state.progress = results[2];
            state.weight = results[3];
            state.onboarding = results[4];
            state.monthKey = results[2].month_key;
            if (currentRouteToken() !== activeRouteToken) {
                return;
            }
            site.setUserShell(results[0]);
            render();
        });
    }

    function mountProfileHubPage() {
        var routeToken = currentRouteToken();
        var root = document.getElementById('page-root');
        activeRouteToken = routeToken;
        site.renderState(root, 'Загрузка', 'Собираю вкладку Я...', false);
        site.ensureOnboardingAccess()
            .then(loadPage)
            .catch(function (error) {
                if (!isActiveRoute(routeToken)) {
                    return;
                }
                if (error && (error.code === 'AUTH_REQUIRED' || error.code === 'ONBOARDING_REQUIRED')) {
                    return;
                }
                site.renderState(root, 'Ошибка', error.message || 'Не удалось загрузить вкладку Я.', true);
            });
    }

    window.KinematicsPages = window.KinematicsPages || {};
    window.KinematicsPages.me = mountProfileHubPage;

    document.addEventListener('DOMContentLoaded', mountProfileHubPage);
})();
