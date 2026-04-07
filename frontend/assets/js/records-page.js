(function () {
    var site = window.KinematicsSite;
    var activeRouteToken = 0;
    var PICKER_ITEM_HEIGHT = 58;
    var state = {
        profile: null,
        summary: null,
        sheet: null,
        notice: '',
        waterSaving: false
    };
    var MONTHS_GENITIVE_RU = [
        'января',
        'февраля',
        'марта',
        'апреля',
        'мая',
        'июня',
        'июля',
        'августа',
        'сентября',
        'октября',
        'ноября',
        'декабря'
    ];

    function currentRouteToken() {
        return window.KinematicsShell ? Number(window.KinematicsShell.routeToken || 0) : 0;
    }

    function isActiveRoute(routeToken) {
        return activeRouteToken === routeToken && currentRouteToken() === routeToken;
    }

    function clamp(value, min, max) {
        return Math.min(max, Math.max(min, Number(value) || 0));
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

    function formatPageDate(value) {
        var date = parseLocalDate(value);
        return MONTHS_GENITIVE_RU[date.getMonth()] + ' ' + date.getDate() + ', ' + date.getFullYear();
    }

    function normalizePulsePoints(points) {
        return site.ensureArray(points).map(function (item) {
            return {
                id: site.ensureFiniteNumber(item && item.id) || 0,
                bpm: site.ensureFiniteNumber(item && item.bpm),
                hour: clamp(item && item.hour, 0, 23),
                minute: clamp(item && item.minute, 0, 59),
                recorded_at: item && item.recorded_at ? String(item.recorded_at) : ''
            };
        }).filter(function (item) {
            return item.bpm != null;
        });
    }

    function normalizeBloodPressurePoints(points) {
        return site.ensureArray(points).map(function (item) {
            return {
                id: site.ensureFiniteNumber(item && item.id) || 0,
                systolic: site.ensureFiniteNumber(item && item.systolic),
                diastolic: site.ensureFiniteNumber(item && item.diastolic),
                hour: clamp(item && item.hour, 0, 23),
                minute: clamp(item && item.minute, 0, 59),
                recorded_at: item && item.recorded_at ? String(item.recorded_at) : ''
            };
        }).filter(function (item) {
            return item.systolic != null && item.diastolic != null;
        });
    }

    function normalizeSummary(summary) {
        var source = site.ensureObject(summary);
        return {
            local_date: source.local_date ? String(source.local_date) : '',
            steps_goal: clamp(source.steps_goal, 0, 50000),
            water_goal_glasses: clamp(source.water_goal_glasses, 0, 20),
            water_consumed_glasses: clamp(source.water_consumed_glasses, 0, 20),
            latest_pulse_bpm: site.ensureFiniteNumber(source.latest_pulse_bpm),
            latest_systolic: site.ensureFiniteNumber(source.latest_systolic),
            latest_diastolic: site.ensureFiniteNumber(source.latest_diastolic),
            pulse_points: normalizePulsePoints(source.pulse_points),
            blood_pressure_points: normalizeBloodPressurePoints(source.blood_pressure_points)
        };
    }

    function goalConfig(metric) {
        if (metric === 'water') {
            return {
                key: 'water',
                title: 'Пейте Воду',
                icon: '💧',
                unit: 'Стаканов',
                cardValueLabel: '',
                openLabel: 'Задать',
                max: 12,
                step: 1,
                emptyDefault: 7,
                accentClass: 'is-water',
                noteHtml: 'Большинству людей нужно <span>8 стаканов</span><br>(≈2000 мл) в день.'
            };
        }

        return {
            key: 'steps',
            title: 'Шаги',
            icon: '🚶',
            unit: 'Шагов',
            cardValueLabel: '',
            openLabel: 'Задать',
            max: 30000,
            step: 500,
            emptyDefault: 6000,
            accentClass: 'is-steps',
            noteHtml: 'Комфортная дневная цель для большинства людей<br>начинается с <span>6000 шагов</span>.'
        };
    }

    function ensureSheetMessage(sheet) {
        if (!sheet || !sheet.message) {
            return '';
        }
        return '<p class="records-sheet-message ' + (sheet.isError ? 'is-error' : '') + '">' + site.escapeHtml(sheet.message) + '</p>';
    }

    function renderGoalArc(displayValue, progressValue, max, accentClass, icon) {
        var progress = max > 0 ? Math.min(100, Math.max(0, (Number(progressValue) || 0) / max * 100)) : 0;
        var displayText = displayValue == null ? '—' : String(displayValue);
        return [
            '<div class="records-goal-arc ', accentClass, '">',
            '<svg viewBox="0 0 220 136" aria-hidden="true">',
            '<path class="records-goal-arc-track" d="M26 112 A84 84 0 0 1 194 112" pathLength="100"></path>',
            '<path class="records-goal-arc-progress" d="M26 112 A84 84 0 0 1 194 112" pathLength="100" style="stroke-dasharray:', progress, ' 100;"></path>',
            '</svg>',
            '<div class="records-goal-arc-center">',
            '<div class="records-goal-emoji">', icon, '</div>',
            '<strong>', site.escapeHtml(displayText), '</strong>',
            '</div>',
            '</div>'
        ].join('');
    }

    function renderGoalCard(metric, value) {
        var config = goalConfig(metric);
        return [
            '<article class="records-card records-card-goal ', config.accentClass, '">',
            '<div class="records-card-head">',
            '<h2>', config.title, '</h2>',
            '<span class="records-card-chevron" aria-hidden="true">',
            '<svg viewBox="0 0 24 24"><path d="M9 5l7 7-7 7"></path></svg>',
            '</span>',
            '</div>',
            renderGoalArc(value, value, config.max, config.accentClass, config.icon),
            '<button class="records-open-link" type="button" data-open-goal="', metric, '">',
            '<span>', config.openLabel, '</span>',
            '</button>',
            '</article>'
        ].join('');
    }

    function renderWaterCard(summary) {
        var config = goalConfig('water');
        var goal = clamp(summary.water_goal_glasses, 0, config.max);
        var consumed = clamp(summary.water_consumed_glasses, 0, Math.max(goal, 0));

        if (goal <= 0) {
            return renderGoalCard('water', 0);
        }

        return [
            '<article class="records-card records-card-goal records-card-water-progress ', config.accentClass, '">',
            '<button class="records-card-head records-card-head-button" type="button" data-open-goal="water">',
            '<h2>', config.title, '</h2>',
            '<span class="records-card-chevron" aria-hidden="true">',
            '<svg viewBox="0 0 24 24"><path d="M9 5l7 7-7 7"></path></svg>',
            '</span>',
            '</button>',
            renderGoalArc(consumed, consumed, Math.max(goal, 1), config.accentClass, config.icon),
            '<div class="records-water-progress-total">/', site.escapeHtml(String(goal)), ' СТАКАНОВ</div>',
            '<div class="records-water-adjustments">',
            '<button class="records-water-adjust" type="button" data-water-adjust="-1"', consumed <= 0 || state.waterSaving ? ' disabled' : '', '>−</button>',
            '<button class="records-water-adjust is-plus" type="button" data-water-adjust="1"', consumed >= goal || state.waterSaving ? ' disabled' : '', '>+</button>',
            '</div>',
            '</article>'
        ].join('');
    }

    function renderPulseChart(points) {
        return renderMetricChart({
            type: 'pulse',
            points: points,
            min: 0,
            max: 200,
            yLabels: [200, 100, 0],
            lineColor: '#15b85a',
            pointColor: '#15b85a'
        });
    }

    function renderBloodPressureChart(points) {
        return renderMetricChart({
            type: 'blood-pressure',
            points: points,
            min: 60,
            max: 120,
            yLabels: [120, 100, 80, 60],
            lineColor: '#18181b',
            pointColor: '#18181b'
        });
    }

    function renderMetricChart(config) {
        var width = 240;
        var height = 124;
        var plotLeft = 12;
        var plotTop = 12;
        var plotWidth = 150;
        var plotHeight = 68;
        var xTicks = [0, 6, 12, 18];
        var xPositions = xTicks.map(function (tick) {
            return plotLeft + plotWidth * (tick / 18);
        });

        function toX(item) {
            var totalHours = Math.min(18, Math.max(0, Number(item.hour) + Number(item.minute || 0) / 60));
            return plotLeft + plotWidth * (totalHours / 18);
        }

        function toY(value) {
            var normalized = clamp(value, config.min, config.max);
            var ratio = (normalized - config.min) / Math.max(1, config.max - config.min);
            return plotTop + plotHeight - ratio * plotHeight;
        }

        function renderGrid() {
            var yLines = config.yLabels.map(function (label) {
                return toY(label);
            });
            return [
                '<g class="records-chart-grid">',
                xPositions.map(function (position) {
                    return '<line x1="' + position + '" y1="' + plotTop + '" x2="' + position + '" y2="' + (plotTop + plotHeight) + '"></line>';
                }).join(''),
                yLines.map(function (position) {
                    return '<line x1="' + plotLeft + '" y1="' + position + '" x2="' + (plotLeft + plotWidth) + '" y2="' + position + '"></line>';
                }).join(''),
                '</g>'
            ].join('');
        }

        function renderPulseSeries() {
            if (!config.points.length) {
                return '';
            }
            var polyline = config.points.map(function (item) {
                return toX(item) + ',' + toY(item.bpm);
            }).join(' ');
            return [
                '<polyline class="records-chart-line" style="stroke:', config.lineColor, '" points="', polyline, '"></polyline>',
                config.points.map(function (item) {
                    return '<circle class="records-chart-point" cx="' + toX(item) + '" cy="' + toY(item.bpm) + '" r="3.6" style="fill:' + config.pointColor + '"></circle>';
                }).join('')
            ].join('');
        }

        function renderBloodPressureSeries() {
            if (!config.points.length) {
                return '';
            }
            var systolicLine = config.points.map(function (item) {
                return toX(item) + ',' + toY(item.systolic);
            }).join(' ');
            var diastolicLine = config.points.map(function (item) {
                return toX(item) + ',' + toY(item.diastolic);
            }).join(' ');
            return [
                '<polyline class="records-chart-line records-chart-line-systolic" points="', systolicLine, '"></polyline>',
                '<polyline class="records-chart-line records-chart-line-diastolic" points="', diastolicLine, '"></polyline>',
                config.points.map(function (item) {
                    return '<circle class="records-chart-point records-chart-point-systolic" cx="' + toX(item) + '" cy="' + toY(item.systolic) + '" r="3.4"></circle>';
                }).join(''),
                config.points.map(function (item) {
                    return '<circle class="records-chart-point records-chart-point-diastolic" cx="' + toX(item) + '" cy="' + toY(item.diastolic) + '" r="3.2"></circle>';
                }).join('')
            ].join('');
        }

        return [
            '<svg class="records-chart" viewBox="0 0 ', width, ' ', height, '" aria-hidden="true">',
            renderGrid(),
            config.type === 'blood-pressure' ? renderBloodPressureSeries() : renderPulseSeries(),
            '<g class="records-chart-axis-x">',
            xTicks.map(function (tick, index) {
                return '<text x="' + xPositions[index] + '" y="' + (plotTop + plotHeight + 28) + '">' + tick + '</text>';
            }).join(''),
            '</g>',
            '<g class="records-chart-axis-y">',
            config.yLabels.map(function (tick) {
                return '<text x="' + (plotLeft + plotWidth + 12) + '" y="' + (toY(tick) + 4) + '">' + tick + '</text>';
            }).join(''),
            '</g>',
            '</svg>'
        ].join('');
    }

    function renderPulseCard(summary) {
        return [
            '<article class="records-card records-card-vital" id="records-vitals-anchor">',
            '<div class="records-card-head"><h2>Частота Пульс</h2></div>',
            '<div class="records-vital-value">',
            summary.latest_pulse_bpm == null ? '—' : site.escapeHtml(String(summary.latest_pulse_bpm)),
            '<span>bpm</span>',
            '</div>',
            renderPulseChart(summary.pulse_points),
            '<button class="records-vital-button" type="button" data-open-pulse-sheet>ИЗМЕРЕНИЕ</button>',
            '</article>'
        ].join('');
    }

    function renderBloodPressureCard(summary) {
        return [
            '<article class="records-card records-card-vital records-card-pressure">',
            '<div class="records-card-head"><h2>Кровяное Давление</h2></div>',
            '<div class="records-vital-value records-vital-value-pressure">',
            summary.latest_systolic == null || summary.latest_diastolic == null
                ? '—/—'
                : site.escapeHtml(String(summary.latest_systolic)) + '/' + site.escapeHtml(String(summary.latest_diastolic)),
            '<span>мм рт. ст.</span>',
            '</div>',
            renderBloodPressureChart(summary.blood_pressure_points),
            '<button class="records-vital-button" type="button" data-open-pressure-sheet>ЗАПИСАТЬ</button>',
            '</article>'
        ].join('');
    }

    function renderQuickSheetNotice(sheet) {
        if (!sheet || !sheet.message) {
            return '<p class="records-sheet-placeholder" aria-hidden="true"></p>';
        }
        return ensureSheetMessage(sheet);
    }

    function renderGoalSheet(sheet) {
        var config = goalConfig(sheet.metric);
        return [
            '<div class="records-sheet-layer">',
            '<button class="records-sheet-backdrop" type="button" data-close-sheet aria-label="Закрыть"></button>',
            '<section class="records-sheet records-sheet-goal" role="dialog" aria-modal="true">',
            '<div class="records-sheet-handle" aria-hidden="true"></div>',
            '<h3 class="records-sheet-title">Задайте Цель На День</h3>',
            '<div class="records-goal-sheet-body">',
            '<button class="records-sheet-adjust" type="button" data-goal-step="-1"', sheet.value <= 0 ? ' disabled' : '', '>−</button>',
            '<div class="records-sheet-goal-center">',
            renderGoalArc(sheet.value, sheet.value, config.max, config.accentClass, config.icon),
            '<div class="records-sheet-goal-caption">', config.unit, '</div>',
            '</div>',
            '<button class="records-sheet-adjust is-plus" type="button" data-goal-step="1"', sheet.value >= config.max ? ' disabled' : '', '>+</button>',
            '</div>',
            '<p class="records-sheet-note">', config.noteHtml, '</p>',
            renderQuickSheetNotice(sheet),
            '<button class="records-sheet-save records-sheet-save-dark" type="button" data-save-sheet', sheet.saving ? ' disabled' : '', '>ГОТОВО</button>',
            '</section>',
            '</div>'
        ].join('');
    }

    function renderPickerColumn(title, unit, currentValue, kind, min, max) {
        var items = [];
        var value;

        for (value = min; value <= max; value += 1) {
            items.push(
                '<button class="records-picker-value ' + (value === currentValue ? 'records-picker-value-current' : '') + '" type="button" data-picker-select="' + value + '" data-picker-kind="' + kind + '"' + (value === currentValue ? ' aria-current="true"' : '') + '>' + value + '</button>'
            );
        }

        return [
            '<div class="records-picker-column">',
            '<div class="records-picker-column-head">',
            '<h4>', title, '</h4>',
            '<span>', unit, '</span>',
            '</div>',
            '<div class="records-picker-values" data-picker-wheel="', kind, '" data-picker-min="', min, '" data-picker-max="', max, '" data-picker-current="', currentValue, '">',
            items.join(''),
            '</div>',
            '</div>'
        ].join('');
    }

    function renderPulseSheet(sheet) {
        return [
            '<div class="records-sheet-layer">',
            '<button class="records-sheet-backdrop" type="button" data-close-sheet aria-label="Закрыть"></button>',
            '<section class="records-sheet records-sheet-picker records-sheet-picker-pulse" role="dialog" aria-modal="true">',
            '<div class="records-sheet-handle" aria-hidden="true"></div>',
            '<div class="records-picker-top"><span></span><button class="records-picker-cancel" type="button" data-close-sheet>Отмена</button></div>',
            '<div class="records-picker-grid records-picker-grid-single">',
            renderPickerColumn('ПУЛЬС', 'bpm', sheet.value, 'pulse', 30, 220),
            '</div>',
            renderQuickSheetNotice(sheet),
            '<button class="records-sheet-save" type="button" data-save-sheet', sheet.saving ? ' disabled' : '', '>СОХРАНИТЬ</button>',
            '</section>',
            '</div>'
        ].join('');
    }

    function renderBloodPressureSheet(sheet) {
        return [
            '<div class="records-sheet-layer">',
            '<button class="records-sheet-backdrop" type="button" data-close-sheet aria-label="Закрыть"></button>',
            '<section class="records-sheet records-sheet-picker records-sheet-picker-pressure" role="dialog" aria-modal="true">',
            '<div class="records-sheet-handle" aria-hidden="true"></div>',
            '<div class="records-picker-top"><span></span><button class="records-picker-cancel" type="button" data-close-sheet>Отмена</button></div>',
            '<div class="records-picker-grid records-picker-grid-double">',
            renderPickerColumn('СИСТОЛИЧЕСКОЕ', 'мм рт. ст.', sheet.systolic, 'systolic', 60, 240),
            renderPickerColumn('ДИАСТОЛИЧЕСКОЕ', 'мм рт. ст.', sheet.diastolic, 'diastolic', 40, 180),
            '</div>',
            renderQuickSheetNotice(sheet),
            '<button class="records-sheet-save" type="button" data-save-sheet', sheet.saving ? ' disabled' : '', '>СОХРАНИТЬ</button>',
            '</section>',
            '</div>'
        ].join('');
    }

    function renderActiveSheet() {
        if (!state.sheet) {
            return '';
        }
        if (state.sheet.type === 'goal') {
            return renderGoalSheet(state.sheet);
        }
        if (state.sheet.type === 'pulse') {
            return renderPulseSheet(state.sheet);
        }
        return renderBloodPressureSheet(state.sheet);
    }

    function render() {
        var root = document.getElementById('page-root');
        var summary = state.summary;

        if (!root || !summary) {
            return;
        }

        root.innerHTML = [
            '<section class="records-screen">',
            '<header class="records-screen-head">',
            '<div class="records-screen-copy">',
            '<h1>Сегодня</h1>',
            '<p>', site.escapeHtml(formatPageDate(summary.local_date)), '</p>',
            '</div>',
            '</header>',
            '<section class="records-grid">',
            renderGoalCard('steps', summary.steps_goal),
            renderWaterCard(summary),
            renderPulseCard(summary),
            renderBloodPressureCard(summary),
            '</section>',
            state.notice ? '<p class="records-inline-notice">' + site.escapeHtml(state.notice) + '</p>' : '',
            '</section>',
            renderActiveSheet()
        ].join('');

        document.body.classList.toggle('records-sheet-open', !!state.sheet);
        document.body.classList.toggle('records-goal-sheet-open', !!state.sheet && state.sheet.type === 'goal');
        bindPickerScrollers(root);
        syncPickerScrollers(root);
    }

    function rerender(options) {
        var preserveScroll = !options || options.preserveScroll !== false;
        var scrollY = preserveScroll ? window.scrollY : 0;
        render();
        if (preserveScroll) {
            window.scrollTo(0, scrollY);
        }
    }

    function openGoalSheet(metric) {
        var summary = state.summary;
        var config = goalConfig(metric);
        var currentValue = metric === 'water' ? summary.water_goal_glasses : summary.steps_goal;
        state.notice = '';
        state.sheet = {
            type: 'goal',
            metric: metric,
            value: currentValue > 0 ? currentValue : config.emptyDefault,
            saving: false,
            message: '',
            isError: false
        };
        rerender();
    }

    function openPulseSheet() {
        state.notice = '';
        state.sheet = {
            type: 'pulse',
            value: state.summary.latest_pulse_bpm != null ? state.summary.latest_pulse_bpm : 72,
            saving: false,
            message: '',
            isError: false
        };
        rerender();
    }

    function openBloodPressureSheet() {
        state.notice = '';
        state.sheet = {
            type: 'blood-pressure',
            systolic: state.summary.latest_systolic != null ? state.summary.latest_systolic : 110,
            diastolic: state.summary.latest_diastolic != null ? state.summary.latest_diastolic : 75,
            saving: false,
            message: '',
            isError: false
        };
        rerender();
    }

    function closeSheet() {
        state.sheet = null;
        rerender();
    }

    function pickerBounds(kind) {
        if (kind === 'pulse') {
            return { min: 30, max: 220 };
        }
        if (kind === 'systolic') {
            return { min: 60, max: 240 };
        }
        return { min: 40, max: 180 };
    }

    function pickerValue(kind) {
        if (!state.sheet) {
            return 0;
        }
        if (kind === 'pulse') {
            return clamp(state.sheet.value, 30, 220);
        }
        if (kind === 'systolic') {
            return clamp(state.sheet.systolic, 60, 240);
        }
        return clamp(state.sheet.diastolic, 40, 180);
    }

    function updateGoalValue(deltaSign) {
        var config = goalConfig(state.sheet.metric);
        state.sheet.value = clamp(
            state.sheet.value + config.step * deltaSign,
            0,
            config.max
        );
        rerender();
    }

    function updatePickerValue(kind, deltaSign) {
        if (!state.sheet) {
            return;
        }
        setPickerValue(kind, pickerValue(kind) + deltaSign);
    }

    function setPickerValue(kind, nextValue) {
        var bounds = pickerBounds(kind);
        var normalized = clamp(nextValue, bounds.min, bounds.max);

        if (!state.sheet) {
            return;
        }
        if (kind === 'pulse') {
            state.sheet.value = normalized;
        }
        if (kind === 'systolic') {
            state.sheet.systolic = normalized;
            if (state.sheet.systolic <= state.sheet.diastolic) {
                state.sheet.diastolic = Math.max(40, state.sheet.systolic - 1);
            }
        }
        if (kind === 'diastolic') {
            state.sheet.diastolic = normalized;
            if (state.sheet.diastolic >= state.sheet.systolic) {
                state.sheet.systolic = Math.min(240, state.sheet.diastolic + 1);
            }
        }
        rerender();
    }

    function syncSinglePickerScroller(scroller) {
        var kind = scroller.getAttribute('data-picker-wheel') || '';
        var bounds = pickerBounds(kind);
        var current = pickerValue(kind);
        var targetTop = (current - bounds.min) * PICKER_ITEM_HEIGHT;

        if (Math.abs(scroller.scrollTop - targetTop) > 1) {
            scroller.scrollTop = targetTop;
        }
    }

    function syncPickerScrollers(root) {
        if (!root || !state.sheet || state.sheet.type === 'goal') {
            return;
        }
        Array.prototype.forEach.call(root.querySelectorAll('[data-picker-wheel]'), function (scroller) {
            syncSinglePickerScroller(scroller);
        });
    }

    function bindPickerScrollers(root) {
        if (!root) {
            return;
        }

        Array.prototype.forEach.call(root.querySelectorAll('[data-picker-wheel]'), function (scroller) {
            if (scroller.__pickerBound) {
                return;
            }

            scroller.addEventListener('scroll', function () {
                var kind = scroller.getAttribute('data-picker-wheel') || '';
                var bounds = pickerBounds(kind);

                if (scroller.__pickerTimer) {
                    window.clearTimeout(scroller.__pickerTimer);
                }

                scroller.__pickerTimer = window.setTimeout(function () {
                    var nextValue = clamp(
                        bounds.min + Math.round(scroller.scrollTop / PICKER_ITEM_HEIGHT),
                        bounds.min,
                        bounds.max
                    );

                    if (nextValue !== pickerValue(kind)) {
                        setPickerValue(kind, nextValue);
                        return;
                    }

                    syncSinglePickerScroller(scroller);
                }, 64);
            }, { passive: true });

            scroller.__pickerBound = true;
        });
    }

    function updateWaterProgress(deltaSign) {
        var goal = clamp(state.summary && state.summary.water_goal_glasses, 0, goalConfig('water').max);
        var previousValue;
        var nextValue;

        if (!state.summary || state.waterSaving) {
            return;
        }
        if (goal <= 0) {
            openGoalSheet('water');
            return;
        }

        previousValue = clamp(state.summary.water_consumed_glasses, 0, goal);
        nextValue = clamp(previousValue + deltaSign, 0, goal);
        if (nextValue === previousValue) {
            return;
        }

        state.notice = '';
        state.waterSaving = true;
        state.summary.water_consumed_glasses = nextValue;
        rerender();

        site.sendJson('/api/records/water-intake', 'PUT', { value: nextValue }, 'Не удалось сохранить воду.')
            .then(function (summary) {
                state.summary = normalizeSummary(summary);
                state.waterSaving = false;
                rerender();
            })
            .catch(function (error) {
                state.summary.water_consumed_glasses = previousValue;
                state.waterSaving = false;
                if (error && error.code === 'AUTH_REQUIRED') {
                    rerender();
                    return;
                }
                state.notice = error.message || 'Не удалось сохранить воду.';
                rerender();
            });
    }

    function startSaving(message) {
        if (!state.sheet) {
            return;
        }
        state.sheet.saving = true;
        state.sheet.message = message;
        state.sheet.isError = false;
        rerender();
    }

    function showSheetError(message) {
        if (!state.sheet) {
            return;
        }
        state.sheet.saving = false;
        state.sheet.message = message;
        state.sheet.isError = true;
        rerender();
    }

    function submitSheet() {
        var request;
        if (!state.sheet) {
            return;
        }

        if (state.sheet.type === 'goal') {
            if (state.sheet.metric === 'water') {
                startSaving('Сохраняю цель по воде...');
                request = site.sendJson('/api/records/water-goal', 'PUT', { value: state.sheet.value }, 'Не удалось сохранить цель по воде.');
            } else {
                startSaving('Сохраняю цель по шагам...');
                request = site.sendJson('/api/records/steps-goal', 'PUT', { value: state.sheet.value }, 'Не удалось сохранить цель по шагам.');
            }
        } else if (state.sheet.type === 'pulse') {
            startSaving('Сохраняю пульс...');
            request = site.sendJson('/api/records/pulse', 'POST', { bpm: state.sheet.value }, 'Не удалось сохранить пульс.');
        } else {
            startSaving('Сохраняю давление...');
            request = site.sendJson('/api/records/blood-pressure', 'POST', {
                systolic: state.sheet.systolic,
                diastolic: state.sheet.diastolic
            }, 'Не удалось сохранить давление.');
        }

        request
            .then(function (summary) {
                state.summary = normalizeSummary(summary);
                state.sheet = null;
                rerender();
            })
            .catch(function (error) {
                if (error && error.code === 'AUTH_REQUIRED') {
                    return;
                }
                showSheetError(error.message || 'Не удалось сохранить данные.');
            });
    }

    function bindRootEvents(root) {
        if (!root || root.__recordsBound) {
            return;
        }

        root.addEventListener('click', function (event) {
            var target = event.target.closest('button');
            var anchor;
            if (!target) {
                return;
            }

            if (target.hasAttribute('data-open-goal')) {
                openGoalSheet(target.getAttribute('data-open-goal'));
                return;
            }
            if (target.hasAttribute('data-open-pulse-sheet')) {
                openPulseSheet();
                return;
            }
            if (target.hasAttribute('data-open-pressure-sheet')) {
                openBloodPressureSheet();
                return;
            }
            if (target.hasAttribute('data-close-sheet')) {
                closeSheet();
                return;
            }
            if (target.hasAttribute('data-goal-step') && state.sheet && state.sheet.type === 'goal') {
                updateGoalValue(Number(target.getAttribute('data-goal-step') || '0'));
                return;
            }
            if (target.hasAttribute('data-picker-select') && target.hasAttribute('data-picker-kind')) {
                setPickerValue(
                    target.getAttribute('data-picker-kind'),
                    Number(target.getAttribute('data-picker-select') || '0')
                );
                return;
            }
            if (target.hasAttribute('data-water-adjust')) {
                updateWaterProgress(Number(target.getAttribute('data-water-adjust') || '0'));
                return;
            }
            if (target.hasAttribute('data-save-sheet')) {
                submitSheet();
                return;
            }
            if (target.hasAttribute('data-scroll-vitals')) {
                anchor = document.getElementById('records-vitals-anchor');
                if (anchor) {
                    anchor.scrollIntoView({ behavior: 'smooth', block: 'start' });
                }
            }
        });

        document.addEventListener('keydown', function (event) {
            if (event.key === 'Escape' && state.sheet) {
                closeSheet();
            }
        });

        root.__recordsBound = true;
    }

    function loadPage() {
        return Promise.all([
            site.requireJson('/api/profile', null, 'Не удалось загрузить профиль.'),
            site.requireJson('/api/records/summary', null, 'Не удалось загрузить записи.')
        ]).then(function (results) {
            state.profile = results[0];
            state.summary = normalizeSummary(results[1]);
            state.notice = '';
            state.waterSaving = false;
            site.setUserShell(results[0]);
        });
    }

    function mountRecordsPage() {
        var routeToken = currentRouteToken();
        var root = document.getElementById('page-root');

        activeRouteToken = routeToken;
        if (!root) {
            return;
        }

        state.notice = '';
        state.waterSaving = false;
        document.body.classList.remove('records-sheet-open');
        document.body.classList.remove('records-goal-sheet-open');
        bindRootEvents(root);
        site.renderState(root, 'Загрузка', 'Собираю экран записей...', false);
        site.ensureOnboardingAccess()
            .then(function () {
                return loadPage();
            })
            .then(function () {
                if (!isActiveRoute(routeToken)) {
                    return;
                }
                rerender({ preserveScroll: false });
            })
            .catch(function (error) {
                if (!isActiveRoute(routeToken)) {
                    return;
                }
                if (error && (error.code === 'AUTH_REQUIRED' || error.code === 'ONBOARDING_REQUIRED')) {
                    return;
                }
                document.body.classList.remove('records-sheet-open');
                document.body.classList.remove('records-goal-sheet-open');
                site.renderState(root, 'Ошибка', error.message || 'Не удалось загрузить экран записей.', true);
            });
    }

    window.KinematicsPages = window.KinematicsPages || {};
    window.KinematicsPages.progress = mountRecordsPage;

    document.addEventListener('DOMContentLoaded', mountRecordsPage);
})();
