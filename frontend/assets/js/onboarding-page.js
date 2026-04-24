(function () {
    var site = window.KinematicsSite;
    var ROOT_ID = 'onboarding-root';
    var ONBOARDING_DRAFT_KEY = 'kinematics-onboarding-draft-v5';
    var LEGACY_ONBOARDING_DRAFT_KEYS = ['kinematics-onboarding-draft-v1', 'kinematics-onboarding-draft-v2', 'kinematics-onboarding-draft-v3', 'kinematics-onboarding-draft-v4'];
    var PLAN_HANDOFF_STORAGE_KEY = 'kinematics-personal-plan-handoff-v4';
    var DEFAULT_REMINDER_TIME = '06:58';
    var NUMERIC_DATA_FIELDS = ['age', 'height_cm', 'current_weight_kg', 'target_weight_kg', 'training_frequency'];
    var ARRAY_DATA_FIELDS = ['interest_tags', 'equipment_tags', 'injury_areas', 'training_days'];

    if (!site) {
        return;
    }

    var MEDIA = {
        poster: '/assets/media/onboarding/poster-home.svg',
        coachAvatar: '/assets/media/onboarding/coach-avatar-20260314b.png',
        coachIntro: '/assets/media/onboarding/coach-avatar-20260314b.png',
        coachAnalyze: '/assets/media/onboarding/coach-thinks-20260314b.png',
        male: '/assets/media/onboarding/gender-male-20260317.png',
        female: '/assets/media/onboarding/gender-female-20260317.png'
    };

    var SECTION_META = {
        1: { number: '01', label: 'ЦЕЛЬ И ФОКУС' },
        2: { number: '02', label: 'ВАШИ ДАННЫЕ' },
        3: { number: '03', label: 'РИТМ И ОГРАНИЧЕНИЯ' }
    };

    var FITNESS_LEVEL_OPTIONS = [
        { value: 'beginner', title: 'Новичок', description: 'Только начинаю и хочу спокойный вход.', icon: 'rocket' },
        { value: 'intermediate', title: 'Любитель', description: 'База уже есть, нужен уверенный рабочий ритм.', icon: 'zap' },
        { value: 'advanced', title: 'Продвинутый', description: 'Могу держать плотную нагрузку и быстрый темп.', icon: 'bolt' }
    ];

    var ACTIVITY_OPTIONS = [
        { value: 'sedentary', title: 'Сидячий режим', description: 'Большую часть дня провожу без движения.', icon: 'seat' },
        { value: 'light', title: 'Лёгкая активность', description: 'Иногда гуляю и немного двигаюсь.', icon: 'walk' },
        { value: 'moderate', title: 'Умеренная активность', description: 'Есть прогулки и регулярное бытовое движение.', icon: 'walk' },
        { value: 'high', title: 'Высокая активность', description: 'Регулярно тренируюсь и двигаюсь каждый день.', icon: 'run' },
        { value: 'very_high', title: 'Очень высокая', description: 'Плотный график с постоянной физической нагрузкой.', icon: 'run' }
    ];

    var DAYS = [
        { value: 'mon', label: 'Пн' },
        { value: 'tue', label: 'Вт' },
        { value: 'wed', label: 'Ср' },
        { value: 'thu', label: 'Чт' },
        { value: 'fri', label: 'Пт' },
        { value: 'sat', label: 'Сб' },
        { value: 'sun', label: 'Вс' }
    ];
    var VALID_DAY_VALUES = DAYS.map(function (day) {
        return day.value;
    });
    var GOAL_TITLES = {
        lose_weight: 'Сбросить вес',
        gain_muscle: 'Нарастить мышечную массу',
        stay_fit: 'Быть в форме'
    };
    var FOCUS_TITLES = {
        shoulders: 'Плечи',
        arms: 'Руки',
        chest: 'Грудь',
        core: 'Пресс',
        legs: 'Ноги',
        full_body: 'Всё тело'
    };
    var FITNESS_LEVEL_TITLES = {
        beginner: 'Новичок',
        intermediate: 'Средний',
        advanced: 'Продвинутый',
        unknown: 'Адаптивный'
    };

    var STEPS = [
        { key: 'splash', type: 'splash' },
        { key: 'coach_intro', type: 'coach' },
        {
            key: 'main_goal',
            type: 'single',
            section: 1,
            title: 'Какая у вас главная цель?',
            field: 'main_goal',
            presentation: 'goal-cards',
            options: [
                { value: 'lose_weight', title: 'Сбросить Вес' },
                { value: 'gain_muscle', title: 'Нарастить Мышечную Массу' },
                { value: 'stay_fit', title: 'Быть В Форме' }
            ]
        },
        {
            key: 'focus_area',
            type: 'single',
            section: 1,
            title: 'Что хотите проработать?',
            field: 'focus_area',
            presentation: 'focus-map',
            options: [
                { value: 'shoulders', title: 'Плечи' },
                { value: 'arms', title: 'Руки' },
                { value: 'chest', title: 'Грудь' },
                { value: 'core', title: 'Пресс' },
                { value: 'legs', title: 'Ноги' },
                { value: 'full_body', title: 'Всё тело' }
            ]
        },
        {
            key: 'gender',
            type: 'single',
            section: 1,
            title: 'Какого вы пола?',
            field: 'gender',
            helper: 'Это поможет точнее рассчитать базовые показатели организма.',
            presentation: 'gender-cards',
            options: [
                { value: 'male', title: 'Мужской', image: MEDIA.male },
                { value: 'female', title: 'Женский', image: MEDIA.female }
            ]
        },
        {
            key: 'age',
            type: 'metric',
            section: 2,
            title: 'В каком году вы родились?',
            field: 'age',
            min: 14,
            max: 80,
            step: 1,
            unit: 'год',
            displayMode: 'birth-year-wheel'
        },
        {
            key: 'height_cm',
            type: 'metric',
            section: 2,
            title: 'Укажите свой рост',
            field: 'height_cm',
            min: 140,
            max: 210,
            step: 1,
            unit: 'см',
            displayMode: 'height'
        },
        {
            key: 'current_weight_kg',
            type: 'metric',
            section: 2,
            title: 'Сколько вы сейчас весите?',
            field: 'current_weight_kg',
            min: 35,
            max: 180,
            step: 0.1,
            unit: 'кг',
            displayMode: 'weight-current',
            insight: 'bmi'
        },
        {
            key: 'target_weight_kg',
            type: 'metric',
            section: 2,
            title: 'Какой вес вы хотите?',
            field: 'target_weight_kg',
            min: 35,
            max: 180,
            step: 0.1,
            unit: 'кг',
            displayMode: 'weight-target'
        },
        {
            key: 'fitness_level',
            type: 'single',
            section: 3,
            title: 'В какой вы физической форме?',
            field: 'fitness_level',
            presentation: 'icon-list',
            options: FITNESS_LEVEL_OPTIONS
        },
        {
            key: 'activity_level',
            type: 'single',
            section: 3,
            title: 'Каков ваш уровень активности?',
            field: 'activity_level',
            presentation: 'icon-list',
            options: ACTIVITY_OPTIONS
        },
        {
            key: 'goal_pace',
            type: 'single',
            section: 3,
            title: 'Какой темп вам подходит?',
            field: 'goal_pace',
            presentation: 'icon-list',
            options: [
                { value: 'slow', title: 'Медленно и уверенно', icon: 'lotus' },
                { value: 'moderate', title: 'Умеренная скорость', icon: 'timer' },
                { value: 'fast', title: 'Как можно быстрее', icon: 'flash' }
            ]
        },
        {
            key: 'interest_tags',
            type: 'multi',
            section: 3,
            title: 'Выберите до 3 занятий, которые вас интересуют',
            field: 'interest_tags',
            maxSelect: 3,
            presentation: 'check-stack',
            options: [
                { value: 'general', title: 'Общие', icon: 'person' },
                { value: 'pilates', title: 'Пилатес', icon: 'pilates' },
                { value: 'chair', title: 'Тренировка на стуле', icon: 'chair' },
                { value: 'dumbbells', title: 'С гантелями', icon: 'dumbbell' },
                { value: 'stretching', title: 'Растяжка', icon: 'stretch' }
            ]
        },
        {
            key: 'equipment_tags',
            type: 'multi',
            section: 3,
            title: 'Какой инвентарь у вас есть?',
            field: 'equipment_tags',
            presentation: 'check-stack',
            options: [
                { value: 'none', title: 'Без инвентаря', icon: 'none' },
                { value: 'dumbbells', title: 'Гантели', icon: 'dumbbell' },
                { value: 'bands', title: 'Резинки', icon: 'band' },
                { value: 'gym', title: 'Тренажёрный зал', icon: 'gym' }
            ]
        },
        {
            key: 'training_frequency',
            type: 'frequency',
            section: 3,
            title: 'Как часто вы хотите тренироваться?',
            field: 'training_frequency'
        },
        {
            key: 'injury_areas',
            type: 'multi',
            section: 3,
            title: 'Есть ли у вас боль, травмы или ограничения?',
            field: 'injury_areas',
            presentation: 'icon-list',
            options: [
                { value: 'none', title: 'Нет', icon: 'none' },
                { value: 'shoulders', title: 'Плечи', icon: 'shoulders' },
                { value: 'wrists', title: 'Запястье', icon: 'wrist' },
                { value: 'knees', title: 'Колени', icon: 'knee' },
                { value: 'ankles', title: 'Лодыжка', icon: 'ankle' }
            ]
        },
        {
            key: 'schedule',
            type: 'schedule',
            section: 3,
            title: 'Задать дни тренировки'
        },
        { key: 'analyzing', type: 'analyzing' }
    ];

    var STEP_INDEX = {};
    STEPS.forEach(function (step, index) {
        STEP_INDEX[step.key] = index;
    });

    var state = {
        onboarding: null,
        currentStepKey: 'splash',
        feedbackText: '',
        feedbackError: false,
        isSaving: false,
        isFinishing: false,
        analysisProgress: 0,
        analysisRequestComplete: false,
        analysisTimerId: null,
        analysisAutoFinishTimerId: null,
        metricPersistTimerId: null,
        savedSignatures: {},
        metricUnits: {
            height_cm: 'cm',
            current_weight_kg: 'kg',
            target_weight_kg: 'kg'
        }
    };

    var METRIC_DISPLAY_CONFIG = {
        height_cm: {
            defaultUnit: 'cm',
            units: {
                cm: {
                    label: 'cm',
                    min: 140,
                    max: 210,
                    step: 1,
                    toCanonical: function (value) { return Math.round(Number(value)); },
                    fromCanonical: function (value) { return Math.round(Number(value)); }
                },
                ft: {
                    label: 'ft',
                    min: 4.6,
                    max: 6.9,
                    step: 0.1,
                    toCanonical: function (value) { return Math.round(Number(value) * 30.48); },
                    fromCanonical: function (value) { return Math.round((Number(value) / 30.48) * 10) / 10; }
                }
            }
        },
        current_weight_kg: {
            defaultUnit: 'kg',
            units: {
                kg: {
                    label: 'kg',
                    min: 35,
                    max: 180,
                    step: 0.1,
                    toCanonical: function (value) { return Math.round(Number(value) * 10) / 10; },
                    fromCanonical: function (value) { return Math.round(Number(value) * 10) / 10; }
                },
                lb: {
                    label: 'lb',
                    min: 77,
                    max: 397,
                    step: 1,
                    toCanonical: function (value) { return Math.round((Number(value) / 2.2046226218) * 10) / 10; },
                    fromCanonical: function (value) { return Math.round((Number(value) * 2.2046226218) * 10) / 10; }
                }
            }
        },
        target_weight_kg: {
            defaultUnit: 'kg',
            units: {
                kg: {
                    label: 'kg',
                    min: 35,
                    max: 180,
                    step: 0.1,
                    toCanonical: function (value) { return Math.round(Number(value) * 10) / 10; },
                    fromCanonical: function (value) { return Math.round(Number(value) * 10) / 10; }
                },
                lb: {
                    label: 'lb',
                    min: 77,
                    max: 397,
                    step: 1,
                    toCanonical: function (value) { return Math.round((Number(value) / 2.2046226218) * 10) / 10; },
                    fromCanonical: function (value) { return Math.round((Number(value) * 2.2046226218) * 10) / 10; }
                }
            }
        }
    };

    function getRoot() {
        return document.getElementById(ROOT_ID);
    }

    function escapeHtml(value) {
        return site.escapeHtml(value);
    }

    function ensureOnboardingStateShape() {
        if (!state.onboarding || typeof state.onboarding !== 'object') {
            state.onboarding = {};
        }
        if (!state.onboarding.data || typeof state.onboarding.data !== 'object') {
            state.onboarding.data = {};
        }
        if (!state.onboarding.derived || typeof state.onboarding.derived !== 'object') {
            state.onboarding.derived = {};
        }
        state.onboarding.data = normalizeOnboardingData(state.onboarding.data);
        return state.onboarding;
    }

    function normalizeNumericFieldValue(field, value) {
        if (value === null || value === undefined || value === '') {
            return null;
        }
        var numericValue = Number(value);
        if (!Number.isFinite(numericValue)) {
            return null;
        }
        if (field === 'training_frequency') {
            return Math.max(1, Math.min(6, Math.round(numericValue)));
        }
        return numericValue;
    }

    function normalizeArrayFieldValue(field, value) {
        if (!Array.isArray(value)) {
            return [];
        }
        var seen = {};
        return value.reduce(function (list, item) {
            var normalized = typeof item === 'string' ? item.trim() : '';
            if (!normalized) {
                return list;
            }
            if (field === 'training_days' && VALID_DAY_VALUES.indexOf(normalized) < 0) {
                return list;
            }
            if (seen[normalized]) {
                return list;
            }
            seen[normalized] = true;
            list.push(normalized);
            return list;
        }, []);
    }

    function reconcileTrainingDays(selectedDays, frequency) {
        var normalizedFrequency = Number(frequency) || 0;
        var normalizedDays = normalizeArrayFieldValue('training_days', selectedDays);

        if (!normalizedFrequency) {
            return normalizedDays;
        }

        return normalizedDays.slice(0, normalizedFrequency);
    }

    function normalizeOnboardingData(data) {
        var source = data && typeof data === 'object' ? data : {};
        var normalized = Object.assign({}, source);

        NUMERIC_DATA_FIELDS.forEach(function (field) {
            if (Object.prototype.hasOwnProperty.call(source, field)) {
                normalized[field] = normalizeNumericFieldValue(field, source[field]);
            }
        });

        ARRAY_DATA_FIELDS.forEach(function (field) {
            if (Object.prototype.hasOwnProperty.call(source, field)) {
                normalized[field] = normalizeArrayFieldValue(field, source[field]);
            }
        });

        normalized.reminders_enabled = !!source.reminders_enabled;
        normalized.reminder_time_local = typeof source.reminder_time_local === 'string' && source.reminder_time_local.trim()
            ? source.reminder_time_local.trim()
            : null;

        if (normalized.training_frequency) {
            normalized.training_days = reconcileTrainingDays(normalized.training_days || [], normalized.training_frequency);
        } else if (Array.isArray(normalized.training_days)) {
            normalized.training_days = [];
        }

        if (normalized.reminders_enabled && !normalized.reminder_time_local) {
            normalized.reminder_time_local = DEFAULT_REMINDER_TIME;
        }

        return normalized;
    }

    function getData() {
        return ensureOnboardingStateShape().data;
    }

    function getDerived() {
        return ensureOnboardingStateShape().derived;
    }

    function getStep(key) {
        return STEPS[STEP_INDEX[key]];
    }

    function getCurrentStep() {
        return getStep(state.currentStepKey);
    }

    function shouldAskTargetWeight(data) {
        var source = data || getData();
        return source.main_goal === 'lose_weight' || source.main_goal === 'gain_muscle';
    }

    function isStepVisible(step, data) {
        if (!step) {
            return false;
        }
        if (step.key === 'target_weight_kg') {
            return shouldAskTargetWeight(data);
        }
        return true;
    }

    function getMetricConfig(step) {
        return step && step.field ? METRIC_DISPLAY_CONFIG[step.field] || null : null;
    }

    function getMetricDisplayUnit(step) {
        var config = getMetricConfig(step);
        if (!config) {
            return step.unit;
        }
        return config.units[state.metricUnits[step.field]] ? state.metricUnits[step.field] : config.defaultUnit;
    }

    function setMetricDisplayUnit(step, unit) {
        var config = getMetricConfig(step);
        if (!config || !config.units[unit]) {
            return;
        }
        state.metricUnits[step.field] = unit;
    }

    function metricDisplayBounds(step) {
        var config = getMetricConfig(step);
        if (!config) {
            return { min: step.min, max: step.max, step: step.step, label: step.unit };
        }
        return config.units[getMetricDisplayUnit(step)];
    }

    function canonicalToDisplayValue(step, value) {
        if (value === null || value === undefined || value === '') {
            return null;
        }
        var config = getMetricConfig(step);
        if (!config) {
            return Number(value);
        }
        return config.units[getMetricDisplayUnit(step)].fromCanonical(value);
    }

    function normalizeMetricValue(step, rawValue) {
        if (rawValue === '' || rawValue === null || rawValue === undefined) {
            return null;
        }
        var parsed = Number(rawValue);
        if (Number.isNaN(parsed)) {
            return null;
        }
        if (step.displayMode === 'birth-year-wheel') {
            var derivedAge = birthYearToAge(parsed);
            if (!Number.isFinite(derivedAge)) {
                return null;
            }
            return Math.max(step.min, Math.min(step.max, Math.round(derivedAge)));
        }
        var config = getMetricConfig(step);
        var canonical = config ? config.units[getMetricDisplayUnit(step)].toCanonical(parsed) : parsed;
        var clamped = Math.max(step.min, Math.min(step.max, canonical));
        if (step.step === 1) {
            return Math.round(clamped);
        }
        return Math.round(clamped / step.step) * step.step;
    }

    function formatMetricDisplayText(displayValue) {
        if (Math.abs(Number(displayValue) - Math.round(Number(displayValue))) < 0.001) {
            return String(Math.round(Number(displayValue)));
        }
        return Number(displayValue).toFixed(1);
    }

    function roundToStep(value, stepSize) {
        if (stepSize === 1) {
            return Math.round(value);
        }
        return Math.round(value / stepSize) * stepSize;
    }

    function currentCalendarYear() {
        return new Date().getFullYear();
    }

    function ageToBirthYear(age) {
        var numericAge = Number(age);
        if (!Number.isFinite(numericAge)) {
            return null;
        }
        return currentCalendarYear() - Math.round(numericAge);
    }

    function birthYearToAge(year) {
        var numericYear = Number(year);
        if (!Number.isFinite(numericYear)) {
            return null;
        }
        return currentCalendarYear() - Math.round(numericYear);
    }

    function getMetricFallback(step) {
        if (step.field === 'age') {
            return step.displayMode === 'birth-year-wheel' ? currentCalendarYear() - 27 : 27;
        }
        if (step.field === 'height_cm') {
            return 180;
        }
        if (step.field === 'current_weight_kg') {
            return 76;
        }
        return 67;
    }

    function getMetricLiveDisplayValue(step) {
        var dataValue = getData()[step.field];
        var displayValue = step.displayMode === 'birth-year-wheel'
            ? ageToBirthYear(dataValue)
            : canonicalToDisplayValue(step, dataValue);
        return displayValue == null ? getMetricFallback(step) : displayValue;
    }

    function buildMetricWheelValues(step) {
        if (step.displayMode === 'birth-year-wheel') {
            var years = [];
            var year = currentCalendarYear() - step.max;
            var yearLimit = currentCalendarYear() - step.min;
            while (year <= yearLimit) {
                years.push(year);
                year += 1;
            }
            return years;
        }
        var bounds = metricDisplayBounds(step);
        var values = [];
        var current = bounds.min;
        var limit = 0;
        while (current <= bounds.max + (bounds.step / 2) && limit < 1200) {
            values.push(roundToStep(current, bounds.step));
            current += bounds.step;
            limit += 1;
        }
        return values;
    }

    function renderMetricWheelItems(values, selectedValue, itemClass) {
        var paddingItems = [
            '<div class="' + itemClass + ' ' + itemClass + '--ghost" aria-hidden="true"></div>',
            '<div class="' + itemClass + ' ' + itemClass + '--ghost" aria-hidden="true"></div>'
        ].join('');
        return [
            paddingItems,
            values.map(function (value) {
                var selected = Math.abs(Number(value) - Number(selectedValue)) < 0.001;
                return '<div class="' + itemClass + ' ' + (selected ? 'is-selected' : '') + '" data-wheel-value="' + value + '">' + escapeHtml(formatMetricDisplayText(value)) + '</div>';
            }).join(''),
            paddingItems
        ].join('');
    }

    function renderMetricRulerItems(step, values, selectedValue) {
        var currentUnit = getMetricDisplayUnit(step);
        var paddingItems = [
            '<div class="fi-height-ruler-item fi-height-ruler-item--ghost" aria-hidden="true"></div>',
            '<div class="fi-height-ruler-item fi-height-ruler-item--ghost" aria-hidden="true"></div>'
        ].join('');
        return [
            paddingItems,
            values.map(function (value) {
                var selected = Math.abs(Number(value) - Number(selectedValue)) < 0.001;
                var hasLabel = currentUnit === 'cm'
                    ? Math.round(Number(value)) % 10 === 0
                    : Math.abs((Number(value) * 10) % 5) < 0.001;
                return [
                    '<div class="fi-height-ruler-item ',
                    selected ? 'is-selected ' : '',
                    hasLabel ? 'has-label' : '',
                    '" data-wheel-value="', value, '">',
                    '<span class="fi-height-ruler-mark"></span>',
                    hasLabel ? '<span class="fi-height-ruler-text">' + escapeHtml(formatMetricDisplayText(value)) + '</span>' : '',
                    '</div>'
                ].join('');
            }).join(''),
            paddingItems
        ].join('');
    }

    function renderWeightRulerItems(step, values, selectedValue) {
        var currentUnit = getMetricDisplayUnit(step);
        var paddingItems = [
            '<div class="fi-weight-ruler-item fi-weight-ruler-item--ghost" aria-hidden="true"></div>',
            '<div class="fi-weight-ruler-item fi-weight-ruler-item--ghost" aria-hidden="true"></div>'
        ].join('');
        return [
            paddingItems,
            values.map(function (value) {
                var selected = Math.abs(Number(value) - Number(selectedValue)) < 0.001;
                var hasLabel = currentUnit === 'kg'
                    ? Math.abs(Number(value) % 1) < 0.001
                    : Math.abs(Number(value) % 10) < 0.001;
                return [
                    '<div class="fi-weight-ruler-item ',
                    selected ? 'is-selected ' : '',
                    hasLabel ? 'has-label' : '',
                    '" data-wheel-value="', value, '">',
                    '<span class="fi-weight-ruler-tick"></span>',
                    hasLabel ? '<span class="fi-weight-ruler-label">' + escapeHtml(formatMetricDisplayText(value)) + '</span>' : '',
                    '</div>'
                ].join('');
            }).join(''),
            paddingItems
        ].join('');
    }

    function resolveBmiLabel(value) {
        if (typeof value !== 'number' || !Number.isFinite(value)) {
            return null;
        }
        if (value < 18.5) {
            return 'Ниже нормы';
        }
        if (value < 25) {
            return 'Обычно';
        }
        if (value < 30) {
            return 'Выше нормы';
        }
        return 'Высокий';
    }

    function syncLocalDerivedMetrics() {
        var data = getData();
        var derived = getDerived();
        var heightCm = Number(data.height_cm);
        var currentWeight = Number(data.current_weight_kg);
        var age = Number(data.age);
        var bmi = null;
        var bmr = null;

        if (Number.isFinite(heightCm) && Number.isFinite(currentWeight) && heightCm > 0) {
            bmi = Math.round((currentWeight / Math.pow(heightCm / 100, 2)) * 10) / 10;
        }
        if (Number.isFinite(heightCm) && Number.isFinite(currentWeight) && Number.isFinite(age) && age > 0) {
            if (data.gender === 'female') {
                bmr = Math.round((10 * currentWeight) + (6.25 * heightCm) - (5 * age) - 161);
            } else {
                bmr = Math.round((10 * currentWeight) + (6.25 * heightCm) - (5 * age) + 5);
            }
        }

        derived.bmi = bmi;
        derived.bmi_label = resolveBmiLabel(bmi);
        derived.bmr_kcal = bmr;
        derived.analysis_items = [
            {
                title: 'Анализируем данные',
                value: Number.isFinite(heightCm) && Number.isFinite(currentWeight)
                    ? Math.round(heightCm) + ' см, ' + currentWeight.toFixed(1) + ' кг'
                    : 'Собираем параметры'
            },
            {
                title: 'Рассчитываем метаболизм',
                value: Number.isFinite(bmr) ? bmr + ' ккал' : 'Готовим расчёт'
            },
            {
                title: 'Настраиваем область фокуса',
                value: FOCUS_TITLES[data.focus_area] || 'Подбираем фокус'
            },
            {
                title: 'Выбираем уровень подготовки',
                value: FITNESS_LEVEL_TITLES[data.fitness_level] || 'Уточняем уровень'
            }
        ];
    }

    function ensureScheduleDefaults() {
        var data = getData();
        var selectedDays = normalizeArrayFieldValue('training_days', data.training_days || []);
        var frequency = Number(data.training_frequency || 0);
        var normalizedDays = reconcileTrainingDays(selectedDays, frequency);

        if (frequency && JSON.stringify(normalizedDays) !== JSON.stringify(selectedDays)) {
            updateLocalData('training_days', normalizedDays);
        }
        if (data.reminders_enabled && !data.reminder_time_local) {
            updateLocalData('reminder_time_local', DEFAULT_REMINDER_TIME);
        }
    }

    function updateLocalData(field, value) {
        ensureOnboardingStateShape().data[field] = value;
        syncLocalDerivedMetrics();
        saveDraft();
    }

    function isEmptyDraftValue(value) {
        if (Array.isArray(value)) {
            return value.length === 0;
        }
        return value === null || value === undefined || value === '';
    }

    function hasAnyDraftAnswers(data) {
        if (!data || typeof data !== 'object') {
            return false;
        }
        return Object.keys(data).some(function (key) {
            return !isEmptyDraftValue(data[key]) && key !== 'onboarding_version' && key !== 'reminders_enabled';
        });
    }

    function readDraft() {
        var raw = site.safeGetSessionStorage ? site.safeGetSessionStorage(ONBOARDING_DRAFT_KEY) : '';
        var index;
        if (!raw && site.safeGetSessionStorage) {
            for (index = 0; index < LEGACY_ONBOARDING_DRAFT_KEYS.length; index += 1) {
                raw = site.safeGetSessionStorage(LEGACY_ONBOARDING_DRAFT_KEYS[index]);
                if (raw) {
                    break;
                }
            }
        }
        if (!raw) {
            return null;
        }
        try {
            var parsed = JSON.parse(raw);
            if (!parsed || typeof parsed !== 'object') {
                return null;
            }
            if (parsed.data && typeof parsed.data === 'object') {
                parsed.data = normalizeOnboardingData(parsed.data);
            }
            return parsed;
        } catch (error) {
            return null;
        }
    }

    function clearDraft() {
        if (site.safeRemoveSessionStorage) {
            site.safeRemoveSessionStorage(ONBOARDING_DRAFT_KEY);
            LEGACY_ONBOARDING_DRAFT_KEYS.forEach(function (key) {
                site.safeRemoveSessionStorage(key);
            });
        }
    }

    function clearPlanCaches() {
        var prefix = 'kinematics-personal-plan:';
        var keysToRemove = [];
        var index;
        var key;

        try {
            for (index = 0; index < window.localStorage.length; index += 1) {
                key = window.localStorage.key(index);
                if (key && key.indexOf(prefix) === 0) {
                    keysToRemove.push(key);
                }
            }
            keysToRemove.forEach(function (storageKey) {
                window.localStorage.removeItem(storageKey);
            });
        } catch (_error) {
            return;
        }
    }

    function isCompletePlanPayload(plan) {
        var source = plan && typeof plan === 'object' ? plan : {};
        var stages = Array.isArray(source.stages) ? source.stages : [];
        var totalDays = 0;

        if (!source.signature || !source.headline || !source.subheadline) {
            return false;
        }
        if (!Array.isArray(source.tags) || !source.tags.length) {
            return false;
        }
        if (!Array.isArray(source.summary_items) || !source.summary_items.length) {
            return false;
        }
        if (stages.length !== 1) {
            return false;
        }

        return stages.every(function (stage) {
            var days = Array.isArray(stage && stage.days) ? stage.days : [];
            if (!days.length) {
                return false;
            }
            totalDays += days.length;
            return days.every(function (day) {
                var exercises = Array.isArray(day && day.exercises) ? day.exercises : [];
                return !!(day && day.title)
                    && exercises.length > 0
                    && exercises.every(function (exercise) {
                        return !!(exercise && exercise.title)
                            && Number(exercise.sets || 0) > 0
                            && Number(exercise.reps || 0) > 0;
                    });
            });
        }) && totalDays === 10;
    }

    function savePlanHandoff(plan) {
        if (!site.safeSetSessionStorage || !isCompletePlanPayload(plan)) {
            return;
        }
        try {
            site.safeSetSessionStorage(PLAN_HANDOFF_STORAGE_KEY, JSON.stringify(plan));
        } catch (_error) {
            return;
        }
    }

    function clearPlanHandoff() {
        if (site.safeRemoveSessionStorage) {
            site.safeRemoveSessionStorage(PLAN_HANDOFF_STORAGE_KEY);
        }
    }

    function dayLabelByValue(value) {
        var match = DAYS.find(function (day) {
            return day.value === value;
        });
        return match ? match.label : value;
    }

    function buildLocalPlanExercise(slug) {
        var library = {
            squat: { title: 'Приседания', details: 'Контроль коленей и ровный корпус', sets: 3, reps: 12, rest_sec: 45 },
            plank: { title: 'Планка', details: 'Держите корпус прямым без провиса', sets: 3, reps: 35, rest_sec: 30 },
            lunge: { title: 'Выпады', details: 'Шаг комфортной длины и стабильный таз', sets: 3, reps: 10, rest_sec: 40 },
            glute_bridge: { title: 'Ягодичный мост', details: 'Подъём таза без рывка', sets: 3, reps: 15, rest_sec: 35 },
            crunch: { title: 'Скручивания', details: 'Мягкий подъём корпуса без рывков шеей', sets: 3, reps: 16, rest_sec: 30 },
            calf_raise: { title: 'Подъёмы на носки', details: 'Плавное движение вверх и вниз', sets: 3, reps: 18, rest_sec: 25 },
            band_row: { title: 'Тяга резинки к поясу', details: 'Лопатки сводим без подъёма плеч', sets: 3, reps: 14, rest_sec: 35 },
            burpee: { title: 'Берпи', details: 'Темп без провала техники', sets: 3, reps: 8, rest_sec: 50 },
            superman: { title: 'Супермен', details: 'Удержание спины и ягодиц в одном ритме', sets: 3, reps: 12, rest_sec: 30 }
        };
        return Object.assign({ slug: slug }, library[slug] || library.squat);
    }

    function buildLocalPlanFromDraft() {
        var data = getData();
        var focusTitle = FOCUS_TITLES[data.focus_area] || 'Всё тело';
        var goalTitle = GOAL_TITLES[data.main_goal] || 'Быть в форме';
        var frequency = Number(data.training_frequency || 3);
        var selectedDays = reconcileTrainingDays(data.training_days || [], frequency);
        var exercisePool = ['squat', 'plank', 'lunge', 'glute_bridge', 'crunch', 'calf_raise', 'band_row', 'superman'];
        var baseDate = new Date();
        var days = [];
        var index;

        for (index = 0; index < 10; index += 1) {
            var isRecovery = index === 2 || index === 6;
            var date = new Date(baseDate.getTime() + index * 24 * 60 * 60 * 1000);
            var dateLabel = String(date.getDate()).padStart(2, '0') + '.' + String(date.getMonth() + 1).padStart(2, '0');
            var weekdayLabel = selectedDays.length ? dayLabelByValue(selectedDays[index % selectedDays.length]) : dayLabelByValue(VALID_DAY_VALUES[index % VALID_DAY_VALUES.length]);
            var exerciseSlugs = isRecovery
                ? ['plank', 'glute_bridge', 'crunch', 'calf_raise']
                : [exercisePool[index % exercisePool.length], exercisePool[(index + 1) % exercisePool.length], exercisePool[(index + 2) % exercisePool.length], 'squat'];

            days.push({
                day_number: index + 1,
                stage_number: 1,
                date_label: dateLabel + ' · ' + weekdayLabel.toLowerCase(),
                title: isRecovery ? 'Восстановление' : (focusTitle + ' и база'),
                subtitle: '',
                duration_min: isRecovery ? 11 : 18,
                estimated_kcal: isRecovery ? 48 : 112,
                intensity: '',
                emphasis: '',
                note: isRecovery ? 'Лёгкий восстановительный день' : 'Основной тренировочный день',
                kind: isRecovery ? 'recovery' : 'workout',
                exercises: exerciseSlugs.map(buildLocalPlanExercise),
                is_highlighted: index === 0
            });
        }

        return {
            user_id: null,
            signature: 'local-demo-' + Date.now(),
            source: 'fallback',
            generated_at: new Date().toISOString(),
            headline: focusTitle,
            subheadline: goalTitle,
            tags: ['Локальный demo', frequency + ' трен./нед', focusTitle],
            summary_items: [
                { label: 'Цель', value: goalTitle },
                { label: 'Фокус', value: focusTitle },
                { label: 'Ритм', value: frequency + ' трен./нед' }
            ],
            stages: [
                {
                    stage_number: 1,
                    title: 'Персональный маршрут',
                    subtitle: 'Локальный план для демо без авторизации',
                    badge: 'Этап 1',
                    days: days
                }
            ]
        };
    }

    function localGuestOnboardingState() {
        return {
            status: 'in_progress',
            is_completed: false,
            resume_step: 'splash',
            data: normalizeOnboardingData({}),
            derived: {}
        };
    }

    function saveDraft() {
        if (!site.safeSetSessionStorage) {
            return;
        }
        try {
            site.safeSetSessionStorage(ONBOARDING_DRAFT_KEY, JSON.stringify({
                currentStepKey: state.currentStepKey,
                data: normalizeOnboardingData(getData())
            }));
        } catch (error) {
            return;
        }
    }

    function mergeResponseWithDraft(response) {
        var draft = readDraft();
        var merged = response && typeof response === 'object' ? JSON.parse(JSON.stringify(response)) : {};
        var mergedData;

        if (!draft || !draft.data || typeof draft.data !== 'object') {
            return merged;
        }

        if (!merged.data || typeof merged.data !== 'object') {
            merged.data = {};
        }
        merged.data = normalizeOnboardingData(merged.data);
        mergedData = merged.data;

        Object.keys(draft.data).forEach(function (field) {
            if (isEmptyDraftValue(mergedData[field]) && !isEmptyDraftValue(draft.data[field])) {
                mergedData[field] = draft.data[field];
            }
        });

        merged.data = normalizeOnboardingData(merged.data);

        return merged;
    }

    function inferResumeStepFromData(data) {
        var questionSteps = STEPS.filter(function (step) {
            return step.key !== 'splash' && step.key !== 'coach_intro' && step.key !== 'analyzing' && isStepVisible(step, data);
        });
        var index;

        for (index = 0; index < questionSteps.length; index += 1) {
            if (!validateStepValue(questionSteps[index], data).ok) {
                return questionSteps[index].key;
            }
        }

        return 'schedule';
    }

    function setFeedback(text, isError) {
        state.feedbackText = text || '';
        state.feedbackError = !!isError;
        var node = document.getElementById('onboarding-feedback');
        if (!node) {
            return;
        }
        node.textContent = state.feedbackText;
        node.classList.toggle('is-error', state.feedbackError);
    }

    function payloadForStep(step) {
        var data = getData();
        if (!step || step.key === 'splash' || step.key === 'coach_intro' || step.key === 'analyzing') {
            return null;
        }
        if (step.key === 'schedule') {
            return {
                training_days: data.training_days || [],
                reminders_enabled: !!data.reminders_enabled,
                reminder_time_local: data.reminder_time_local || null
            };
        }
        var payload = {};
        payload[step.field] = data[step.field];
        return payload;
    }

    function signatureForStep(step, payload) {
        return step.key + ':' + JSON.stringify(payload || {});
    }

    function buildOnboardingPayload() {
        var data = getData();
        return {
            main_goal: data.main_goal || null,
            motivation: data.motivation || null,
            desired_outcome: data.desired_outcome || null,
            focus_area: data.focus_area || null,
            gender: data.gender || null,
            current_body_shape: data.current_body_shape || null,
            target_body_shape: data.target_body_shape || null,
            age: normalizeNumericFieldValue('age', data.age),
            height_cm: normalizeNumericFieldValue('height_cm', data.height_cm),
            current_weight_kg: normalizeNumericFieldValue('current_weight_kg', data.current_weight_kg),
            target_weight_kg: normalizeNumericFieldValue('target_weight_kg', data.target_weight_kg),
            fitness_level: data.fitness_level || null,
            activity_level: data.activity_level || null,
            goal_pace: data.goal_pace || null,
            training_frequency: normalizeNumericFieldValue('training_frequency', data.training_frequency),
            calorie_tracking: data.calorie_tracking || null,
            diet_type: data.diet_type || null,
            self_image: data.self_image || null,
            reminders_enabled: !!data.reminders_enabled,
            reminder_time_local: data.reminders_enabled ? (data.reminder_time_local || DEFAULT_REMINDER_TIME) : null,
            interest_tags: normalizeArrayFieldValue('interest_tags', data.interest_tags || []),
            equipment_tags: normalizeArrayFieldValue('equipment_tags', data.equipment_tags || []),
            injury_areas: normalizeArrayFieldValue('injury_areas', data.injury_areas || []),
            training_days: reconcileTrainingDays(data.training_days || [], data.training_frequency)
        };
    }

    function sendJsonNoRedirect(url, method, payload, fallbackMessage) {
        function runRequest() {
            return site.fetchJsonWithRetry(
                url,
                {
                    method: method,
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(payload)
                },
                { retries: 2, delayMs: 400, backoffMultiplier: 2 }
            );
        }

        function warmTelegramSession() {
            return site.ensureAuthenticatedSession({ allowTelegram: true, redirectOnFail: false })
                .catch(function () {
                    return site.authenticateWithTelegram();
                })
                .catch(function () {
                    return null;
                })
                .then(function () {
                    return null;
                });
        }

        function finalize(result) {
            if (result.response.status === 401) {
                var authError = new Error('AUTH_REQUIRED');
                authError.code = 'AUTH_REQUIRED';
                throw authError;
            }
            if (!result.response.ok) {
                throw new Error(site.parseApiError(result.data, fallbackMessage || 'Не удалось выполнить запрос.'));
            }
            return result.data;
        }

        return warmTelegramSession().then(function () {
            return runRequest().then(function (result) {
                if (result.response.status !== 401) {
                    return finalize(result);
                }
                return site.ensureAuthenticatedSession({ allowTelegram: true, redirectOnFail: false })
                    .catch(function () {
                        return site.authenticateWithTelegram();
                    })
                    .then(function () {
                        return runRequest().then(function (retryResult) {
                            return finalize(retryResult);
                        });
                    });
            });
        });
    }

    function persistAllData(silent) {
        var payload = buildOnboardingPayload();
        var signature = 'all:' + JSON.stringify(payload);
        if (state.savedSignatures.all === signature) {
            if (!silent) {
                setFeedback('Черновик сохранён.', false);
            }
            return Promise.resolve(state.onboarding);
        }

        state.isSaving = true;
        if (!silent) {
            setFeedback('Сохраняю черновик…', false);
        }

        return sendJsonNoRedirect('/api/onboarding', 'PATCH', payload, 'Не удалось сохранить шаг.')
            .then(function (response) {
                state.isSaving = false;
                state.onboarding = response;
                state.savedSignatures.all = signature;
                saveDraft();
                if (!silent) {
                    setFeedback('Черновик сохранён.', false);
                }
                return response;
            })
            .catch(function (error) {
                state.isSaving = false;
                if (error && error.code === 'AUTH_REQUIRED') {
                    saveDraft();
                    if (!silent) {
                        setFeedback('Черновик сохранён локально. Можно продолжать без авторизации.', false);
                    }
                    return state.onboarding;
                }
                setFeedback(error.message || 'Не удалось сохранить шаг.', true);
                throw error;
            });
    }

    function persistCurrentStep(silent) {
        var step = getCurrentStep();
        var payload = payloadForStep(step);
        if (!payload) {
            return Promise.resolve(state.onboarding);
        }

        var signature = signatureForStep(step, payload);
        if (state.savedSignatures[step.key] === signature) {
            if (!silent) {
                setFeedback('Черновик сохранён.', false);
            }
            return Promise.resolve(state.onboarding);
        }

        state.isSaving = true;
        if (!silent) {
            setFeedback('Сохраняю черновик…', false);
        }

        return sendJsonNoRedirect('/api/onboarding', 'PATCH', payload, 'Не удалось сохранить шаг.')
            .then(function (response) {
                state.isSaving = false;
                state.onboarding = response;
                state.savedSignatures[step.key] = signature;
                saveDraft();
                if (!silent) {
                    setFeedback('Черновик сохранён.', false);
                }
                return response;
            })
            .catch(function (error) {
                state.isSaving = false;
                if (error && error.code === 'AUTH_REQUIRED') {
                    saveDraft();
                    if (!silent) {
                        setFeedback('Черновик сохранён локально. Можно продолжать без авторизации.', false);
                    }
                    return state.onboarding;
                }
                setFeedback(error.message || 'Не удалось сохранить шаг.', true);
                throw error;
            });
    }

    function nextStepKey(currentKey) {
        var index = STEP_INDEX[currentKey];
        if (typeof index !== 'number') {
            return STEPS[STEPS.length - 1].key;
        }
        for (var nextIndex = index + 1; nextIndex < STEPS.length; nextIndex += 1) {
            if (isStepVisible(STEPS[nextIndex], getData())) {
                return STEPS[nextIndex].key;
            }
        }
        return STEPS[STEPS.length - 1].key;
    }

    function previousStepKey(currentKey) {
        var index = STEP_INDEX[currentKey];
        if (typeof index !== 'number' || index <= 0) {
            return 'splash';
        }
        for (var prevIndex = index - 1; prevIndex >= 0; prevIndex -= 1) {
            if (isStepVisible(STEPS[prevIndex], getData())) {
                return STEPS[prevIndex].key;
            }
        }
        return 'splash';
    }

    function getSectionSteps(section) {
        return STEPS.filter(function (step) {
            return step.section === section && isStepVisible(step, getData());
        });
    }

    function isProgressQuestionStep(step) {
        return !!(step && step.section);
    }

    function validateStepValue(step, data) {
        var value;

        if (!step || step.key === 'splash' || step.key === 'coach_intro' || step.key === 'analyzing') {
            return { ok: true };
        }

        if (step.key === 'schedule') {
            var selectedDays = normalizeArrayFieldValue('training_days', data.training_days || []);
            var frequency = Number(data.training_frequency || 0);
            if (!selectedDays.length) {
                return { ok: false, message: 'Выберите тренировочные дни.' };
            }
            if (!frequency) {
                return { ok: false, message: 'Сначала выберите частоту тренировок.' };
            }
            if (selectedDays.length !== frequency) {
                return { ok: false, message: 'Количество дней должно совпадать с выбранной частотой.' };
            }
            if (data.reminders_enabled && !data.reminder_time_local) {
                return { ok: false, message: 'Укажите время напоминания.' };
            }
            return { ok: true };
        }

        if (step.type === 'multi') {
            value = data[step.field] || [];
            if (!value.length) {
                return { ok: false, message: 'Выберите хотя бы один вариант.' };
            }
            if (step.key === 'interest_tags' && value.length > step.maxSelect) {
                return { ok: false, message: 'Можно выбрать максимум 3 формата.' };
            }
            if ((step.key === 'equipment_tags' || step.key === 'injury_areas') && value.indexOf('none') >= 0 && value.length > 1) {
                return { ok: false, message: 'Вариант «Нет» нельзя сочетать с другими.' };
            }
            return { ok: true };
        }

        value = data[step.field];
        if (value === null || value === undefined || value === '') {
            return { ok: false, message: step.type === 'metric' ? 'Введите значение.' : 'Выберите вариант ответа.' };
        }
        return { ok: true };
    }

    function isStepAnswered(step, data) {
        return isProgressQuestionStep(step) && validateStepValue(step, data).ok;
    }

    function getSectionProgressRatio(section, currentStep) {
        var steps = getSectionSteps(section).filter(isProgressQuestionStep);
        if (!steps.length) {
            return section < currentStep.section ? 1 : 0;
        }
        if (section < currentStep.section) {
            return 1;
        }
        if (section > currentStep.section) {
            return 0;
        }
        var currentIndex = steps.findIndex(function (item) {
            return item.key === currentStep.key;
        });
        var visibleSteps = currentIndex >= 0 ? steps.slice(0, currentIndex + 1) : steps;
        var completedVisibleCount = visibleSteps.reduce(function (count, item) {
            return count + (isStepAnswered(item, getData()) ? 1 : 0);
        }, 0);
        return completedVisibleCount / steps.length;
    }

    function nextButtonLabel(step) {
        if (step.key === 'splash') {
            return state.onboarding && state.onboarding.status === 'in_progress' ? 'Продолжить' : 'НАЧАТЬ';
        }
        if (step.key === 'coach_intro') {
            return 'НАЧАТЬ!';
        }
        if (step.key === 'analyzing') {
            return 'ПОЛУЧИТЬ МОЙ ПЛАН';
        }
        return 'ДАЛЕЕ';
    }

    function renderIcon(name, className) {
        var cls = className ? ' class="' + className + '"' : '';
        var stroke = 'currentColor';
        if (name === 'arrow-next') {
            return '<svg' + cls + ' viewBox="0 0 24 24" fill="none"><path d="M9 6L15 12L9 18" stroke="' + stroke + '" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"/></svg>';
        }
        if (name === 'rocket') {
            return '<svg' + cls + ' viewBox="0 0 24 24" fill="none"><path d="M14.5 4.5C17 5 19 7 19.5 9.5L13 16L8 17L9 12L14.5 4.5Z" stroke="' + stroke + '" stroke-width="1.8" stroke-linejoin="round"/><path d="M7 13L5 15" stroke="' + stroke + '" stroke-width="1.8" stroke-linecap="round"/><path d="M10 16L8 18" stroke="' + stroke + '" stroke-width="1.8" stroke-linecap="round"/></svg>';
        }
        if (name === 'zap') {
            return '<svg' + cls + ' viewBox="0 0 24 24" fill="none"><path d="M12 4V12" stroke="' + stroke + '" stroke-width="1.8" stroke-linecap="round"/><path d="M9 9L12 4L15 9" stroke="' + stroke + '" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"/><path d="M8 14H16" stroke="' + stroke + '" stroke-width="1.8" stroke-linecap="round"/><path d="M9 20H15" stroke="' + stroke + '" stroke-width="1.8" stroke-linecap="round"/></svg>';
        }
        if (name === 'bolt' || name === 'flash') {
            return '<svg' + cls + ' viewBox="0 0 24 24" fill="none"><path d="M13 2L5 13H11L10.5 22L19 10.5H13.2L13 2Z" stroke="' + stroke + '" stroke-width="1.8" stroke-linejoin="round"/></svg>';
        }
        if (name === 'seat') {
            return '<svg' + cls + ' viewBox="0 0 24 24" fill="none"><path d="M8 5V12C8 14 9.6 15.6 11.6 15.6H16.5" stroke="' + stroke + '" stroke-width="1.8" stroke-linecap="round"/><path d="M8 11H5.5C4.7 11 4 11.7 4 12.5V17.5" stroke="' + stroke + '" stroke-width="1.8" stroke-linecap="round"/><path d="M17 15.5V19" stroke="' + stroke + '" stroke-width="1.8" stroke-linecap="round"/></svg>';
        }
        if (name === 'walk' || name === 'run' || name === 'person') {
            return '<svg' + cls + ' viewBox="0 0 24 24" fill="none"><circle cx="12" cy="4.8" r="2.3" fill="currentColor"/><path d="M12 8.2L8 11.5" stroke="' + stroke + '" stroke-width="1.8" stroke-linecap="round"/><path d="M12 8.2L16 11.2" stroke="' + stroke + '" stroke-width="1.8" stroke-linecap="round"/><path d="M11.6 9.3L12.8 14.6L16.2 19" stroke="' + stroke + '" stroke-width="1.8" stroke-linecap="round"/><path d="M11.3 9.5L9 15" stroke="' + stroke + '" stroke-width="1.8" stroke-linecap="round"/><path d="M9 15L6.8 18.8" stroke="' + stroke + '" stroke-width="1.8" stroke-linecap="round"/></svg>';
        }
        if (name === 'lotus') {
            return '<svg' + cls + ' viewBox="0 0 24 24" fill="none"><path d="M12 8C9.7 9.4 8 11.6 8 14C8 15.8 9.4 17 12 17C14.6 17 16 15.8 16 14C16 11.6 14.3 9.4 12 8Z" stroke="' + stroke + '" stroke-width="1.8"/><path d="M6 12.8C4.8 13.7 4 14.9 4 16.1C4 17.6 5.4 18.7 7.6 18.7C8.4 18.7 9.2 18.5 10 18.1" stroke="' + stroke + '" stroke-width="1.8" stroke-linecap="round"/><path d="M18 12.8C19.2 13.7 20 14.9 20 16.1C20 17.6 18.6 18.7 16.4 18.7C15.6 18.7 14.8 18.5 14 18.1" stroke="' + stroke + '" stroke-width="1.8" stroke-linecap="round"/></svg>';
        }
        if (name === 'timer') {
            return '<svg' + cls + ' viewBox="0 0 24 24" fill="none"><circle cx="12" cy="13" r="7.5" stroke="' + stroke + '" stroke-width="1.8"/><path d="M12 13L15.5 11" stroke="' + stroke + '" stroke-width="1.8" stroke-linecap="round"/><path d="M9.5 3H14.5" stroke="' + stroke + '" stroke-width="1.8" stroke-linecap="round"/></svg>';
        }
        if (name === 'pilates') {
            return '<svg' + cls + ' viewBox="0 0 24 24" fill="none"><path d="M4 15C7 15 8.5 13 10 10.5C11 8.8 12.5 8 15.2 8H20" stroke="' + stroke + '" stroke-width="1.8" stroke-linecap="round"/><path d="M7 17L5 20" stroke="' + stroke + '" stroke-width="1.8" stroke-linecap="round"/><path d="M12 12L15 19" stroke="' + stroke + '" stroke-width="1.8" stroke-linecap="round"/></svg>';
        }
        if (name === 'chair') {
            return '<svg' + cls + ' viewBox="0 0 24 24" fill="none"><path d="M7 4V11" stroke="' + stroke + '" stroke-width="1.8" stroke-linecap="round"/><path d="M7 11H15" stroke="' + stroke + '" stroke-width="1.8" stroke-linecap="round"/><path d="M15 11V8" stroke="' + stroke + '" stroke-width="1.8" stroke-linecap="round"/><path d="M5 20V14C5 12.9 5.9 12 7 12H17V20" stroke="' + stroke + '" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"/></svg>';
        }
        if (name === 'dumbbell') {
            return '<svg' + cls + ' viewBox="0 0 24 24" fill="none"><path d="M4 10V14" stroke="' + stroke + '" stroke-width="1.8" stroke-linecap="round"/><path d="M7 8V16" stroke="' + stroke + '" stroke-width="1.8" stroke-linecap="round"/><path d="M10 11H14" stroke="' + stroke + '" stroke-width="1.8" stroke-linecap="round"/><path d="M17 8V16" stroke="' + stroke + '" stroke-width="1.8" stroke-linecap="round"/><path d="M20 10V14" stroke="' + stroke + '" stroke-width="1.8" stroke-linecap="round"/></svg>';
        }
        if (name === 'band') {
            return '<svg' + cls + ' viewBox="0 0 24 24" fill="none"><path d="M7 8C7 6.3 8.3 5 10 5C11.7 5 13 6.3 13 8V16C13 17.7 11.7 19 10 19C8.3 19 7 17.7 7 16V8Z" stroke="' + stroke + '" stroke-width="1.8"/><path d="M11 9L17 9C18.7 9 20 10.3 20 12C20 13.7 18.7 15 17 15L11 15" stroke="' + stroke + '" stroke-width="1.8" stroke-linecap="round"/></svg>';
        }
        if (name === 'gym') {
            return '<svg' + cls + ' viewBox="0 0 24 24" fill="none"><path d="M4 19V10.5C4 8.6 5.6 7 7.5 7H16.5C18.4 7 20 8.6 20 10.5V19" stroke="' + stroke + '" stroke-width="1.8" stroke-linecap="round"/><path d="M8 7V5" stroke="' + stroke + '" stroke-width="1.8" stroke-linecap="round"/><path d="M16 7V5" stroke="' + stroke + '" stroke-width="1.8" stroke-linecap="round"/><path d="M7 19V14H17V19" stroke="' + stroke + '" stroke-width="1.8" stroke-linejoin="round"/></svg>';
        }
        if (name === 'stretch') {
            return '<svg' + cls + ' viewBox="0 0 24 24" fill="none"><circle cx="12" cy="5" r="2.1" fill="currentColor"/><path d="M12 8L9 12" stroke="' + stroke + '" stroke-width="1.8" stroke-linecap="round"/><path d="M12 8L15 12" stroke="' + stroke + '" stroke-width="1.8" stroke-linecap="round"/><path d="M9 12L4.5 14" stroke="' + stroke + '" stroke-width="1.8" stroke-linecap="round"/><path d="M15 12L19.5 14" stroke="' + stroke + '" stroke-width="1.8" stroke-linecap="round"/><path d="M12 10.5V19" stroke="' + stroke + '" stroke-width="1.8" stroke-linecap="round"/></svg>';
        }
        if (name === 'none') {
            return '<svg' + cls + ' viewBox="0 0 24 24" fill="none"><path d="M8 5L16 19" stroke="' + stroke + '" stroke-width="1.8" stroke-linecap="round"/><path d="M16 5L8 19" stroke="' + stroke + '" stroke-width="1.8" stroke-linecap="round"/></svg>';
        }
        if (name === 'shoulders') {
            return '<svg' + cls + ' viewBox="0 0 24 24" fill="none"><path d="M5 14C7.4 11.2 9.3 10 12 10C14.7 10 16.6 11.2 19 14" stroke="' + stroke + '" stroke-width="1.8" stroke-linecap="round"/><path d="M7 8.5C7.8 6.8 9.2 6 10.8 6" stroke="' + stroke + '" stroke-width="1.8" stroke-linecap="round"/><path d="M17 8.5C16.2 6.8 14.8 6 13.2 6" stroke="' + stroke + '" stroke-width="1.8" stroke-linecap="round"/></svg>';
        }
        if (name === 'wrist') {
            return '<svg' + cls + ' viewBox="0 0 24 24" fill="none"><path d="M8 8L16 16" stroke="' + stroke + '" stroke-width="1.8" stroke-linecap="round"/><path d="M12 4L18 10" stroke="' + stroke + '" stroke-width="1.8" stroke-linecap="round"/><path d="M6 10L14 18" stroke="' + stroke + '" stroke-width="1.8" stroke-linecap="round"/><path d="M5 16L9 20" stroke="' + stroke + '" stroke-width="1.8" stroke-linecap="round"/></svg>';
        }
        if (name === 'knee') {
            return '<svg' + cls + ' viewBox="0 0 24 24" fill="none"><path d="M10 4C10 9 12 11 12 15C12 18.3 10.2 20 7.5 20" stroke="' + stroke + '" stroke-width="1.8" stroke-linecap="round"/><path d="M12 15H17.5" stroke="' + stroke + '" stroke-width="1.8" stroke-linecap="round"/><path d="M17.5 15C18.8 15 20 16.2 20 17.5C20 18.9 18.9 20 17.5 20H15" stroke="' + stroke + '" stroke-width="1.8" stroke-linecap="round"/></svg>';
        }
        if (name === 'ankle') {
            return '<svg' + cls + ' viewBox="0 0 24 24" fill="none"><path d="M8 4V12C8 15.3 10.7 18 14 18H18" stroke="' + stroke + '" stroke-width="1.8" stroke-linecap="round"/><path d="M8 13L5 17" stroke="' + stroke + '" stroke-width="1.8" stroke-linecap="round"/><path d="M18 18C19.7 18 21 19.3 21 21H13" stroke="' + stroke + '" stroke-width="1.8" stroke-linecap="round"/></svg>';
        }
        return '<svg' + cls + ' viewBox="0 0 24 24" fill="none"><circle cx="12" cy="12" r="9" stroke="' + stroke + '" stroke-width="1.8"/></svg>';
    }

    function renderProgress(step) {
        if (!step.section) {
            return '';
        }
        var meta = SECTION_META[step.section];
        var sections = [1, 2, 3];
        return [
            '<div class="fi-progress-meta"><span class="fi-progress-number">', escapeHtml(meta.number), '</span> ', escapeHtml(meta.label), '</div>',
            '<div class="fi-progress-rail">',
            sections.map(function (section, index) {
                var ratio = Math.max(0, Math.min(1, getSectionProgressRatio(section, step)));
                var dividerClass = section < step.section ? ' fi-progress-divider--complete' : '';
                return [
                    '<span class="fi-progress-stage"><span class="fi-progress-stage-fill" style="width:', escapeHtml(String(Math.round(ratio * 1000) / 10)), '%;"></span></span>',
                    index < sections.length - 1 ? '<span class="fi-progress-divider' + dividerClass + '"></span>' : ''
                ].join('');
            }).join(''),
            '</div>'
        ].join('');
    }

    function renderHeader(step) {
        var canGoBack = step.key !== 'splash' && step.key !== 'analyzing';
        return [
            '<header class="fi-topbar">',
            canGoBack ? '<button id="onboarding-back-btn" class="fi-back-btn" type="button" aria-label="Назад">' + renderIcon('arrow-next', 'fi-back-icon fi-back-icon--left') + '</button>' : '<span class="fi-back-spacer"></span>',
            '<div class="fi-topbar-copy">', renderProgress(step), '</div>',
            '</header>'
        ].join('');
    }

    function renderScreen(step, contentHtml, options) {
        var extraClass = options && options.extraClass ? ' ' + options.extraClass : '';
        return [
            '<div class="fi-shell', extraClass, '" data-step-key="', escapeHtml(step.key), '">',
            renderHeader(step),
            '<main class="fi-main">',
            '<section class="fi-question-head">',
            '<h1 class="fi-title">', escapeHtml(step.title), '</h1>',
            step.helper ? '<p class="fi-subtitle">' + escapeHtml(step.helper) + '</p>' : '',
            '</section>',
            '<section class="fi-content">', contentHtml, '</section>',
            '</main>',
            '<footer class="fi-footer">',
            '<p id="onboarding-feedback" class="fi-feedback ', state.feedbackError ? 'is-error' : '', '">', escapeHtml(state.feedbackText), '</p>',
            '<button id="onboarding-next-btn" class="fi-primary-btn" type="button" ', state.isSaving ? 'disabled' : '', '>', escapeHtml(nextButtonLabel(step)), '</button>',
            '</footer>',
            '</div>'
        ].join('');
    }

    function renderIndicator(isSelected) {
        return '<span class="fi-card-indicator ' + (isSelected ? 'is-selected' : '') + '">' + (isSelected ? '<span class="fi-card-indicator-dot"></span>' : '') + '</span>';
    }

    function renderOptionBullet(isSelected) {
        return '<span class="fi-option-bullet ' + (isSelected ? 'is-selected' : '') + '"></span>';
    }

    function renderGoalCards(step) {
        var value = getData()[step.field];
        return '<div class="fi-goal-stack">' + step.options.map(function (option) {
            return [
                '<button class="fi-goal-card ', value === option.value ? 'is-selected' : '', '" type="button" data-choice-value="', option.value, '">',
                '<div class="fi-goal-card-copy"><span class="fi-goal-card-title">', escapeHtml(option.title), '</span></div>',
                renderIndicator(value === option.value),
                '</button>'
            ].join('');
        }).join('') + '</div>';
    }

    function renderIconList(step, isMulti) {
        var selectedValues = isMulti ? (getData()[step.field] || []) : [];
        var selectedValue = isMulti ? '' : getData()[step.field];
        return '<div class="fi-option-stack">' + step.options.map(function (option) {
            var isSelected = isMulti ? selectedValues.indexOf(option.value) >= 0 : selectedValue === option.value;
            return [
                '<button class="fi-option-card ', isSelected ? 'is-selected' : '', '" type="button" data-choice-value="', option.value, '">',
                renderOptionBullet(isSelected),
                '<span class="fi-option-copy"><span class="fi-option-title">', escapeHtml(option.title), '</span>',
                option.description ? '<span class="fi-option-description">' + escapeHtml(option.description) + '</span>' : '',
                '</span>',
                '</button>'
            ].join('');
        }).join('') + '</div>';
    }

    function renderFocusArea(step) {
        var value = getData()[step.field] || '';
        return '<div class="fi-focus-grid">' + step.options.map(function (option) {
            var isSelected = value === option.value;
            return [
                '<button class="fi-focus-label ',
                isSelected ? 'is-selected ' : '',
                'fi-focus-label--', option.value.replace(/_/g, '-'), ' ',
                option.value === 'full_body' ? 'fi-focus-label--wide' : '',
                '" type="button" data-choice-value="', option.value, '">',
                '<span class="fi-focus-label-copy">', escapeHtml(option.title), '</span>',
                renderIndicator(isSelected),
                '</button>'
            ].join('');
        }).join('') + '</div>';
    }

    function renderGender(step) {
        var value = getData()[step.field];
        return [
            '<div class="fi-gender-grid">',
            step.options.map(function (option) {
                var isSelected = value === option.value;
                return [
                    '<button class="fi-gender-card ', isSelected ? 'is-selected' : '', '" type="button" data-choice-value="', option.value, '">',
                    renderIndicator(isSelected),
                    '<span class="fi-gender-card-media"><img src="', escapeHtml(option.image), '" alt="', escapeHtml(option.title), '"></span>',
                    '<span class="fi-gender-card-label">', escapeHtml(option.title), '</span>',
                    '</button>'
                ].join('');
            }).join(''),
            '</div>'
        ].join('');
    }

    function renderMetricUnitPills(step) {
        var config = getMetricConfig(step);
        if (!config) {
            return '';
        }
        return Object.keys(config.units).map(function (unit) {
            return '<button class="fi-unit-pill ' + (getMetricDisplayUnit(step) === unit ? 'is-active' : '') + '" type="button" data-metric-unit="' + unit + '">' + escapeHtml(config.units[unit].label) + '</button>';
        }).join('');
    }

    function renderMetricInsight(step) {
        if (step.insight !== 'bmi') {
            return '';
        }
        var derived = getDerived();
        return [
            '<article class="fi-insight-card fi-insight-card--metric">',
            '<div class="fi-insight-card-head">Текущий ИМТ <span class="fi-info-dot">i</span></div>',
            '<div class="fi-insight-card-metric"><span id="metric-bmi-value">', typeof derived.bmi === 'number' ? escapeHtml(String(derived.bmi)) : '—', '</span> <span id="metric-bmi-label">(', escapeHtml(derived.bmi_label || 'Без оценки'), ')</span></div>',
            '<p id="metric-bmi-copy">', typeof derived.bmi === 'number' ? 'После сохранения можно корректнее оценить стартовую точку.' : 'После сохранения покажем точную оценку по текущим данным.', '</p>',
            '</article>'
        ].join('');
    }

    function renderAgeMetric(step) {
        var liveValue = getMetricLiveDisplayValue(step);
        var values = buildMetricWheelValues(step);
        return [
            '<div class="fi-age-stage">',
            '<div class="fi-wheel-shell fi-wheel-shell--age">',
            '<div class="fi-wheel-fade fi-wheel-fade--top"></div>',
            '<div class="fi-wheel-fade fi-wheel-fade--bottom"></div>',
            '<div class="fi-wheel-selection-window fi-wheel-selection-window--age-inline"></div>',
            '<div id="metric-wheel" class="fi-wheel-picker fi-wheel-picker--age" data-wheel-field="' + escapeHtml(step.field) + '" data-wheel-step="' + escapeHtml(String(step.step)) + '">' + renderMetricWheelItems(values, liveValue, 'fi-wheel-item') + '</div>',
            '</div>',
            '<p class="fi-age-caption">Проведите, чтобы выбрать год рождения.</p>',
            '</div>'
        ].join('');
    }

    function renderMetricRuler(step) {
        var liveValue = getMetricLiveDisplayValue(step);
        var values = buildMetricWheelValues(step);
        var currentUnit = getMetricDisplayUnit(step);
        return [
            '<div class="fi-unit-toggle">', renderMetricUnitPills(step), '</div>',
            '<div class="fi-height-layout">',
            '<div class="fi-height-panel">',
            '<div class="fi-height-value"><strong id="metric-live-value">', escapeHtml(formatMetricDisplayText(liveValue)), '</strong><span id="metric-live-unit" class="fi-height-unit">', escapeHtml(currentUnit), '</span></div>',
            '</div>',
            '<div class="fi-height-ruler-shell">',
            '<div class="fi-wheel-fade fi-wheel-fade--top"></div>',
            '<div class="fi-wheel-fade fi-wheel-fade--bottom"></div>',
            '<div class="fi-height-ruler-current-line"></div>',
            '<div id="metric-wheel" class="fi-height-ruler-picker" data-wheel-field="', escapeHtml(step.field), '">', renderMetricRulerItems(step, values, liveValue), '</div>',
            '</div>',
            '</div>'
        ].join('');
    }

    function renderWeightRuler(step) {
        var data = getData();
        var liveValue = getMetricLiveDisplayValue(step);
        var values = buildMetricWheelValues(step);
        var currentUnit = getMetricDisplayUnit(step);
        return [
            '<div class="fi-unit-toggle">', renderMetricUnitPills(step), '</div>',
            '<div class="fi-ruler-metric-head fi-ruler-metric-head--weight">',
            '<div class="fi-ruler-metric-value"><strong id="metric-live-value">', escapeHtml(formatMetricDisplayText(liveValue)), '</strong><span id="metric-live-unit" class="fi-ruler-unit">', escapeHtml(currentUnit), '</span></div>',
            step.displayMode === 'weight-target' && data.current_weight_kg ? '<span class="fi-ruler-side-badge">' + escapeHtml(Number(data.current_weight_kg).toFixed(1)) + '</span>' : '',
            '</div>',
            '<div class="fi-weight-ruler-shell">',
            '<div class="fi-weight-ruler-current-line"></div>',
            '<div id="metric-wheel" class="fi-weight-ruler-picker" data-wheel-field="', escapeHtml(step.field), '" data-wheel-axis="x">', renderWeightRulerItems(step, values, liveValue), '</div>',
            '</div>',
            renderMetricInsight(step)
        ].join('');
    }

    function renderMetricStep(step) {
        if (step.displayMode === 'birth-year-wheel') {
            return renderAgeMetric(step);
        }
        if (step.displayMode === 'height') {
            return renderMetricRuler(step);
        }
        if (step.displayMode === 'weight-current' || step.displayMode === 'weight-target') {
            return renderWeightRuler(step);
        }
        return '';
    }

    function frequencyDescription(value) {
        if (value <= 2) {
            return 'Спокойный режим, который проще встроить в неделю.';
        }
        if (value <= 4) {
            return 'Комфортный ритм для заметного прогресса.';
        }
        return 'Плотный график с быстрым темпом адаптации.';
    }

    function renderFrequencyStep() {
        var value = Number(getData().training_frequency || 2);
        return [
            '<div class="fi-frequency-hero">',
            '<div class="fi-frequency-calendar"><span class="fi-frequency-calendar-top"></span><strong id="frequency-live-value">', value, '</strong></div>',
            '<div class="fi-frequency-copy"><strong id="frequency-live-title">', value, ' раз(а) в неделю</strong><span id="frequency-live-text">', frequencyDescription(value), '</span></div>',
            '</div>',
            '<div class="fi-frequency-choice-grid">',
            [1, 2, 3, 4, 5, 6].map(function (item) {
                return [
                    '<button class="fi-frequency-choice ', item === value ? 'is-active' : '', '" type="button" data-frequency-value="', item, '">',
                    '<strong>', item, '</strong>',
                    '<span>', item === 1 ? 'раз в неделю' : 'раза в неделю', '</span>',
                    '</button>'
                ].join('');
            }).join(''),
            '</div>'
        ].join('');
    }

    function renderScheduleStep() {
        ensureScheduleDefaults();
        var data = getData();
        var selectedDays = data.training_days || [];
        var remindersEnabled = !!data.reminders_enabled;
        return [
            '<div class="fi-day-grid">',
            DAYS.map(function (day) {
                var selected = selectedDays.indexOf(day.value) >= 0;
                return '<button class="fi-day-pill ' + (selected ? 'is-selected' : '') + '" type="button" data-day-value="' + day.value + '">' + escapeHtml(day.label) + '</button>';
            }).join(''),
            '</div>',
            '<div class="fi-reminder-divider"></div>',
            '<div class="fi-reminder-row">',
            '<div><strong>Напоминания</strong><span>Помогут держать режим без пропусков</span></div>',
            '<label class="fi-switch"><input id="reminders-toggle" type="checkbox" ' + (remindersEnabled ? 'checked' : '') + '><span></span></label>',
            '</div>',
            '<label id="reminder-time-row" class="fi-time-card ' + (remindersEnabled ? '' : 'is-hidden') + '"><span>Время напоминания</span><input id="reminder-time-input" type="time" value="' + escapeHtml(data.reminder_time_local || '06:58') + '"></label>'
        ].join('');
    }

    function analysisItemProgress(index, totalItems) {
        if (!totalItems) {
            return 100;
        }
        var slotSize = 100 / totalItems;
        var slotStart = index * slotSize;
        return Math.max(0, Math.min(100, Math.round(((state.analysisProgress - slotStart) / slotSize) * 100)));
    }

    function isAnalysisAnimationComplete() {
        return state.analysisProgress >= 100;
    }

    function isAnalysisComplete() {
        return isAnalysisAnimationComplete() && state.analysisRequestComplete;
    }

    function renderAnalyzingStep() {
        var items = getDerived().analysis_items || [];
        var totalPercent = Math.max(0, Math.min(100, Math.round(state.analysisProgress)));
        return [
            '<section class="fi-analyze-screen">',
            '<div class="fi-analyze-head">',
            '<img class="fi-analyze-coach" src="', escapeHtml(MEDIA.coachAnalyze), '" alt="Тренер">',
            '<div class="fi-analyze-head-copy">',
            '<span class="fi-analyze-kicker">Персонализация плана</span>',
            '<h1 class="fi-title fi-title--analysis">Тренер работает над вашим запросом</h1>',
            '</div>',
            '</div>',
            '<article class="fi-analyze-summary">',
            '<div class="fi-analyze-summary-row"><span>Готовность плана</span><strong id="analyze-total-percent">', totalPercent, '%</strong></div>',
            '<span class="fi-analyze-total-bar"><span id="analyze-total-bar-fill" style="width:', totalPercent, '%;"></span></span>',
            '</article>',
            '<div class="fi-analyze-list" style="grid-template-rows:repeat(', Math.max(items.length, 1), ', minmax(0, 1fr));">',
            items.map(function (item, index) {
                var percent = analysisItemProgress(index, items.length);
                var stateClass = percent >= 100 ? 'is-complete' : (percent > 0 ? 'is-current' : 'is-pending');
                return [
                    '<article class="fi-analyze-item ', stateClass, '" data-analyze-item="', index, '">',
                    '<div class="fi-analyze-line"><span class="fi-analyze-dot"></span><div class="fi-analyze-copy"><strong>', escapeHtml(item.title), '</strong><em class="fi-analyze-value ', percent >= 45 ? 'is-visible' : '', '" data-analyze-value>', escapeHtml(item.value), '</em></div><small data-analyze-percent>', percent, '%</small></div>',
                    '<span class="fi-analyze-bar"><span data-analyze-bar style="width:', percent, '%;"></span></span>',
                    '</article>'
                ].join('');
            }).join(''),
            '</div>',
            '<div class="fi-analyze-cta">',
            '<button id="onboarding-finish-btn" class="fi-primary-btn fi-primary-btn--mint" type="button" ' + (isAnalysisComplete() ? '' : 'disabled') + '>' + (isAnalysisComplete() ? 'ПОЛУЧИТЬ МОЙ ПЛАН' : 'ГОТОВИМ ПЛАН…') + '</button>',
            '<p id="analyze-cta-note" class="fi-analyze-note">' + (isAnalysisComplete() ? 'План готов. Можно переходить дальше.' : 'Данные появляются по мере заполнения каждой шкалы.') + '</p>',
            '</div>',
            '</section>'
        ].join('');
    }

    function renderSplash() {
        return [
            '<section class="fi-hero-screen">',
            '<div class="fi-hero-copy">',
            '<div class="fi-hero-brand-block">',
            '<div class="fi-hero-chip">ПЕРСОНАЛЬНЫЙ ИИ-ТРЕНЕР</div>',
            '<div class="fi-hero-brand">Kinematics</div>',
            '<p class="fi-hero-subtitle">Персональный ИИ-тренер</p>',
            '<p class="fi-hero-note">План, техника и ежедневный ритм в одном маршруте, который подстраивается под вас.</p>',
            '<div class="fi-hero-pill-row">',
            '<span class="fi-hero-pill">План</span>',
            '<span class="fi-hero-pill">Техника</span>',
            '<span class="fi-hero-pill">Прогресс</span>',
            '</div>',
            '</div>',
            '<div class="fi-hero-actions">',
            '<button id="onboarding-start-btn" class="fi-primary-btn fi-primary-btn--hero" type="button">', escapeHtml(nextButtonLabel(getCurrentStep())), '</button>',
            '</div>',
            '</div>',
            '</section>'
        ].join('');
    }

    function renderCoachIntro() {
        return [
            '<section class="fi-coach-screen">',
            '<div class="fi-coach-top">', renderHeader(getCurrentStep()), '</div>',
            '<div class="fi-coach-body">',
            '<div class="fi-coach-photo-shell"><img class="fi-coach-photo" src="', escapeHtml(MEDIA.coachIntro), '" alt="Тренер"></div>',
            '<h1 class="fi-title">ПРИВЕТ!</h1>',
            '<p class="fi-coach-text">Я ваш личный тренер. У меня есть пара вопросов. Они помогут составить <span>персональный план</span> для вас.</p>',
            '</div>',
            '<footer class="fi-footer fi-footer--coach"><button id="onboarding-start-btn" class="fi-primary-btn fi-primary-btn--mint" type="button">', escapeHtml(nextButtonLabel(getCurrentStep())), '</button></footer>',
            '</section>'
        ].join('');
    }

    function renderChoiceStep(step) {
        if (step.presentation === 'goal-cards') {
            return renderGoalCards(step);
        }
        if (step.presentation === 'focus-map') {
            return renderFocusArea(step);
        }
        if (step.presentation === 'gender-cards') {
            return renderGender(step);
        }
        return renderIconList(step, step.type === 'multi');
    }

    function render() {
        var root = getRoot();
        var step = getCurrentStep();

        if (!root || !step) {
            return;
        }

        document.body.classList.add('onboarding-body');
        document.body.classList.remove('is-onboarding-result');

        if (step.key === 'splash') {
            root.innerHTML = renderSplash();
        } else if (step.key === 'coach_intro') {
            root.innerHTML = renderCoachIntro();
        } else if (step.key === 'analyzing') {
            root.innerHTML = renderAnalyzingStep();
        } else if (step.type === 'metric') {
            root.innerHTML = renderScreen(step, renderMetricStep(step), step.field === 'age' ? { extraClass: 'fi-shell--age' } : null);
        } else if (step.type === 'frequency') {
            root.innerHTML = renderScreen(step, renderFrequencyStep());
        } else if (step.type === 'schedule') {
            root.innerHTML = renderScreen(step, renderScheduleStep());
        } else {
            root.innerHTML = renderScreen(step, renderChoiceStep(step));
        }

        bindCurrentStep();
        setFeedback(state.feedbackText, state.feedbackError);
        if (step.key === 'analyzing') {
            updateAnalyzingUI();
        }
    }

    function updateChoiceSelectionUI(step) {
        var selectedValues = step.type === 'multi' ? (getData()[step.field] || []) : [];
        var selectedValue = step.type === 'multi' ? null : getData()[step.field];
        document.querySelectorAll('[data-choice-value]').forEach(function (button) {
            var buttonValue = button.getAttribute('data-choice-value');
            var isSelected = step.type === 'multi' ? selectedValues.indexOf(buttonValue) >= 0 : selectedValue === buttonValue;
            button.classList.toggle('is-selected', isSelected);
            var indicator = button.querySelector('.fi-card-indicator');
            if (indicator) {
                indicator.classList.toggle('is-selected', isSelected);
                indicator.innerHTML = isSelected ? '<span class="fi-card-indicator-dot"></span>' : '';
            }
        });
        if (step.key === 'focus_area') {
            document.querySelectorAll('[data-focus-point]').forEach(function (point) {
                point.classList.toggle('is-active', point.getAttribute('data-focus-point') === selectedValue);
            });
        }
    }

    function updateFrequencyUI() {
        var value = Number(getData().training_frequency || 2);
        var liveValue = document.getElementById('frequency-live-value');
        var liveTitle = document.getElementById('frequency-live-title');
        var liveText = document.getElementById('frequency-live-text');

        if (liveValue) {
            liveValue.textContent = String(value);
        }
        if (liveTitle) {
            liveTitle.textContent = value + ' раз(а) в неделю';
        }
        if (liveText) {
            liveText.textContent = frequencyDescription(value);
        }

        document.querySelectorAll('[data-frequency-value]').forEach(function (button) {
            button.classList.toggle('is-active', Number(button.getAttribute('data-frequency-value')) === value);
        });
    }

    function updateScheduleUI() {
        var selectedDays = getData().training_days || [];
        document.querySelectorAll('[data-day-value]').forEach(function (button) {
            button.classList.toggle('is-selected', selectedDays.indexOf(button.getAttribute('data-day-value')) >= 0);
        });
        var toggle = document.getElementById('reminders-toggle');
        var timeRow = document.getElementById('reminder-time-row');
        if (toggle) {
            toggle.checked = !!getData().reminders_enabled;
        }
        if (timeRow) {
            timeRow.classList.toggle('is-hidden', !getData().reminders_enabled);
        }
    }

    function scrollMetricWheelToValue(step, displayValue) {
        var wheel = document.getElementById('metric-wheel');
        if (!wheel) {
            return;
        }

        var axis = wheel.getAttribute('data-wheel-axis') === 'x' ? 'x' : 'y';
        var items = Array.from(wheel.querySelectorAll('[data-wheel-value]'));
        var targetItem = items[0];

        if (!targetItem) {
            return;
        }

        items.forEach(function (item) {
            if (Math.abs(Number(item.getAttribute('data-wheel-value')) - Number(displayValue)) < 0.001) {
                targetItem = item;
            }
        });

        if (axis === 'x') {
            wheel.scrollLeft = targetItem.offsetLeft - ((wheel.clientWidth - targetItem.offsetWidth) / 2);
            return;
        }
        wheel.scrollTop = targetItem.offsetTop - ((wheel.clientHeight - targetItem.offsetHeight) / 2);
    }

    function updateMetricInsightUI(step) {
        if (!step || step.insight !== 'bmi') {
            return;
        }
        var derived = getDerived();
        var bmiValue = document.getElementById('metric-bmi-value');
        var bmiLabel = document.getElementById('metric-bmi-label');
        var bmiCopy = document.getElementById('metric-bmi-copy');

        if (bmiValue) {
            bmiValue.textContent = typeof derived.bmi === 'number' ? String(derived.bmi) : '—';
        }
        if (bmiLabel) {
            bmiLabel.textContent = '(' + (derived.bmi_label || 'Без оценки') + ')';
        }
        if (bmiCopy) {
            bmiCopy.textContent = typeof derived.bmi === 'number'
                ? 'После сохранения можно корректнее оценить стартовую точку.'
                : 'После сохранения покажем точную оценку по текущим данным.';
        }
    }

    function updateMetricWheelUI(step, shouldScroll) {
        var displayValue = getMetricLiveDisplayValue(step);
        var liveValue = document.getElementById('metric-live-value');
        var liveUnit = document.getElementById('metric-live-unit');

        if (liveValue) {
            liveValue.textContent = formatMetricDisplayText(displayValue);
        }
        if (liveUnit) {
            liveUnit.textContent = getMetricDisplayUnit(step);
        }

        document.querySelectorAll('#metric-wheel [data-wheel-value]').forEach(function (item) {
            item.classList.toggle('is-selected', Math.abs(Number(item.getAttribute('data-wheel-value')) - Number(displayValue)) < 0.001);
        });

        updateMetricInsightUI(step);
        updateMetricWheelDepth(step);

        if (shouldScroll) {
            scrollMetricWheelToValue(step, displayValue);
            window.requestAnimationFrame(function () {
                updateMetricWheelDepth(step);
            });
        }
    }

    function updateMetricWheelDepth(step) {
        if (!step || step.displayMode !== 'birth-year-wheel') {
            return;
        }

        var wheel = document.getElementById('metric-wheel');
        if (!wheel) {
            return;
        }

        var items = Array.from(wheel.querySelectorAll('[data-wheel-value]'));
        if (!items.length) {
            return;
        }

        var wheelRect = wheel.getBoundingClientRect();
        var wheelCenter = wheelRect.top + (wheelRect.height / 2);

        items.forEach(function (item) {
            var rect = item.getBoundingClientRect();
            var itemCenter = rect.top + (rect.height / 2);
            var distance = Math.abs(itemCenter - wheelCenter) / Math.max(rect.height, 1);

            item.classList.remove('is-near', 'is-mid', 'is-far');
            if (item.classList.contains('is-selected')) {
                return;
            }

            if (distance <= 1.05) {
                item.classList.add('is-near');
                return;
            }
            if (distance <= 1.95) {
                item.classList.add('is-mid');
                return;
            }
            item.classList.add('is-far');
        });
    }

    function scheduleMetricPersist() {
        if (state.metricPersistTimerId) {
            window.clearTimeout(state.metricPersistTimerId);
        }
        state.metricPersistTimerId = window.setTimeout(function () {
            state.metricPersistTimerId = null;
        }, 220);
    }

    function bindChoiceButtons(step) {
        document.querySelectorAll('[data-choice-value]').forEach(function (button) {
            button.addEventListener('click', function () {
                var value = button.getAttribute('data-choice-value');
                if (step.type === 'multi') {
                    toggleMultiValue(step.field, value, step.maxSelect);
                } else {
                    updateLocalData(step.field, value);
                }
                state.feedbackText = '';
                state.feedbackError = false;
                updateChoiceSelectionUI(step);
                setFeedback('', false);
            });
        });
    }

    function toggleMultiValue(field, value, maxSelect) {
        var current = (getData()[field] || []).slice();
        var index = current.indexOf(value);

        if (index >= 0) {
            current.splice(index, 1);
        } else if (value === 'none') {
            current = ['none'];
        } else {
            current = current.filter(function (item) { return item !== 'none'; });
            if (typeof maxSelect === 'number' && current.length >= maxSelect) {
                current.shift();
            }
            current.push(value);
        }

        updateLocalData(field, current);
    }

    function bindMetricControls(step) {
        var wheel = document.getElementById('metric-wheel');
        var wheelValues = buildMetricWheelValues(step);
        var wheelSyncLock = false;

        if (getData()[step.field] === null || getData()[step.field] === undefined || getData()[step.field] === '') {
            updateLocalData(step.field, normalizeMetricValue(step, getMetricLiveDisplayValue(step)));
        }

        function nearestWheelDisplayValue() {
            if (!wheel) {
                return getMetricLiveDisplayValue(step);
            }
            var axis = wheel.getAttribute('data-wheel-axis') === 'x' ? 'x' : 'y';
            var items = Array.from(wheel.querySelectorAll('[data-wheel-value]'));
            if (!items.length) {
                return getMetricLiveDisplayValue(step);
            }

            var wheelRect = wheel.getBoundingClientRect();
            var wheelCenter = axis === 'x'
                ? wheelRect.left + (wheelRect.width / 2)
                : wheelRect.top + (wheelRect.height / 2);
            var nearestValue = wheelValues[0];
            var nearestDistance = Number.POSITIVE_INFINITY;

            items.forEach(function (item) {
                var itemRect = item.getBoundingClientRect();
                var itemCenter = axis === 'x'
                    ? itemRect.left + (itemRect.width / 2)
                    : itemRect.top + (itemRect.height / 2);
                var distance = Math.abs(itemCenter - wheelCenter);
                if (distance < nearestDistance) {
                    nearestDistance = distance;
                    nearestValue = Number(item.getAttribute('data-wheel-value'));
                }
            });

            return nearestValue;
        }

        if (wheel) {
            window.requestAnimationFrame(function () {
                wheelSyncLock = true;
                updateMetricWheelUI(step, true);
                window.requestAnimationFrame(function () {
                    wheelSyncLock = false;
                });
            });

            wheel.addEventListener('scroll', function () {
                if (wheelSyncLock) {
                    return;
                }
                var displayValue = nearestWheelDisplayValue();
                updateLocalData(step.field, normalizeMetricValue(step, displayValue));
                updateMetricWheelUI(step, false);
                setFeedback('', false);
                scheduleMetricPersist();
            }, { passive: true });
        }

        document.querySelectorAll('[data-metric-unit]').forEach(function (button) {
            button.addEventListener('click', function () {
                setMetricDisplayUnit(step, button.getAttribute('data-metric-unit'));
                render();
            });
        });
    }

    function bindFrequencyControls() {
        if (!getData().training_frequency) {
            updateLocalData('training_frequency', 2);
        }
        updateFrequencyUI();

        function applyValue(value, persistAfter) {
            var numericValue = Number(value);
            updateLocalData('training_frequency', numericValue);
            updateLocalData('training_days', reconcileTrainingDays(getData().training_days || [], numericValue));
            updateFrequencyUI();
        }

        document.querySelectorAll('[data-frequency-value]').forEach(function (button) {
            button.addEventListener('click', function () {
                applyValue(button.getAttribute('data-frequency-value'), true);
            });
        });
    }

    function bindScheduleControls() {
        document.querySelectorAll('[data-day-value]').forEach(function (button) {
            button.addEventListener('click', function () {
                var selectedDays = (getData().training_days || []).slice();
                var value = button.getAttribute('data-day-value');
                var index = selectedDays.indexOf(value);
                var maxDays = Number(getData().training_frequency || 0);

                if (index >= 0) {
                    selectedDays.splice(index, 1);
                } else if (selectedDays.length < maxDays) {
                    selectedDays.push(value);
                } else if (maxDays > 0) {
                    selectedDays = maxDays === 1
                        ? [value]
                        : selectedDays.slice(1).concat(value);
                }

                updateLocalData('training_days', normalizeArrayFieldValue('training_days', selectedDays));
                updateScheduleUI();
                setFeedback('', false);
            });
        });

        var toggle = document.getElementById('reminders-toggle');
        if (toggle) {
            toggle.addEventListener('change', function () {
                updateLocalData('reminders_enabled', !!toggle.checked);
                if (!toggle.checked) {
                    updateLocalData('reminder_time_local', null);
                } else if (!getData().reminder_time_local) {
                    updateLocalData('reminder_time_local', DEFAULT_REMINDER_TIME);
                }
                updateScheduleUI();
            });
        }

        var timeInput = document.getElementById('reminder-time-input');
        if (timeInput) {
            timeInput.addEventListener('change', function () {
                updateLocalData('reminder_time_local', timeInput.value || null);
            });
        }
    }

    function bindNavigationButtons() {
        var next = document.getElementById('onboarding-next-btn');
        var start = document.getElementById('onboarding-start-btn');
        var back = document.getElementById('onboarding-back-btn');
        var finish = document.getElementById('onboarding-finish-btn');

        if (next) {
            next.addEventListener('click', goNext);
        }
        if (start) {
            start.addEventListener('click', goNext);
        }
        if (back) {
            back.addEventListener('click', goBack);
        }
        if (finish) {
            finish.addEventListener('click', window.KinematicsOnboardingFinish);
        }
    }

    function bindCurrentStep() {
        var step = getCurrentStep();
        if (!step) {
            return;
        }

        bindNavigationButtons();

        if (step.key === 'splash' || step.key === 'coach_intro' || step.key === 'analyzing') {
            return;
        }

        if (step.type === 'metric') {
            bindMetricControls(step);
            return;
        }

        if (step.type === 'frequency') {
            bindFrequencyControls();
            return;
        }

        if (step.type === 'schedule') {
            bindScheduleControls();
            return;
        }

        bindChoiceButtons(step);
    }

    function updateAnalyzingUI() {
        var items = getDerived().analysis_items || [];
        var totalPercent = Math.max(0, Math.min(100, Math.round(state.analysisProgress)));
        var totalPercentNode = document.getElementById('analyze-total-percent');
        var totalBar = document.getElementById('analyze-total-bar-fill');
        var finishButton = document.getElementById('onboarding-finish-btn');
        var ctaNote = document.getElementById('analyze-cta-note');

        if (totalPercentNode) {
            totalPercentNode.textContent = totalPercent + '%';
        }
        if (totalBar) {
            totalBar.style.width = totalPercent + '%';
        }

        items.forEach(function (item, index) {
            var percent = analysisItemProgress(index, items.length);
            var card = document.querySelector('[data-analyze-item="' + index + '"]');
            if (!card) {
                return;
            }
            var percentNode = card.querySelector('[data-analyze-percent]');
            var bar = card.querySelector('[data-analyze-bar]');
            var valueNode = card.querySelector('[data-analyze-value]');

            card.classList.toggle('is-pending', percent <= 0);
            card.classList.toggle('is-current', percent > 0 && percent < 100);
            card.classList.toggle('is-complete', percent >= 100);

            if (percentNode) {
                percentNode.textContent = percent + '%';
            }
            if (bar) {
                bar.style.width = percent + '%';
            }
            if (valueNode) {
                valueNode.classList.toggle('is-visible', percent >= 45);
            }
        });

        if (finishButton) {
            finishButton.disabled = !isAnalysisComplete();
            finishButton.textContent = isAnalysisComplete()
                ? 'ПОЛУЧИТЬ МОЙ ПЛАН'
                : (isAnalysisAnimationComplete() ? 'ФИНАЛИЗИРУЕМ ПЛАН…' : 'ГОТОВИМ ПЛАН…');
        }
        if (ctaNote) {
            ctaNote.textContent = isAnalysisComplete()
                ? 'План готов. Можно переходить дальше.'
                : (isAnalysisAnimationComplete()
                    ? 'Почти готово. Сохраняем и финализируем ваш план.'
                    : 'Данные появляются по мере заполнения каждой шкалы.');
        }

        if (isAnalysisComplete() && !state.isFinishing && !state.analysisAutoFinishTimerId) {
            state.analysisAutoFinishTimerId = window.setTimeout(function () {
                state.analysisAutoFinishTimerId = null;
                window.KinematicsOnboardingFinish();
            }, 220);
            return;
        }

        if (!isAnalysisComplete() && state.analysisAutoFinishTimerId) {
            window.clearTimeout(state.analysisAutoFinishTimerId);
            state.analysisAutoFinishTimerId = null;
        }
    }

    function clearAnalysisTimer() {
        if (state.analysisTimerId) {
            window.clearInterval(state.analysisTimerId);
            state.analysisTimerId = null;
        }
    }

    function clearAnalysisAutoFinishTimer() {
        if (state.analysisAutoFinishTimerId) {
            window.clearTimeout(state.analysisAutoFinishTimerId);
            state.analysisAutoFinishTimerId = null;
        }
    }

    function startAnalysisAnimation() {
        clearAnalysisTimer();
        var items = getDerived().analysis_items || [];
        var totalItems = items.length;
        state.analysisProgress = 0;
        updateAnalyzingUI();

        if (!totalItems) {
            state.analysisProgress = 100;
            updateAnalyzingUI();
            return;
        }

        var startedAt = Date.now();
        var durationMs = Math.max(3200, totalItems * 950);
        state.analysisTimerId = window.setInterval(function () {
            var elapsed = Date.now() - startedAt;
            state.analysisProgress = Math.max(0, Math.min(100, (elapsed / durationMs) * 100));
            updateAnalyzingUI();
            if (state.analysisProgress >= 100) {
                clearAnalysisTimer();
                state.analysisProgress = 100;
                updateAnalyzingUI();
            }
        }, 50);
    }

    function completeFlow() {
        state.currentStepKey = 'analyzing';
        state.analysisProgress = 0;
        state.analysisRequestComplete = false;
        clearAnalysisAutoFinishTimer();
        render();
        startAnalysisAnimation();

        sendJsonNoRedirect('/api/onboarding/complete', 'POST', {}, 'Не удалось завершить onboarding.')
            .then(function (response) {
                state.onboarding = response;
                state.analysisRequestComplete = true;
                clearDraft();
                clearPlanCaches();
                if (response && response.plan) {
                    savePlanHandoff(response.plan);
                } else {
                    clearPlanHandoff();
                }
                if (site.markOnboardingCompletedLocally) {
                    site.markOnboardingCompletedLocally();
                }
                if (site.clearPendingOnboardingReset) {
                    site.clearPendingOnboardingReset();
                }
                if (state.currentStepKey === 'analyzing') {
                    render();
                }
            })
            .catch(function (error) {
                if (error && error.code === 'AUTH_REQUIRED') {
                    state.onboarding = Object.assign({}, state.onboarding || {}, {
                        status: 'completed',
                        is_completed: true
                    });
                    state.analysisRequestComplete = true;
                    clearDraft();
                    clearPlanCaches();
                    savePlanHandoff(buildLocalPlanFromDraft());
                    if (site.markOnboardingCompletedLocally) {
                        site.markOnboardingCompletedLocally();
                    }
                    if (site.clearPendingOnboardingReset) {
                        site.clearPendingOnboardingReset();
                    }
                    if (state.currentStepKey === 'analyzing') {
                        render();
                    }
                    return;
                }
                clearAnalysisTimer();
                state.analysisProgress = 0;
                state.analysisRequestComplete = false;
                clearAnalysisAutoFinishTimer();
                if (error && error.code === 'PLAN_GENERATION_UNAVAILABLE') {
                    clearDraft();
                    clearPlanCaches();
                    clearPlanHandoff();
                    if (site.markOnboardingCompletedLocally) {
                        site.markOnboardingCompletedLocally();
                    }
                    if (site.clearPendingOnboardingReset) {
                        site.clearPendingOnboardingReset();
                    }
                    window.location.replace('/app/programs');
                    return;
                }
                state.currentStepKey = 'schedule';
                setFeedback(error.message || 'Не удалось завершить onboarding.', true);
                render();
            });
    }

    function validateCurrentStep() {
        return validateStepValue(getCurrentStep(), getData());
    }

    function goNext() {
        var step = getCurrentStep();
        var validation = validateCurrentStep();

        if (!validation.ok) {
            setFeedback(validation.message, true);
            return;
        }

        if (step.key === 'splash') {
            state.currentStepKey = 'coach_intro';
            saveDraft();
            render();
            return;
        }

        if (step.key === 'coach_intro') {
            state.currentStepKey = 'main_goal';
            saveDraft();
            render();
            return;
        }

        if (step.key === 'schedule') {
            persistAllData(false).then(function () {
                completeFlow();
            }).catch(function () {
                return;
            });
            return;
        }

        state.feedbackText = '';
        state.feedbackError = false;
        state.currentStepKey = nextStepKey(step.key);
        saveDraft();
        render();
    }

    function goBack() {
        clearAnalysisTimer();
        state.analysisRequestComplete = false;
        clearAnalysisAutoFinishTimer();
        state.feedbackText = '';
        state.feedbackError = false;
        state.currentStepKey = previousStepKey(state.currentStepKey);
        saveDraft();
        render();
    }

    window.KinematicsOnboardingFinish = function () {
        if (state.isFinishing || !isAnalysisComplete()) {
            return;
        }
        state.isFinishing = true;
        clearAnalysisAutoFinishTimer();
        if (site.clearPendingOnboardingReset) {
            site.clearPendingOnboardingReset();
        }
        site.ensureAuthenticatedSession({ allowTelegram: true, redirectOnFail: false })
            .catch(function () {
                return null;
            })
            .then(function () {
                window.location.replace('/app/programs?fresh_plan=' + Date.now());
            })
            .catch(function () {
                state.isFinishing = false;
                window.location.replace('/app/programs?fresh_plan=' + Date.now());
            });
    };

    function requestedStepKey() {
        try {
            var params = new window.URLSearchParams(window.location.search || '');
            var requested = String(params.get('step') || '').trim();
            if (requested && Object.prototype.hasOwnProperty.call(STEP_INDEX, requested) && requested !== 'analyzing') {
                return requested;
            }
        } catch (error) {
            return '';
        }
        return '';
    }

    function resolveInitialStep(response) {
        var mergedResponse = mergeResponseWithDraft(response);
        var draft = readDraft();

        state.onboarding = mergedResponse && typeof mergedResponse === 'object' ? mergedResponse : {};
        ensureOnboardingStateShape();
        syncLocalDerivedMetrics();

        var requested = requestedStepKey();
        if (requested) {
            try {
                window.history.replaceState({}, document.title, '/app/onboarding');
            } catch (error) {
                return requested;
            }
            return requested;
        }

        if (mergedResponse && mergedResponse.resume_step && mergedResponse.resume_step !== 'splash') {
            return mergedResponse.resume_step;
        }

        if (hasAnyDraftAnswers(getData())) {
            return inferResumeStepFromData(getData());
        }

        if (draft && draft.currentStepKey && draft.currentStepKey !== 'splash') {
            return draft.currentStepKey;
        }

        return (mergedResponse && mergedResponse.resume_step) || 'splash';
    }

    document.addEventListener('DOMContentLoaded', function () {
        var root = getRoot();
        site.renderState(root, 'Загрузка', 'Подготавливаю onboarding…', false);

        site.prepareOnboardingPage()
            .then(function (response) {
                state.currentStepKey = resolveInitialStep(response);
                state.feedbackText = '';
                state.feedbackError = false;
                render();
            })
            .catch(function (error) {
                if (error && error.code === 'AUTH_REQUIRED') {
                    state.currentStepKey = resolveInitialStep(localGuestOnboardingState());
                    state.feedbackText = '';
                    state.feedbackError = false;
                    render();
                    return;
                }
                if (error && error.code === 'ONBOARDING_COMPLETED') {
                    return;
                }
                site.renderState(root, 'Ошибка', error.message || 'Не удалось открыть onboarding.', true);
            });
    });
})();
