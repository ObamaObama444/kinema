(function () {
    var site = window.KinematicsSite;

    function setStatus(text, isError) {
        var node = document.getElementById('launcher-status');
        if (!node) {
            return;
        }
        node.textContent = text;
        node.classList.remove('is-error');
        if (isError) {
            node.classList.add('is-error');
        }
    }

    function openResolvedApp() {
        site.resolveAppEntryUrl({ allowReset: true })
            .then(function (nextUrl) {
                setStatus('Открываю Kinematics...', false);
                window.location.replace(nextUrl);
            })
            .catch(function (error) {
                setStatus(error.message || 'Не удалось открыть Kinematics.', true);
            });
    }

    function fallbackToCookieSession() {
        site.fetchJsonWithRetry('/api/auth/me', null, { retries: 3, delayMs: 400, backoffMultiplier: 2 })
            .then(function (result) {
                if (result.response.ok) {
                    setStatus('Открываю Kinematics...', false);
                    openResolvedApp();
                    return;
                }

                if (result.response.status === 401) {
                    if (site.isTelegramMiniApp()) {
                        setStatus('Подключаю Telegram...', false);
                        site.authenticateWithTelegram()
                            .then(function (user) {
                                if (user) {
                                    openResolvedApp();
                                    return;
                                }
                                setStatus('Не удалось подключить Telegram.', true);
                            })
                            .catch(function () {
                                setStatus('Не удалось подключить Telegram.', true);
                            });
                        return;
                    }
                    setStatus('Открываю вход...', false);
                    window.location.replace('/login');
                    return;
                }

                setStatus(site.parseApiError(result.data, 'Не удалось проверить сессию.'), true);
            })
            .catch(function () {
                setStatus('Не удалось связаться с сервером.', true);
            });
    }

    document.addEventListener('DOMContentLoaded', function () {
        var telegramUser = site.getTelegramUser();
        var userNode = document.getElementById('launcher-user');
        if (userNode && telegramUser) {
            userNode.textContent = telegramUser.first_name || telegramUser.username || String(telegramUser.id);
        }

        setStatus('Загружаю Kinematics...', false);

        site.authenticateWithTelegram()
            .then(function (user) {
                if (user) {
                    setStatus('Открываю Kinematics...', false);
                    openResolvedApp();
                    return;
                }

                fallbackToCookieSession();
            })
            .catch(function () {
                fallbackToCookieSession();
            });
    });
})();
