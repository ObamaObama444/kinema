(function () {
    var site = window.KinematicsSite;
    var techniqueUtils = window.KinematicsCustomTechnique;
    var state = {
        profile: null,
        stream: null,
        analyzer: null,
        recording: false,
        poseBusy: false,
        animationFrame: null,
        capturedFrames: [],
        recordStartedAt: 0,
        cameraReady: false,
        message: '',
        messageError: false,
        compareBusy: false
    };

    function getProfileId() {
        var segments = site.getPathSegments();
        var raw = segments.length ? segments[segments.length - 1] : '';
        var value = Number(raw);
        return Number.isFinite(value) && value > 0 ? value : null;
    }

    function setMessage(text, isError) {
        var node = document.getElementById('exercise-calibration-message');
        state.message = String(text || '');
        state.messageError = isError === true;

        if (!node) {
            return;
        }
        node.textContent = state.message;
        node.classList.toggle('is-error', state.messageError);
    }

    function escapeHtml(value) {
        return site.escapeHtml(value);
    }

    function profileStatusLabel(status) {
        if (status === 'published') {
            return 'В библиотеке';
        }
        if (status === 'testing') {
            return 'Тестируется';
        }
        return 'Черновик';
    }

    function numberField(name, label, value, step, min, max, disabled) {
        return [
            '<label class="field">',
            '<span>', escapeHtml(label), '</span>',
            '<input name="', escapeHtml(name), '" type="number" step="', escapeHtml(String(step)), '" min="', escapeHtml(String(min)), '" max="', escapeHtml(String(max)), '" value="', escapeHtml(String(value)), '" ', disabled ? 'disabled' : '', '>',
            '</label>'
        ].join('');
    }

    function renderResult(result) {
        if (!result) {
            return '<article class="glass-card empty-card">Запустите тест с камеры, чтобы увидеть текущий score и детализацию по метрикам.</article>';
        }

        return [
            '<article class="glass-card calibration-result-card">',
            '<div class="section-head"><div><span class="section-kicker">Последний тест</span><h3>Score и метрики</h3></div><span class="status-pill">', escapeHtml(result.quality || 'Ожидание'), '</span></div>',
            '<div class="metric-grid-inline">',
            '<article><span>Score</span><strong>', escapeHtml(String(result.rep_score || 0)), '</strong></article>',
            '<article><span>Амплитуда</span><strong>', escapeHtml(String(Math.round(Number((result.details && result.details.scores && result.details.scores.range_of_motion) || 0)))), '</strong></article>',
            '<article><span>Корпус</span><strong>', escapeHtml(String(Math.round(Number((result.details && result.details.scores && result.details.scores.posture) || 0)))), '</strong></article>',
            '</div>',
            result.errors && result.errors.length ? '<div class="glass-inner-panel"><strong>Ошибки</strong><ul class="exercise-rule-list">' + result.errors.map(function (item) { return '<li>' + escapeHtml(item) + '</li>'; }).join('') + '</ul></div>' : '',
            result.tips && result.tips.length ? '<div class="glass-inner-panel"><strong>Подсказки</strong><ul class="exercise-rule-list">' + result.tips.map(function (item) { return '<li>' + escapeHtml(item) + '</li>'; }).join('') + '</ul></div>' : '',
            '</article>'
        ].join('');
    }

    function renderProfile(profile) {
        var root = document.getElementById('page-root');
        var calibration = profile.calibration_profile || {};
        var weights = calibration.weights || {};
        var tolerances = calibration.tolerances || {};
        var caps = calibration.caps || {};
        var disabled = !profile.can_edit;
        var canPublish = profile.can_edit && profile.status !== 'published';
        var markup;

        if (!root) {
            return;
        }

        markup = [
            '<section class="exercise-calibration-page">',
            '<header class="exercise-create-head">',
            '<a class="technique-back-link" href="/app/catalog">Назад к упражнениям</a>',
            '<span class="section-kicker">Калибровка</span>',
            '<h1>', escapeHtml(profile.title), '</h1>',
            '<p class="muted-text">Проверьте эталонную модель, настройте веса и допуски, затем протестируйте scoring через камеру.</p>',
            '</header>',

            '<section class="glass-card exercise-create-summary-card">',
            '<div class="section-head">',
            '<div><span class="section-kicker">Профиль</span><h3>Эталонная модель</h3></div>',
            '<span class="meta-pill is-accent">', escapeHtml(profileStatusLabel(profile.status)), '</span>',
            '</div>',
            '<div class="tag-row">',
            '<span class="meta-pill">', escapeHtml(profile.motion_family_label), '</span>',
            '<span class="meta-pill">', escapeHtml(profile.view_type_label), '</span>',
            '<span class="meta-pill">', escapeHtml(String((profile.reference_model && profile.reference_model.frame_count) || 0)), ' кадров</span>',
            '<span class="meta-pill">', escapeHtml(String(Math.round(Number(((profile.reference_model && profile.reference_model.duration_ms) || 0) / 1000)))), ' сек</span>',
            '</div>',
            '<div class="metric-grid-inline">',
            '<article><span>Primary amp</span><strong>', escapeHtml(String((profile.reference_model.summary && profile.reference_model.summary.primary_amplitude) || 0)), '</strong></article>',
            '<article><span>Depth amp</span><strong>', escapeHtml(String((profile.reference_model.summary && profile.reference_model.summary.depth_amplitude) || 0)), '</strong></article>',
            '<article><span>View quality</span><strong>', escapeHtml(String((profile.reference_model.summary && profile.reference_model.summary.mean_view_quality) || 0)), '</strong></article>',
            '</div>',
            '</section>',

            '<section class="glass-card exercise-create-form-card">',
            '<div class="section-head"><div><span class="section-kicker">Редактор</span><h3>Порог чувствительности и веса</h3></div></div>',
            !profile.can_edit ? '<p class="muted-text">Этот профиль уже в библиотеке. Вы можете тестировать его, но редактирование доступно только автору.</p>' : '',
            '<form id="exercise-calibration-form" class="stack-form" novalidate>',
            '<label class="field"><span>Пресет чувствительности</span><select name="preset" ', disabled ? 'disabled' : '', '><option value="soft"', calibration.preset === 'soft' ? ' selected' : '', '>Мягкий</option><option value="standard"', calibration.preset === 'standard' ? ' selected' : '', '>Стандарт</option><option value="strict"', calibration.preset === 'strict' ? ' selected' : '', '>Строгий</option></select></label>',
            '<div class="field-grid-two">',
            numberField('weight_trajectory', 'Вес: траектория', weights.trajectory || 0, 0.01, 0, 1, disabled),
            numberField('weight_range_of_motion', 'Вес: амплитуда', weights.range_of_motion || 0, 0.01, 0, 1, disabled),
            numberField('weight_posture', 'Вес: корпус', weights.posture || 0, 0.01, 0, 1, disabled),
            numberField('weight_symmetry', 'Вес: симметрия', weights.symmetry || 0, 0.01, 0, 1, disabled),
            numberField('weight_stability', 'Вес: стабильность', weights.stability || 0, 0.01, 0, 1, disabled),
            numberField('weight_tempo', 'Вес: темп', weights.tempo || 0, 0.01, 0, 1, disabled),
            '</div>',
            '<div class="field-grid-two">',
            numberField('curve_mae', 'Допуск curve MAE', tolerances.curve_mae || 0.18, 0.01, 0.05, 0.55, disabled),
            numberField('range_ratio_low', 'Минимум ROM ratio', tolerances.range_ratio_low || 0.82, 0.01, 0.55, 1, disabled),
            numberField('range_ratio_high', 'Максимум ROM ratio', tolerances.range_ratio_high || 1.18, 0.01, 1, 1.6, disabled),
            numberField('torso_tilt_deg', 'Допуск корпуса, °', tolerances.torso_tilt_deg || 12, 0.5, 3, 35, disabled),
            numberField('asymmetry_pct', 'Допуск асимметрии, °/%', tolerances.asymmetry_pct || 14, 0.5, 2, 40, disabled),
            numberField('heel_lift_norm', 'Допуск heel lift', tolerances.heel_lift_norm || 0.04, 0.005, 0, 0.25, disabled),
            numberField('stability_norm', 'Допуск stability', tolerances.stability_norm || 0.12, 0.005, 0.01, 0.4, disabled),
            numberField('tempo_ratio_pct', 'Допуск темпа', tolerances.tempo_ratio_pct || 0.24, 0.01, 0.05, 0.8, disabled),
            numberField('view_quality_min', 'Минимум view quality', tolerances.view_quality_min || 0.45, 0.01, 0.1, 0.95, disabled),
            '</div>',
            '<div class="field-grid-two">',
            numberField('bad_view_max_score', 'Cap: плохой ракурс', caps.bad_view_max_score || 65, 1, 20, 100, disabled),
            numberField('severe_range_max_score', 'Cap: амплитуда', caps.severe_range_max_score || 45, 1, 10, 100, disabled),
            numberField('severe_posture_max_score', 'Cap: корпус', caps.severe_posture_max_score || 55, 1, 10, 100, disabled),
            numberField('severe_asymmetry_max_score', 'Cap: асимметрия', caps.severe_asymmetry_max_score || 60, 1, 10, 100, disabled),
            numberField('severe_heel_lift_max_score', 'Cap: heel lift', caps.severe_heel_lift_max_score || 50, 1, 10, 100, disabled),
            '</div>',
            profile.can_edit ? '<div class="hero-actions exercise-create-actions"><button id="exercise-calibration-save" class="primary-pill-btn" type="submit">Сохранить калибровку</button></div>' : '',
            '</form>',
            '</section>',

            '<section class="glass-card exercise-calibration-camera-card">',
            '<div class="section-head"><div><span class="section-kicker">Тест с камеры</span><h3>Проверить текущий score</h3></div><span id="exercise-camera-status" class="meta-pill">Камера выключена</span></div>',
            '<div class="technique-camera-stage exercise-calibration-camera-stage">',
            '<video id="exercise-test-video" class="tech-video" playsinline muted autoplay></video>',
            '</div>',
            '<p class="muted-text">Ручной тест: нажмите «Начать тест», выполните один повтор и нажмите «Стоп и посчитать» после возврата в старт.</p>',
            '<div class="hero-actions">',
            '<button id="exercise-test-start" class="primary-pill-btn" type="button">Начать тест</button>',
            '<button id="exercise-test-stop" class="secondary-pill-btn" type="button" disabled>Стоп и посчитать</button>',
            '</div>',
            '</section>',

            '<div id="exercise-test-result">', renderResult(profile.latest_test_summary), '</div>',

            '<section class="glass-card exercise-create-form-card">',
            '<div class="section-head"><div><span class="section-kicker">Публикация</span><h3>Добавить в общую библиотеку</h3></div></div>',
            '<p class="muted-text">После подтверждения упражнение появится в общем каталоге. Перед публикацией нужен чистый тест с камеры: score не ниже 75 и без критических срабатываний caps.</p>',
            '<div class="hero-actions">',
            canPublish ? '<button id="exercise-publish-btn" class="primary-pill-btn" type="button">Подтвердить и добавить в библиотеку</button>' : '<span class="meta-pill is-accent">Опубликовано</span>',
            '</div>',
            '</section>',

            '<p id="exercise-calibration-message" class="inline-message" aria-live="polite"></p>',
            '</section>'
        ].join('');

        root.innerHTML = markup;
        bindEvents();
        setMessage(state.message, state.messageError);
    }

    function calibrationPayloadFromForm() {
        var form = document.getElementById('exercise-calibration-form');
        return {
            preset: site.ensureString(form.preset.value, 'standard'),
            weights: {
                trajectory: Number(form.weight_trajectory.value),
                range_of_motion: Number(form.weight_range_of_motion.value),
                posture: Number(form.weight_posture.value),
                symmetry: Number(form.weight_symmetry.value),
                stability: Number(form.weight_stability.value),
                tempo: Number(form.weight_tempo.value)
            },
            tolerances: {
                curve_mae: Number(form.curve_mae.value),
                range_ratio_low: Number(form.range_ratio_low.value),
                range_ratio_high: Number(form.range_ratio_high.value),
                torso_tilt_deg: Number(form.torso_tilt_deg.value),
                asymmetry_pct: Number(form.asymmetry_pct.value),
                heel_lift_norm: Number(form.heel_lift_norm.value),
                stability_norm: Number(form.stability_norm.value),
                tempo_ratio_pct: Number(form.tempo_ratio_pct.value),
                view_quality_min: Number(form.view_quality_min.value)
            },
            caps: {
                bad_view_max_score: Number(form.bad_view_max_score.value),
                severe_range_max_score: Number(form.severe_range_max_score.value),
                severe_posture_max_score: Number(form.severe_posture_max_score.value),
                severe_asymmetry_max_score: Number(form.severe_asymmetry_max_score.value),
                severe_heel_lift_max_score: Number(form.severe_heel_lift_max_score.value)
            }
        };
    }

    function fetchProfile(profileId) {
        return site.requireJson('/api/exercises/custom/' + profileId, null, 'Не удалось загрузить профиль упражнения.');
    }

    function saveCalibration(event) {
        event.preventDefault();
        site.sendJson(
            '/api/exercises/custom/' + state.profile.id + '/calibration',
            'POST',
            { calibration_profile: calibrationPayloadFromForm() },
            'Не удалось сохранить калибровку.'
        )
            .then(function (profile) {
                stopCameraPreview();
                state.profile = profile;
                renderProfile(profile);
                setMessage('Калибровка сохранена.', false);
            })
            .catch(function (error) {
                setMessage(error.message || 'Не удалось сохранить калибровку.', true);
            });
    }

    function renderCameraStatus(text) {
        var node = document.getElementById('exercise-camera-status');
        if (node) {
            node.textContent = text;
        }
    }

    function ensureCameraPreview() {
        var video = document.getElementById('exercise-test-video');

        if (state.stream && state.analyzer && state.cameraReady) {
            return Promise.resolve();
        }

        renderCameraStatus('Подключаю...');
        return techniqueUtils.createPoseAnalyzer()
            .then(function (analyzer) {
                state.analyzer = analyzer;
                return navigator.mediaDevices.getUserMedia({
                    video: {
                        facingMode: 'user',
                        width: { ideal: 960 },
                        height: { ideal: 540 }
                    },
                    audio: false
                });
            })
            .then(function (stream) {
                state.stream = stream;
                video.srcObject = stream;
                return video.play().catch(function () {
                    return Promise.resolve();
                });
            })
            .then(function () {
                state.cameraReady = true;
                renderCameraStatus('Камера готова');
            })
            .catch(function (error) {
                renderCameraStatus('Ошибка камеры');
                throw error;
            });
    }

    function stopCameraPreview() {
        var video = document.getElementById('exercise-test-video');
        if (state.animationFrame) {
            window.cancelAnimationFrame(state.animationFrame);
            state.animationFrame = null;
        }
        if (state.stream) {
            state.stream.getTracks().forEach(function (track) {
                track.stop();
            });
            state.stream = null;
        }
        if (state.analyzer && typeof state.analyzer.dispose === 'function') {
            state.analyzer.dispose();
            state.analyzer = null;
        }
        if (video) {
            video.srcObject = null;
        }
        state.cameraReady = false;
        state.poseBusy = false;
    }

    function processCameraFrame() {
        var video = document.getElementById('exercise-test-video');
        var metric;

        if (!state.cameraReady || !state.analyzer || !video) {
            return;
        }
        if (!state.recording) {
            state.animationFrame = window.requestAnimationFrame(processCameraFrame);
            return;
        }
        if (state.poseBusy || video.readyState < 2) {
            state.animationFrame = window.requestAnimationFrame(processCameraFrame);
            return;
        }

        state.poseBusy = true;
        state.analyzer.analyzeImage(video)
            .then(function (results) {
                metric = techniqueUtils.buildMetricFrame(
                    results && results.poseLandmarks,
                    state.profile.motion_family,
                    state.profile.view_type,
                    Date.now() - state.recordStartedAt
                );
                if (metric) {
                    state.capturedFrames.push(metric);
                }
            })
            .catch(function () {
                return;
            })
            .finally(function () {
                state.poseBusy = false;
                state.animationFrame = window.requestAnimationFrame(processCameraFrame);
            });
    }

    function startTest() {
        ensureCameraPreview()
            .then(function () {
                var startButton = document.getElementById('exercise-test-start');
                var stopButton = document.getElementById('exercise-test-stop');
                state.capturedFrames = [];
                state.recording = true;
                state.recordStartedAt = Date.now();
                renderCameraStatus('Идёт запись');
                setMessage('Выполните один полный повтор и нажмите «Стоп и посчитать».', false);
                if (startButton) {
                    startButton.disabled = true;
                }
                if (stopButton) {
                    stopButton.disabled = false;
                }
                if (!state.animationFrame) {
                    processCameraFrame();
                }
            })
            .catch(function (error) {
                setMessage(error.message || 'Не удалось получить доступ к камере.', true);
            });
    }

    function stopAndCompare() {
        var isolatedRep;
        var startButton = document.getElementById('exercise-test-start');
        var stopButton = document.getElementById('exercise-test-stop');
        var durationMs;

        state.recording = false;
        durationMs = Date.now() - state.recordStartedAt;
        renderCameraStatus('Считаю score');

        if (startButton) {
            startButton.disabled = false;
        }
        if (stopButton) {
            stopButton.disabled = true;
        }

        if (state.capturedFrames.length < 10) {
            renderCameraStatus('Камера готова');
            setMessage('Слишком мало валидных кадров. Повторите тест и держите тело целиком в кадре.', true);
            return;
        }

        isolatedRep = techniqueUtils.isolateSingleRep(state.capturedFrames);
        if (!isolatedRep || !isolatedRep.frameMetrics || isolatedRep.frameMetrics.length < 10) {
            renderCameraStatus('Камера готова');
            setMessage('Не удалось выделить один чистый повтор. Повторите тест спокойнее и вернитесь в стартовую позицию.', true);
            return;
        }

        state.compareBusy = true;
        site.sendJson(
            '/api/exercises/custom/' + state.profile.id + '/compare',
            'POST',
            {
                frame_metrics: isolatedRep.frameMetrics,
                duration_ms: Math.max(1, isolatedRep.durationMs || durationMs)
            },
            'Не удалось посчитать score по камере.'
        )
            .then(function (result) {
                var shell = document.getElementById('exercise-test-result');
                state.compareBusy = false;
                renderCameraStatus('Камера готова');
                state.profile.latest_test_summary = result;
                if (shell) {
                    shell.innerHTML = renderResult(result);
                }
                setMessage('Тест завершён. При необходимости скорректируйте калибровку и попробуйте снова.', false);
            })
            .catch(function (error) {
                state.compareBusy = false;
                renderCameraStatus('Камера готова');
                setMessage(error.message || 'Не удалось посчитать score.', true);
            });
    }

    function publishProfile() {
        site.sendJson(
            '/api/exercises/custom/' + state.profile.id + '/publish',
            'POST',
            {},
            'Не удалось опубликовать упражнение.'
        )
            .then(function (response) {
                stopCameraPreview();
                state.profile = response.profile;
                renderProfile(state.profile);
                setMessage('Упражнение опубликовано и добавлено в общую библиотеку.', false);
            })
            .catch(function (error) {
                setMessage(error.message || 'Не удалось опубликовать упражнение.', true);
            });
    }

    function bindEvents() {
        var form = document.getElementById('exercise-calibration-form');
        var startButton = document.getElementById('exercise-test-start');
        var stopButton = document.getElementById('exercise-test-stop');
        var publishButton = document.getElementById('exercise-publish-btn');

        if (form && state.profile.can_edit) {
            form.addEventListener('submit', saveCalibration);
        }
        if (startButton) {
            startButton.addEventListener('click', startTest);
        }
        if (stopButton) {
            stopButton.addEventListener('click', stopAndCompare);
        }
        if (publishButton) {
            publishButton.addEventListener('click', publishProfile);
        }
    }

    document.addEventListener('DOMContentLoaded', function () {
        var root = document.getElementById('page-root');
        var profileId = getProfileId();

        if (!root || !profileId) {
            site.renderState(root, 'Ошибка', 'Не удалось определить профиль упражнения.', true);
            return;
        }

        site.renderState(root, 'Загрузка', 'Открываю эталон и калибровку...', false);
        site.ensureOnboardingAccess()
            .then(function () {
                return Promise.all([
                    site.requireJson('/api/profile', null, 'Не удалось загрузить профиль.'),
                    fetchProfile(profileId)
                ]);
            })
            .then(function (results) {
                site.setUserShell(results[0]);
                state.profile = results[1];
                renderProfile(state.profile);
            })
            .catch(function (error) {
                if (error && (error.code === 'AUTH_REQUIRED' || error.code === 'ONBOARDING_REQUIRED')) {
                    return;
                }
                site.renderState(root, 'Ошибка', error.message || 'Не удалось открыть калибровку.', true);
            });
    });

    window.addEventListener('beforeunload', stopCameraPreview);
})();
