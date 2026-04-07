(function () {
    var site = window.KinematicsSite;

    function render() {
        var root = document.getElementById('page-root');
        root.innerHTML = [
            '<section class="settings-detail-sheet">',
            '<header class="settings-sheet-head">',
            '<button id="settings-disclaimer-back" class="settings-back-btn" type="button" aria-label="Назад">',
            '<svg viewBox="0 0 24 24" fill="none"><path d="M14.5 5L8 11.5L14.5 18" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"></path></svg>',
            '</button>',
            '<h1 class="settings-sheet-title">Отказ От Ответственности</h1>',
            '<span class="settings-sheet-spacer"></span>',
            '</header>',
            '<section class="glass-card settings-detail-card settings-disclaimer-card">',
            '<h3>Важно</h3>',
            '<p class="muted-text">Kinematics предоставляет информационные рекомендации по тренировкам и образу жизни. Сервис не заменяет консультацию врача, физиотерапевта или другого квалифицированного специалиста.</p>',
            '<p class="muted-text">Если у вас есть травмы, хронические заболевания, боли, ограничения по нагрузке или любые сомнения, согласуйте программу с врачом до начала тренировок.</p>',
            '<p class="muted-text">Вы используете рекомендации приложения добровольно и принимаете ответственность за выбор интенсивности, техники выполнения и общее состояние во время занятий.</p>',
            '</section>',
            '</section>'
        ].join('');

        var back = document.getElementById('settings-disclaimer-back');
        if (back) {
            back.addEventListener('click', function () {
                if (window.history.length > 1) {
                    window.history.back();
                    return;
                }
                window.location.assign('/app/profile/settings');
            });
        }
    }

    document.addEventListener('DOMContentLoaded', function () {
        var root = document.getElementById('page-root');
        site.renderState(root, 'Загрузка', 'Подготавливаю страницу…', false);
        site.ensureOnboardingAccess()
            .then(function () {
                return site.requireJson('/api/profile', null, 'Не удалось загрузить профиль.');
            })
            .then(function (profile) {
                site.setUserShell(profile);
                render();
            })
            .catch(function (error) {
                if (error && (error.code === 'AUTH_REQUIRED' || error.code === 'ONBOARDING_REQUIRED')) {
                    return;
                }
                site.renderState(root, 'Ошибка', error.message || 'Не удалось загрузить страницу.', true);
            });
    });
})();
