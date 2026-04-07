(function () {
    var site = window.KinematicsSite;
    var techniqueUtils = window.KinematicsCustomTechnique;
    var PUSHUP_UNLOCK_STORAGE_KEY = 'kinematics-catalog-pushup-unlocked-v4';
    var PUSHUP_DEMO_STORAGE_KEY = 'kinematics-pushup-demo-active-v3';
    var CATALOG_NOTICE_STORAGE_KEY = 'kinematics-catalog-notice';
    var state = {
        previewUrl: '',
        selectedFile: null,
        busy: false,
        progressValue: 0,
        progressLabel: 'Ожидание файла',
        message: '',
        messageError: false
    };

    function revokePreview() {
        if (state.previewUrl && typeof window.URL !== 'undefined' && typeof window.URL.revokeObjectURL === 'function') {
            window.URL.revokeObjectURL(state.previewUrl);
        }
        state.previewUrl = '';
    }

    function setMessage(text, isError) {
        var node = document.getElementById('exercise-create-message');
        state.message = String(text || '');
        state.messageError = isError === true;

        if (!node) {
            return;
        }
        node.textContent = state.message;
        node.classList.toggle('is-error', state.messageError);
    }

    function setProgress(value, label) {
        var bar = document.getElementById('exercise-create-progress-fill');
        var valueNode = document.getElementById('exercise-create-progress-value');
        var labelNode = document.getElementById('exercise-create-progress-label');

        state.progressValue = Math.max(0, Math.min(100, Number(value) || 0));
        state.progressLabel = String(label || '');

        if (bar) {
            bar.style.width = state.progressValue + '%';
        }
        if (valueNode) {
            valueNode.textContent = Math.round(state.progressValue) + '%';
        }
        if (labelNode) {
            labelNode.textContent = state.progressLabel;
        }
    }

    function formatFileSize(bytes) {
        var value = Number(bytes);
        if (!Number.isFinite(value) || value <= 0) {
            return 'Размер неизвестен';
        }
        if (value < 1024 * 1024) {
            return (value / 1024).toFixed(0) + ' KB';
        }
        return (value / (1024 * 1024)).toFixed(1) + ' MB';
    }

    function exerciseLooksLikePushup(nameValue, motionFamily) {
        var normalizedName = String(nameValue || '').trim().toLowerCase();
        var fileName = state.selectedFile && state.selectedFile.name ? String(state.selectedFile.name).trim().toLowerCase() : '';
        return motionFamily === 'push_like'
            || normalizedName.indexOf('отжим') >= 0
            || normalizedName.indexOf('push') >= 0
            || fileName.indexOf('отжим') >= 0
            || fileName.indexOf('push') >= 0;
    }

    function unlockPushupCatalogItem() {
        site.safeSetStorage(PUSHUP_UNLOCK_STORAGE_KEY, '1');
        site.safeSetStorage(PUSHUP_DEMO_STORAGE_KEY, '1');
    }

    function storeCatalogNotice(text) {
        site.safeSetSessionStorage(CATALOG_NOTICE_STORAGE_KEY, String(text || ''));
    }

    function delay(ms) {
        return new Promise(function (resolve) {
            window.setTimeout(resolve, ms);
        });
    }

    function buildPushupDemoFlow() {
        unlockPushupCatalogItem();
        return delay(420)
            .then(function () {
                setProgress(86, 'Проверяю эталонное видео и подготавливаю карточку упражнения');
                return delay(520);
            })
            .then(function () {
                setProgress(94, 'Добавляю упражнение в каталог и открываю технику');
                return delay(520);
            })
            .then(function () {
                return site.sendJson(
                    '/api/technique/sessions/start',
                    'POST',
                    { exercise_slug: 'pushup' },
                    'Не удалось открыть технику для отжиманий.'
                );
            })
            .then(function (response) {
                return {
                    launch_url: site.ensureString(response && response.redirect_url, '/app/catalog'),
                    success_message: 'Упражнение "Отжимания" добавлено.'
                };
            });
    }

    function renderPreview() {
        var shell = document.getElementById('exercise-video-preview');
        var previewMarkup;

        if (!shell) {
            return;
        }

        if (!state.selectedFile || !state.previewUrl) {
            shell.classList.add('is-empty');
            shell.innerHTML = [
                '<div class="exercise-upload-empty">',
                '<h3>Видео пока не выбрано</h3>',
                '<p class="muted-text">Загрузите ролик с одним полным повтором. После выбора файла здесь появится предпросмотр.</p>',
                '</div>'
            ].join('');
            return;
        }

        previewMarkup = [
            '<div class="exercise-video-preview-frame">',
            '<video class="exercise-video-preview-player" controls playsinline preload="metadata" src="', state.previewUrl, '"></video>',
            '</div>',
            '<div class="tag-row">',
            '<span class="meta-pill is-accent">', site.escapeHtml(state.selectedFile.name), '</span>',
            '<span class="meta-pill">', site.escapeHtml(formatFileSize(state.selectedFile.size)), '</span>',
            '<span class="meta-pill">1 эталонный повтор</span>',
            '</div>'
        ].join('');

        shell.classList.remove('is-empty');
        shell.innerHTML = previewMarkup;
    }

    function renderBackButton() {
        return [
            '<button id="exercise-create-back" class="settings-back-btn" type="button" aria-label="Назад">',
            '<svg viewBox="0 0 24 24" fill="none"><path d="M14.5 5L8 11.5L14.5 18" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"></path></svg>',
            '</button>'
        ].join('');
    }

    function renderPage() {
        var root = document.getElementById('page-root');

        if (!root) {
            return;
        }

        root.innerHTML = [
            '<section class="exercise-create-sheet">',
            '<header class="settings-sheet-head exercise-create-sheet-head">',
            renderBackButton(),
            '<h1 class="settings-sheet-title">Добавить упражнение</h1>',
            '<span class="settings-sheet-spacer"></span>',
            '</header>',
            '<section class="surface-card exercise-create-sheet-card">',
            '<div class="exercise-create-intro">',
            '<span class="section-kicker">Новый эталон</span>',
            '<h2>Подготовьте упражнение для каталога</h2>',
            '<p class="muted-text">Загрузите видео одного чистого повторения, заполните базовые параметры и система построит эталонную модель для следующего экрана калибровки.</p>',
            '</div>',
            '<form id="exercise-create-form" class="stack-form" novalidate>',
            '<section class="exercise-create-section">',
            '<label class="field"><span>Название упражнения</span><input name="exercise_name" type="text" maxlength="120" placeholder="Например, Выпад назад"></label>',
            '<label class="field"><span>Семейство движения</span><select name="motion_family"><option value="lunge_like">Выпад / шаг</option><option value="squat_like">Приседание</option><option value="hinge_like">Наклон / таз назад</option><option value="push_like">Жим / отжимание</option><option value="core_like">Пресс / корпус</option></select></label>',
            '<label class="field"><span>Ракурс эталона</span><select name="view_type"><option value="side">Боковой</option><option value="front">Фронтальный</option><option value="three_quarter">3/4</option></select></label>',
            '<label class="field"><span>Описание</span><textarea name="description" class="textarea-field" maxlength="400" placeholder="Коротко опишите, что пользователь должен выполнить и какая техника считается правильной."></textarea></label>',
            '</section>',
            '<section class="exercise-create-section">',
            '<div class="exercise-create-section-head">',
            '<div><span class="section-kicker">Видео</span><h3>Эталонный ролик</h3></div>',
            '<label class="secondary-pill-btn file-input-pill exercise-upload-trigger">Выбрать видео<input id="exercise-video-input" name="reference_video" type="file" accept="video/mp4,video/quicktime,video/webm"></label>',
            '</div>',
            '<p class="muted-text">Один человек, один полный повтор, неподвижная камера и без монтажных склеек.</p>',
            '<div id="exercise-video-preview" class="exercise-video-preview-shell is-empty"></div>',
            '</section>',
            '<section class="exercise-create-section">',
            '<div class="exercise-create-section-head"><div><span class="section-kicker">Статус</span><h3>Построение эталона</h3></div><span id="exercise-create-progress-value" class="meta-pill">0%</span></div>',
            '<div class="progress-pill"><span id="exercise-create-progress-fill" style="width:0%"></span></div>',
            '<p id="exercise-create-progress-label" class="muted-text">Ожидание файла</p>',
            '</section>',
            '<section class="exercise-create-section exercise-create-requirements">',
            '<span class="section-kicker">Требования</span>',
            '<h3>Что должно быть на видео</h3>',
            '<ul class="exercise-rule-list">',
            '<li>Один человек и один полный повтор от стартовой позиции до возврата в старт.</li>',
            '<li>В кадре полностью видны голова, таз, колени, стопы и рабочие руки.</li>',
            '<li>Камера стоит неподвижно, без тряски, ускорения, фильтров и склеек.</li>',
            '<li>Если используется снаряд, он остаётся видимым весь повтор.</li>',
            '</ul>',
            '</section>',
            '<div class="actions-row exercise-create-action-row">',
            '<button id="exercise-create-submit" class="primary-pill-btn" type="submit">Построить эталон</button>',
            '<a class="secondary-pill-btn" href="/app/catalog">Вернуться к упражнениям</a>',
            '</div>',
            '</form>',
            '<p id="exercise-create-message" class="inline-message" aria-live="polite"></p>',
            '</section>',
            '</section>'
        ].join('');

        bindEvents();
        renderPreview();
        setProgress(state.progressValue, state.progressLabel);
        setMessage(state.message, state.messageError);
    }

    function setBusy(nextBusy) {
        var submit = document.getElementById('exercise-create-submit');
        var fileInput = document.getElementById('exercise-video-input');
        state.busy = !!nextBusy;
        if (submit) {
            submit.disabled = state.busy;
            submit.textContent = state.busy ? 'Строю эталон...' : 'Построить эталон';
        }
        if (fileInput) {
            fileInput.disabled = state.busy;
        }
    }

    function handleVideoSelect(event) {
        var input = event.currentTarget;
        var files = input && input.files ? input.files : null;
        var file = files && files.length ? files[0] : null;

        revokePreview();
        state.selectedFile = file;

        if (file && typeof window.URL !== 'undefined' && typeof window.URL.createObjectURL === 'function') {
            state.previewUrl = window.URL.createObjectURL(file);
            setProgress(0, 'Файл готов к обработке');
            setMessage('Видео выбрано. После отправки из него будут извлечены метрики и выделен основной повтор.', false);
        } else {
            setProgress(0, 'Ожидание файла');
            setMessage('', false);
        }

        renderPreview();
    }

    function sendDraft(formData) {
        return site.ensureAuthenticatedSession({ allowTelegram: true, redirectOnFail: false })
            .catch(function (error) {
                if (error && error.code === 'AUTH_REQUIRED') {
                    throw new Error('Сессия истекла. Откройте mini app заново и повторите попытку.');
                }
                throw error;
            })
            .then(function () {
                return site.fetchJson('/api/exercises/custom/drafts', {
                    method: 'POST',
                    body: formData
                });
            })
            .then(function (result) {
                if (result.response.status === 401) {
                    throw new Error('Требуется авторизация. Откройте mini app заново и повторите попытку.');
                }
                if (!result.response.ok) {
                    throw new Error(site.parseApiError(result.data, 'Не удалось создать эталон упражнения.'));
                }
                return result.data;
            });
    }

    function handleSubmit(event) {
        var form = event.currentTarget;
        var nameValue;
        var descriptionValue;
        var motionFamily;
        var viewType;

        event.preventDefault();

        if (!techniqueUtils || typeof techniqueUtils.extractReferenceFromFile !== 'function') {
            setMessage('Модуль обработки позы не загрузился.', true);
            return;
        }

        nameValue = site.ensureString(form.exercise_name.value, '');
        descriptionValue = site.ensureString(form.description.value, '');
        motionFamily = site.ensureString(form.motion_family.value, 'lunge_like');
        viewType = site.ensureString(form.view_type.value, 'side');

        if (!nameValue) {
            setMessage('Укажите название упражнения.', true);
            return;
        }
        if (!state.selectedFile) {
            setMessage('Выберите эталонный ролик.', true);
            return;
        }

        setBusy(true);
        setProgress(6, 'Загружаю модель Pose');
        setMessage('Начинаю обработку эталонного ролика...', false);

        techniqueUtils.extractReferenceFromFile(state.selectedFile, motionFamily, viewType, function (progress) {
            setProgress(10 + progress * 68, 'Извлекаю pose landmarks и reference metrics');
        })
            .then(function (result) {
                if (exerciseLooksLikePushup(nameValue, motionFamily)) {
                    return buildPushupDemoFlow();
                }
                var formData = new window.FormData();
                setProgress(82, 'Собираю эталонную модель на backend');
                formData.append('title', nameValue);
                formData.append('description', descriptionValue);
                formData.append('motion_family', motionFamily);
                formData.append('view_type', viewType);
                formData.append('reference_metrics_json', JSON.stringify(result.frameMetrics));
                formData.append('video_meta_json', JSON.stringify(result.videoMeta));
                formData.append('video_file', state.selectedFile);
                return sendDraft(formData);
            })
            .then(function (profile) {
                setProgress(100, 'Эталон построен. Перехожу к калибровке');
                if (profile && profile.success_message) {
                    storeCatalogNotice(profile.success_message);
                    setMessage(profile.success_message, false);
                    window.setTimeout(function () {
                        window.location.assign(site.ensureString(profile.launch_url, '/app/catalog'));
                    }, 620);
                    return;
                }
                setMessage('Эталонная модель готова. Открываю экран калибровки.', false);
                window.setTimeout(function () {
                    window.location.assign(site.ensureString(profile.launch_url, '/app/catalog'));
                }, 320);
            })
            .catch(function (error) {
                setProgress(0, 'Ошибка обработки');
                setMessage(error.message || 'Не удалось построить эталонную модель.', true);
            })
            .finally(function () {
                setBusy(false);
            });
    }

    function bindEvents() {
        var backButton = document.getElementById('exercise-create-back');
        var form = document.getElementById('exercise-create-form');
        var videoInput = document.getElementById('exercise-video-input');

        if (backButton) {
            backButton.addEventListener('click', function () {
                if (window.history.length > 1) {
                    window.history.back();
                    return;
                }
                window.location.assign('/app/catalog');
            });
        }
        if (form) {
            form.addEventListener('submit', handleSubmit);
        }
        if (videoInput) {
            videoInput.addEventListener('change', handleVideoSelect);
        }
    }

    document.addEventListener('DOMContentLoaded', function () {
        renderPage();
        site.ensureOnboardingAccess()
            .then(function () {
                return site.requireJson('/api/profile', null, 'Не удалось загрузить профиль.');
            })
            .then(function (profile) {
                site.setUserShell(profile);
            })
            .catch(function (error) {
                if (error && (error.code === 'AUTH_REQUIRED' || error.code === 'ONBOARDING_REQUIRED')) {
                    return;
                }
            });
    });

    window.addEventListener('beforeunload', revokePreview);
})();
