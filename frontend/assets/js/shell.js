(function () {
    var site = window.KinematicsSite;
    var ICONS = {
        progress: '<svg viewBox="0 0 24 24" fill="currentColor" aria-hidden="true"><rect x="4" y="11" width="4.2" height="9" rx="1.5"></rect><rect x="9.9" y="7" width="4.2" height="13" rx="1.5"></rect><rect x="15.8" y="4" width="4.2" height="16" rx="1.5"></rect></svg>',
        plan: '<svg viewBox="0 0 24 24" fill="none" aria-hidden="true"><rect x="3.8" y="3.8" width="16.4" height="16.4" rx="2.8" stroke="currentColor" stroke-width="1.8"></rect><circle cx="8" cy="8.4" r="1.1" fill="currentColor"></circle><circle cx="8" cy="12.2" r="1.1" fill="currentColor"></circle><circle cx="8" cy="16" r="1.1" fill="currentColor"></circle><path d="M10.8 8.4h5.6M10.8 12.2h5.6M10.8 16h5.6" stroke="currentColor" stroke-width="1.8" stroke-linecap="round"></path></svg>',
        workouts: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.9" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M6 8h3v8H6z"></path><path d="M15 8h3v8h-3z"></path><path d="M3 10h3v4H3z"></path><path d="M18 10h3v4h-3z"></path><path d="M9 12h6"></path></svg>',
        me: '<svg viewBox="0 0 24 24" fill="currentColor" aria-hidden="true"><circle cx="12" cy="8" r="4.2"></circle><path d="M4.2 20.4a7.8 7.8 0 0 1 15.6 0z"></path></svg>'
    };
    var PAGE_LABELS = {
        progress: '04 Records',
        plan: '02 Plan',
        workouts: '03 Exercises',
        me: '05 Me'
    };
    var PAGE_CONFIG = {
        progress: {
            key: 'progress',
            href: '/app',
            label: 'Записи',
            title: 'Записи | Kinematics',
            heading: 'Записи',
            subtitle: 'Ежедневные цели по воде и шагам, пульс и давление.',
            dataView: 'records-hub',
            mainClass: '',
            hideHeader: true,
            script: '/assets/js/records-page.js'
        },
        plan: {
            key: 'plan',
            href: '/app/programs',
            label: 'Мой План',
            title: 'Мой план | Kinematics',
            heading: 'Мой план',
            subtitle: 'Персональный 10-дневный маршрут, собранный Mistral по первому интервью.',
            dataView: 'plan-hub',
            mainClass: '',
            hideHeader: true,
            script: '/assets/js/programs-page.js'
        },
        workouts: {
            key: 'workouts',
            href: '/app/catalog',
            label: 'Упражнения',
            title: 'Упражнения | Kinematics',
            heading: 'Упражнения',
            subtitle: 'Список упражнений из старого каталога и заготовка под текущий план.',
            dataView: 'exercise-hub',
            mainClass: '',
            hideHeader: true,
            script: '/assets/js/catalog-page.js'
        },
        me: {
            key: 'me',
            href: '/app/profile',
            label: 'Я',
            title: 'Я | Kinematics',
            heading: 'Я',
            subtitle: 'Профиль, избранное, настройки, календарь и вес.',
            dataView: 'profile-hub',
            mainClass: '',
            hideHeader: true,
            script: '/assets/js/profile-page.js'
        }
    };
    var NAV_ITEMS = [
        PAGE_CONFIG.plan,
        PAGE_CONFIG.workouts,
        PAGE_CONFIG.progress,
        PAGE_CONFIG.me
    ];
    var shellState = window.KinematicsShell = window.KinematicsShell || {};
    var currentPageKey = null;
    var assetQuery = '';
    var navigationToken = 0;

    function normalizePath(path) {
        var normalized = String(path || '').trim() || '/';
        if (normalized.length > 1) {
            normalized = normalized.replace(/\/+$/, '');
        }
        return normalized || '/';
    }

    function normalizePageKey(value) {
        var raw = String(value || '').trim().toLowerCase();
        if (raw === 'home') {
            return 'progress';
        }
        if (raw === 'records') {
            return 'progress';
        }
        if (raw === 'programs') {
            return 'plan';
        }
        if (raw === 'catalog') {
            return 'workouts';
        }
        if (raw === 'profile' || raw === 'theme') {
            return 'me';
        }
        return raw || 'progress';
    }

    function currentBodyMeta() {
        return {
            title: document.body.getAttribute('data-title') || 'Kinematics',
            heading: document.body.getAttribute('data-heading') || 'Kinematics',
            subtitle: document.body.getAttribute('data-subtitle') || '',
            dataView: document.body.getAttribute('data-view') || '',
            mainClass: document.body.getAttribute('data-main-class') || '',
            hideHeader: document.body.getAttribute('data-hide-header') === '1'
        };
    }

    function pageConfig(key) {
        return PAGE_CONFIG[normalizePageKey(key)] || null;
    }

    function pageKeyByPath(pathname) {
        var normalized = normalizePath(pathname);
        var match = null;

        Object.keys(PAGE_CONFIG).some(function (key) {
            if (PAGE_CONFIG[key].href === normalized) {
                match = key;
                return true;
            }
            return false;
        });

        return match;
    }

    function resolveAssetQuery() {
        var script;
        var src;
        var queryIndex;

        if (assetQuery) {
            return assetQuery;
        }

        script = document.querySelector('script[src*="/assets/js/shell.js"]');
        src = script ? String(script.getAttribute('src') || '') : '';
        queryIndex = src.indexOf('?');
        assetQuery = queryIndex >= 0 ? src.slice(queryIndex) : '';
        return assetQuery;
    }

    function bumpRouteToken(pathname) {
        shellState.routeToken = Number(shellState.routeToken || 0) + 1;
        shellState.path = normalizePath(pathname || window.location.pathname);
        return shellState.routeToken;
    }

    function navItem(currentPage, item) {
        var active = currentPage === item.key;
        return [
            '<a class="mobile-dock-item dock-item ', active ? 'is-active active' : '', '" href="', item.href, '" data-dock-key="', item.key, '" ', active ? 'aria-current="page"' : '', '>',
            '<span class="mobile-dock-icon dock-glyph" aria-hidden="true">', ICONS[item.key], '</span>',
            '<span class="mobile-dock-label">', item.label, '</span>',
            '</a>'
        ].join('');
    }

    function buildHeader(pageKey, meta) {
        var pageLabel = PAGE_LABELS[pageKey] || 'Kinematics';

        if (meta.hideHeader) {
            return '';
        }

        return [
            '<header class="mobile-app-header page-head">',
            '<div class="mobile-header-copy head-copy">',
            '<span class="mobile-header-kicker kicker">', pageLabel, '</span>',
            '<h1 class="mobile-header-title">', meta.heading, '</h1>',
            meta.subtitle ? '<p class="mobile-header-subtitle subtitle">' + meta.subtitle + '</p>' : '',
            '</div>',
            '<a class="mobile-profile-chip avatar-soft" href="/app/profile" aria-label="Открыть раздел Я">',
            '<span class="avatar-circle">K</span>',
            '<span class="mobile-profile-copy"><span class="status-user-name">Пользователь</span><span class="status-user-email" hidden></span></span>',
            '</a>',
            '</header>'
        ].join('');
    }

    function buildMainMarkup(pageKey, meta) {
        return [
            buildHeader(pageKey, meta),
            '<section id="page-root" class="mobile-page-root"></section>'
        ].join('');
    }

    function readDockMetrics(item) {
        if (!item) {
            return null;
        }

        return {
            left: item.offsetLeft,
            top: item.offsetTop,
            width: item.offsetWidth,
            height: item.offsetHeight
        };
    }

    function applyDockIndicatorMetrics(indicator, metrics) {
        if (!indicator || !metrics) {
            return;
        }

        indicator.style.width = metrics.width + 'px';
        indicator.style.height = metrics.height + 'px';
        indicator.style.transform = 'translate3d(' + metrics.left + 'px, ' + metrics.top + 'px, 0)';
    }

    function mountDockIndicator(dock, fromKey) {
        var indicator = dock.querySelector('.mobile-dock-indicator');
        var activeItem = dock.querySelector('.mobile-dock-item.is-active');
        var fromItem = fromKey ? dock.querySelector('[data-dock-key="' + fromKey + '"]') : null;
        var activeMetrics;
        var fromMetrics;

        if (!indicator || !activeItem) {
            return;
        }

        activeMetrics = readDockMetrics(activeItem);
        if (!activeMetrics) {
            return;
        }

        fromMetrics = readDockMetrics(fromItem);

        if (dock.__dockResizeHandler) {
            window.removeEventListener('resize', dock.__dockResizeHandler);
        }

        dock.__dockResizeHandler = function () {
            applyDockIndicatorMetrics(indicator, readDockMetrics(activeItem));
        };
        window.addEventListener('resize', dock.__dockResizeHandler);

        if (!fromMetrics || fromKey === currentPageKey) {
            applyDockIndicatorMetrics(indicator, activeMetrics);
            dock.classList.add('is-mounted');
            return;
        }

        dock.classList.remove('is-mounted');
        applyDockIndicatorMetrics(indicator, fromMetrics);

        if (typeof window.requestAnimationFrame === 'function') {
            window.requestAnimationFrame(function () {
                window.requestAnimationFrame(function () {
                    dock.classList.add('is-mounted');
                    applyDockIndicatorMetrics(indicator, activeMetrics);
                });
            });
            return;
        }

        window.setTimeout(function () {
            dock.classList.add('is-mounted');
            applyDockIndicatorMetrics(indicator, activeMetrics);
        }, 16);
    }

    function syncDockState(nextKey, options) {
        var dock = document.querySelector('.mobile-dock');
        var animate = !!(options && options.animate);
        var fromKey = options && options.fromKey ? normalizePageKey(options.fromKey) : null;
        var targetItem;

        if (!dock) {
            return;
        }

        if (dock.__dockMotionTimer) {
            window.clearTimeout(dock.__dockMotionTimer);
            dock.__dockMotionTimer = null;
        }

        Array.prototype.forEach.call(dock.querySelectorAll('.mobile-dock-item'), function (item) {
            var active = normalizePageKey(item.getAttribute('data-dock-key')) === nextKey;
            item.classList.toggle('is-active', active);
            item.classList.toggle('active', active);
            item.classList.remove('is-transition-target');
            if (active) {
                item.setAttribute('aria-current', 'page');
                targetItem = item;
            } else {
                item.removeAttribute('aria-current');
            }
        });

        dock.classList.toggle('has-motion', animate);
        if (animate && targetItem) {
            targetItem.classList.add('is-transition-target');
        }

        mountDockIndicator(dock, animate ? fromKey : null);

        if (!animate || !targetItem) {
            return;
        }

        dock.__dockMotionTimer = window.setTimeout(function () {
            targetItem.classList.remove('is-transition-target');
            dock.classList.remove('has-motion');
            dock.__dockMotionTimer = null;
        }, 420);
    }

    function updateBodyMeta(pageKey, meta) {
        document.body.setAttribute('data-page', pageKey);
        document.body.setAttribute('data-view', meta.dataView || '');
        document.body.setAttribute('data-title', meta.title || 'Kinematics');
        document.body.setAttribute('data-heading', meta.heading || 'Kinematics');
        document.body.setAttribute('data-subtitle', meta.subtitle || '');
        document.body.setAttribute('data-main-class', meta.mainClass || '');
        document.body.setAttribute('data-hide-header', meta.hideHeader ? '1' : '0');
        document.title = meta.title || 'Kinematics';
    }

    function renderMainFrame(pageKey, meta) {
        var main = document.getElementById('app-main');
        var className = 'mobile-app-main';

        if (!main) {
            return;
        }

        document.body.classList.remove('records-sheet-open');
        document.body.classList.remove('records-goal-sheet-open');

        if (meta.mainClass) {
            className += ' ' + meta.mainClass;
        }

        main.className = className;
        main.innerHTML = buildMainMarkup(pageKey, meta);
    }

    function ensurePageScript(pageKey) {
        var meta = pageConfig(pageKey);
        var pages = window.KinematicsPages || {};

        if (!meta || !meta.script) {
            return Promise.reject(new Error('Не удалось определить экран.'));
        }

        if (typeof pages[pageKey] === 'function') {
            return Promise.resolve();
        }

        if (!site || typeof site.loadScript !== 'function') {
            return Promise.reject(new Error('Не удалось загрузить скрипт страницы.'));
        }

        return site.loadScript(meta.script + resolveAssetQuery());
    }

    function mountPage(pageKey, token) {
        var pages = window.KinematicsPages || {};
        var mount = pages[pageKey];

        if (token !== navigationToken) {
            return;
        }

        if (typeof mount !== 'function') {
            throw new Error('Экран не зарегистрирован.');
        }

        mount();
    }

    function navigateToDockPage(pageKey, options) {
        var targetKey = normalizePageKey(pageKey);
        var meta = pageConfig(targetKey);
        var fromKey = currentPageKey || normalizePageKey(document.body.getAttribute('data-page'));
        var currentPath = normalizePath(window.location.pathname);
        var token;

        options = options || {};

        if (!meta) {
            window.location.assign(options.href || '/app');
            return Promise.resolve(false);
        }

        if (fromKey === targetKey && currentPath === meta.href && options.force !== true) {
            return Promise.resolve(false);
        }

        navigationToken += 1;
        token = navigationToken;
        currentPageKey = targetKey;
        bumpRouteToken(meta.href);

        updateBodyMeta(targetKey, meta);
        renderMainFrame(targetKey, meta);
        syncDockState(targetKey, {
            fromKey: fromKey,
            animate: options.animate !== false && fromKey !== targetKey
        });

        if (options.historyMode === 'push') {
            window.history.pushState({ dockPage: targetKey }, '', meta.href);
        } else if (options.historyMode === 'replace') {
            window.history.replaceState({ dockPage: targetKey }, '', meta.href);
        }

        window.scrollTo(0, 0);

        return ensurePageScript(targetKey)
            .then(function () {
                mountPage(targetKey, token);
                return true;
            })
            .catch(function () {
                if (options.allowHardReload === false) {
                    return false;
                }
                window.location.assign(meta.href);
                return false;
            });
    }

    function bindDockEvents() {
        var dock = document.querySelector('.mobile-dock');

        if (!dock) {
            return;
        }

        Array.prototype.forEach.call(dock.querySelectorAll('[data-dock-key]'), function (item) {
            item.addEventListener('click', function (event) {
                var nextKey;

                if (
                    event.defaultPrevented ||
                    event.button !== 0 ||
                    event.metaKey ||
                    event.ctrlKey ||
                    event.shiftKey ||
                    event.altKey
                ) {
                    return;
                }

                nextKey = normalizePageKey(item.getAttribute('data-dock-key'));
                if (!pageConfig(nextKey)) {
                    return;
                }

                if (!pageKeyByPath(window.location.pathname)) {
                    return;
                }

                event.preventDefault();
                navigateToDockPage(nextKey, {
                    historyMode: 'push',
                    animate: true
                });
            });
        });
    }

    function renderShell() {
        var root = document.getElementById('app-shell-root');
        var initialPageKey;
        var initialMeta;
        var initialConfig;
        var topLevelPage;

        if (!root) {
            return;
        }

        topLevelPage = pageKeyByPath(window.location.pathname);
        initialPageKey = normalizePageKey(document.body.getAttribute('data-page'));
        initialConfig = topLevelPage ? pageConfig(topLevelPage) : null;
        initialMeta = initialConfig ? {
            title: initialConfig.title,
            heading: initialConfig.heading,
            subtitle: initialConfig.subtitle,
            dataView: initialConfig.dataView,
            mainClass: initialConfig.mainClass,
            hideHeader: initialConfig.hideHeader
        } : currentBodyMeta();
        currentPageKey = initialPageKey;
        bumpRouteToken(window.location.pathname);

        document.body.classList.add('mobile-app-body');
        updateBodyMeta(initialPageKey, initialMeta);

        root.innerHTML = [
            '<div class="mobile-app-shell phone tg-phone-shell">',
            '<div class="mobile-app-shell-glow mobile-app-shell-glow-a"></div>',
            '<div class="mobile-app-shell-glow mobile-app-shell-glow-b"></div>',
            '<main id="app-main" class="mobile-app-main', initialMeta.mainClass ? ' ' + initialMeta.mainClass : '', '">',
            buildMainMarkup(initialPageKey, initialMeta),
            '</main>',
            '<nav class="mobile-dock dock" aria-label="Основная навигация">',
            '<span class="mobile-dock-indicator" aria-hidden="true"></span>',
            NAV_ITEMS.map(function (item) {
                return navItem(initialPageKey, item);
            }).join(''),
            '</nav>',
            '</div>'
        ].join('');

        bindDockEvents();
        syncDockState(initialPageKey, {
            fromKey: initialPageKey,
            animate: false
        });

        if (topLevelPage && window.history && typeof window.history.replaceState === 'function') {
            window.history.replaceState({ dockPage: topLevelPage }, '', PAGE_CONFIG[topLevelPage].href);
        }
    }

    window.addEventListener('popstate', function () {
        var nextKey = pageKeyByPath(window.location.pathname);

        if (!nextKey) {
            window.location.reload();
            return;
        }

        navigateToDockPage(nextKey, {
            historyMode: 'replace',
            animate: true,
            allowHardReload: false,
            force: true
        });
    });

    renderShell();
})();
