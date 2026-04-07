(function () {
    var site = window.KinematicsSite;

    var ITEMS = [
        {
            href: '/app/profile/edit',
            label: 'Профиль',
            icon: '<svg viewBox="0 0 24 24" fill="none"><path d="M12 12.2C14.9833 12.2 17.4 9.78335 17.4 6.8C17.4 3.81666 14.9833 1.4 12 1.4C9.01666 1.4 6.6 3.81666 6.6 6.8C6.6 9.78335 9.01666 12.2 12 12.2Z" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"></path><path d="M3.8 21.6C5.45 18.1332 8.28722 16.4 12 16.4C15.7128 16.4 18.55 18.1332 20.2 21.6" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"></path></svg>'
        },
        {
            href: '/app/profile/favorites',
            label: 'Избранное',
            icon: '<svg viewBox="0 0 24 24" fill="none"><path d="M12 20.6C11.3 20.6 10.7 20.3333 10.1 19.8L5.6 15.6C2.4 12.6334 2.4 7.86665 5.6 4.9C8 2.66667 11.4 2.8 13.5 5.1C15.6 2.8 19 2.66667 21.4 4.9C24.6 7.86665 24.6 12.6334 21.4 15.6L16.9 19.8C16.3 20.3333 15.7 20.6 15 20.6H12Z" stroke="currentColor" stroke-width="2" stroke-linejoin="round"></path></svg>'
        },
        {
            href: '/app/profile/reminders',
            label: 'Напоминание',
            icon: '<svg viewBox="0 0 24 24" fill="none"><path d="M12 22C17.5228 22 22 17.5228 22 12C22 6.47715 17.5228 2 12 2C6.47715 2 2 6.47715 2 12C2 17.5228 6.47715 22 12 22Z" stroke="currentColor" stroke-width="2"></path><path d="M12 6V12L15.8 14.3" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"></path><path d="M6.5 1.8L4.2 4.1" stroke="currentColor" stroke-width="2" stroke-linecap="round"></path><path d="M17.5 1.8L19.8 4.1" stroke="currentColor" stroke-width="2" stroke-linecap="round"></path></svg>'
        },
        {
            href: '/app/profile/settings/general',
            label: 'Общие Настройки',
            icon: '<svg viewBox="0 0 24 24" fill="none"><path d="M3 12H13" stroke="currentColor" stroke-width="2" stroke-linecap="round"></path><path d="M3 7H9" stroke="currentColor" stroke-width="2" stroke-linecap="round"></path><path d="M3 17H9" stroke="currentColor" stroke-width="2" stroke-linecap="round"></path><circle cx="17.5" cy="12" r="3.5" stroke="currentColor" stroke-width="2"></circle><path d="M13.8 7H21" stroke="currentColor" stroke-width="2" stroke-linecap="round"></path><path d="M13.8 17H21" stroke="currentColor" stroke-width="2" stroke-linecap="round"></path></svg>'
        },
        {
            href: '/app/profile/settings/disclaimer',
            label: 'Отказ От Ответственности',
            icon: '<svg viewBox="0 0 24 24" fill="none"><circle cx="12" cy="12" r="9" stroke="currentColor" stroke-width="2"></circle><path d="M12 10V16" stroke="currentColor" stroke-width="2" stroke-linecap="round"></path><path d="M12 7.5H12.01" stroke="currentColor" stroke-width="2.6" stroke-linecap="round"></path></svg>'
        }
    ];

    function render() {
        var root = document.getElementById('page-root');
        root.innerHTML = [
            '<section class="settings-sheet">',
            '<header class="settings-sheet-head">',
            '<button id="settings-back" class="settings-back-btn" type="button" aria-label="Назад">',
            '<svg viewBox="0 0 24 24" fill="none"><path d="M14.5 5L8 11.5L14.5 18" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"></path></svg>',
            '</button>',
            '<h1 class="settings-sheet-title">Настройки</h1>',
            '<span class="settings-sheet-spacer"></span>',
            '</header>',
            '<section class="settings-menu-card">',
            ITEMS.map(function (item, index) {
                return [
                    '<a class="settings-menu-row" href="' + item.href + '">',
                    '<span class="settings-menu-icon">' + item.icon + '</span>',
                    '<span class="settings-menu-label">' + site.escapeHtml(item.label) + '</span>',
                    '<span class="settings-menu-arrow" aria-hidden="true"><svg viewBox="0 0 24 24" fill="none"><path d="M9 6L15 12L9 18" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"></path></svg></span>',
                    '</a>',
                    index < ITEMS.length - 1 ? '<div class="settings-menu-divider"></div>' : ''
                ].join('');
            }).join(''),
            '</section>',
            '</section>'
        ].join('');

        var back = document.getElementById('settings-back');
        if (back) {
            back.addEventListener('click', function () {
                if (window.history.length > 1) {
                    window.history.back();
                    return;
                }
                window.location.assign('/app/profile');
            });
        }
    }

    document.addEventListener('DOMContentLoaded', function () {
        var root = document.getElementById('page-root');
        site.renderState(root, 'Загрузка', 'Подготавливаю настройки…', false);
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
                site.renderState(root, 'Ошибка', error.message || 'Не удалось загрузить настройки.', true);
            });
    });
})();
