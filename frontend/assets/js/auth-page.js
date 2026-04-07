(function () {
    var site = window.KinematicsSite;

    function setTelegramLoadingMode(copy) {
        var authCard = document.querySelector('.auth-card');
        if (authCard) {
            authCard.classList.add('is-telegram-loading');
        }

        document.querySelectorAll('#login-form, #register-form, .auth-link').forEach(function (node) {
            node.hidden = true;
        });

        var note = document.getElementById('telegram-auth-copy');
        if (note) {
            note.textContent = copy || 'Подключаю Telegram-сессию...';
        }
    }

    function resolveSession() {
        site.resolveAppEntryUrl({ allowReset: true })
            .then(function (nextUrl) {
                window.location.replace(nextUrl);
            })
            .catch(function (error) {
                if (error && error.message) {
                    return;
                }
                site.redirectToApp();
            });
    }

    document.addEventListener('DOMContentLoaded', function () {
        var note = document.getElementById('telegram-auth-copy');
        var telegramUser = site.getTelegramUser();

        if (telegramUser) {
            setTelegramLoadingMode(
                'Telegram-сессия для ' + (telegramUser.first_name || telegramUser.username || telegramUser.id) + ' подключается автоматически.'
            );
        }

        if (note) {
            note.textContent = telegramUser
                ? 'Подключаю Telegram-сессию для ' + (telegramUser.first_name || telegramUser.username || telegramUser.id) + '.'
                : 'Страница открыта вне Telegram. Для теста это допустимо.';
        }

        site.authenticateWithTelegram()
            .then(function (result) {
                if (result) {
                    resolveSession();
                    return;
                }

                if (telegramUser) {
                    return;
                }

                site.fetchJsonWithRetry('/api/auth/me', null, { retries: 3, delayMs: 400, backoffMultiplier: 2 })
                    .then(function (authResult) {
                        if (authResult.response.ok) {
                            resolveSession();
                        }
                    })
                    .catch(function () {
                        return;
                    });
            })
            .catch(function () {
                if (telegramUser) {
                    if (note) {
                        note.textContent = 'Не удалось автоматически подключить Telegram-сессию. Закройте Mini App и откройте его снова из бота.';
                    }
                    return;
                }
                site.fetchJsonWithRetry('/api/auth/me', null, { retries: 3, delayMs: 400, backoffMultiplier: 2 })
                    .then(function (authResult) {
                        if (authResult.response.ok) {
                            resolveSession();
                        }
                    })
                    .catch(function () {
                        return;
                    });
            });
    });
})();
