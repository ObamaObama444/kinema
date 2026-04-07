(function () {
    function getElement(id) {
        return document.getElementById(id);
    }

    function formatTime(totalSeconds) {
        var minutes = Math.floor(totalSeconds / 60);
        var seconds = totalSeconds % 60;
        return String(minutes).padStart(2, "0") + ":" + String(seconds).padStart(2, "0");
    }

    function parseApiError(data, fallbackMessage) {
        if (!data) {
            return fallbackMessage;
        }
        if (typeof data.detail === "string") {
            return data.detail;
        }
        if (Array.isArray(data.detail) && data.detail.length > 0 && data.detail[0] && data.detail[0].msg) {
            return data.detail[0].msg;
        }
        return fallbackMessage;
    }

    function normalizeStatus(status) {
        if (status === "started") {
            return "started";
        }
        if (status === "finished") {
            return "finished";
        }
        if (status === "stopped") {
            return "stopped";
        }
        return "started";
    }

    function statusLabel(status) {
        if (status === "started") {
            return "Идет";
        }
        if (status === "finished") {
            return "Завершена";
        }
        if (status === "stopped") {
            return "Остановлена";
        }
        return status;
    }

    function createState(config) {
        return {
            sessionId: Number(config.session_id || 0),
            programId: Number(config.program_id || 0),
            status: normalizeStatus(config.status || "started"),
            timerSeconds: 0,
            paused: false,
            webcamActive: false,
            reps: 0,
            formScore: null,
            logSetNumber: 1,
            hints: Array.isArray(config.hints) && config.hints.length > 0
                ? config.hints.slice()
                : [
                    "MOCK: Держите спину ровно",
                    "MOCK: Колени не выходят за носки",
                    "MOCK: Контролируйте темп",
                    "MOCK: Дышите равномерно",
                ],
            hintIndex: 0,
            logHistory: [],
            timerHandle: null,
            hintsHandle: null,
            skeletonHandle: null,
        };
    }

    function renderSessionStatus(state) {
        var statusNode = getElement("session-status-value");
        if (statusNode) {
            statusNode.textContent = statusLabel(state.status);
        }
    }

    function renderTimer(state) {
        var timerNode = getElement("timer-value");
        if (timerNode) {
            timerNode.textContent = formatTime(state.timerSeconds);
        }
    }

    function renderReps(state) {
        var repsNode = getElement("reps-value");
        var scoreNode = getElement("score-value");
        if (repsNode) {
            repsNode.textContent = String(state.reps);
        }
        if (scoreNode) {
            scoreNode.textContent = state.formScore === null ? "--" : String(state.formScore);
        }
    }

    function setStatusMessage(message, type) {
        var statusNode = getElement("workout-status");
        if (!statusNode) {
            return;
        }
        statusNode.textContent = message;
        statusNode.classList.remove("is-error", "is-success", "is-muted");
        if (type === "error") {
            statusNode.classList.add("is-error");
        } else if (type === "success") {
            statusNode.classList.add("is-success");
        } else {
            statusNode.classList.add("is-muted");
        }
    }

    function renderHints(state) {
        var listNode = getElement("hints-list");
        if (!listNode) {
            return;
        }

        var items = [];
        for (var i = 0; i < Math.min(3, state.hints.length); i += 1) {
            items.push(state.hints[(state.hintIndex + i) % state.hints.length]);
        }

        listNode.innerHTML = "";
        for (var j = 0; j < items.length; j += 1) {
            var li = document.createElement("li");
            li.textContent = items[j];
            listNode.appendChild(li);
        }
    }

    function renderLogHistory(state) {
        var listNode = getElement("log-history-list");
        if (!listNode) {
            return;
        }

        listNode.innerHTML = "";
        if (state.logHistory.length === 0) {
            var emptyItem = document.createElement("li");
            emptyItem.className = "workout-log-empty";
            emptyItem.textContent = "Логи еще не отправлялись.";
            listNode.appendChild(emptyItem);
            return;
        }

        for (var i = 0; i < state.logHistory.length; i += 1) {
            var item = state.logHistory[i];
            var li = document.createElement("li");
            li.className = "workout-log-item";
            li.textContent = "#" + item.setNumber + " - reps: " + item.reps + ", form_score_mock: " + item.formScore + " (" + item.time + ")";
            listNode.appendChild(li);
        }
    }

    function updatePauseButton(state) {
        var pauseButton = getElement("pause-btn");
        if (!pauseButton) {
            return;
        }

        if (state.status !== "started") {
            pauseButton.disabled = true;
            pauseButton.textContent = "Пауза";
            return;
        }

        pauseButton.disabled = false;
        pauseButton.textContent = state.paused ? "Продолжить" : "Пауза";
    }

    function updateControlsAvailability(state) {
        var repPlusButton = getElement("rep-plus-btn");
        var repResetButton = getElement("rep-reset-btn");
        var cameraButton = getElement("camera-toggle-btn");

        var disabled = state.status !== "started";
        if (repPlusButton) {
            repPlusButton.disabled = disabled || state.paused;
        }
        if (repResetButton) {
            repResetButton.disabled = disabled;
        }
        if (cameraButton) {
            cameraButton.disabled = disabled;
        }

        updatePauseButton(state);
    }

    function rotateHints(state) {
        if (state.hints.length === 0 || state.paused || state.status !== "started") {
            return;
        }
        state.hintIndex = (state.hintIndex + 1) % state.hints.length;
        renderHints(state);
    }

    function runTimerTick(state) {
        if (state.status !== "started" || state.paused) {
            return;
        }
        state.timerSeconds += 1;
        renderTimer(state);
    }

    function randomShift(base, spread) {
        return base + (Math.random() * spread * 2 - spread);
    }

    function animateSkeleton(state) {
        if (!state.webcamActive || state.paused || state.status !== "started") {
            return;
        }

        var keypoints = [
            { id: "kp-head", x: 50, y: 14 },
            { id: "kp-neck", x: 50, y: 24 },
            { id: "kp-l-shoulder", x: 30, y: 46 },
            { id: "kp-r-shoulder", x: 70, y: 46 },
            { id: "kp-hip", x: 50, y: 42 },
            { id: "kp-l-knee", x: 38, y: 68 },
            { id: "kp-r-knee", x: 62, y: 68 },
        ];

        var positions = {};
        for (var i = 0; i < keypoints.length; i += 1) {
            var point = keypoints[i];
            var node = getElement(point.id);
            if (!node) {
                continue;
            }
            var x = randomShift(point.x, 2.2);
            var y = randomShift(point.y, 1.8);
            node.setAttribute("cx", String(x));
            node.setAttribute("cy", String(y));
            positions[point.id] = { x: x, y: y };
        }

        var boneA = getElement("bone-a");
        var boneB = getElement("bone-b");
        var boneC = getElement("bone-c");
        var boneD = getElement("bone-d");
        var boneE = getElement("bone-e");
        if (boneA && positions["kp-neck"] && positions["kp-hip"]) {
            boneA.setAttribute("x1", String(positions["kp-neck"].x));
            boneA.setAttribute("y1", String(positions["kp-neck"].y));
            boneA.setAttribute("x2", String(positions["kp-hip"].x));
            boneA.setAttribute("y2", String(positions["kp-hip"].y));
        }
        if (boneB && positions["kp-neck"] && positions["kp-l-shoulder"]) {
            boneB.setAttribute("x1", String(positions["kp-neck"].x));
            boneB.setAttribute("y1", String(positions["kp-neck"].y));
            boneB.setAttribute("x2", String(positions["kp-l-shoulder"].x));
            boneB.setAttribute("y2", String(positions["kp-l-shoulder"].y));
        }
        if (boneC && positions["kp-neck"] && positions["kp-r-shoulder"]) {
            boneC.setAttribute("x1", String(positions["kp-neck"].x));
            boneC.setAttribute("y1", String(positions["kp-neck"].y));
            boneC.setAttribute("x2", String(positions["kp-r-shoulder"].x));
            boneC.setAttribute("y2", String(positions["kp-r-shoulder"].y));
        }
        if (boneD && positions["kp-hip"] && positions["kp-l-knee"]) {
            boneD.setAttribute("x1", String(positions["kp-hip"].x));
            boneD.setAttribute("y1", String(positions["kp-hip"].y));
            boneD.setAttribute("x2", String(positions["kp-l-knee"].x));
            boneD.setAttribute("y2", String(positions["kp-l-knee"].y));
        }
        if (boneE && positions["kp-hip"] && positions["kp-r-knee"]) {
            boneE.setAttribute("x1", String(positions["kp-hip"].x));
            boneE.setAttribute("y1", String(positions["kp-hip"].y));
            boneE.setAttribute("x2", String(positions["kp-r-knee"].x));
            boneE.setAttribute("y2", String(positions["kp-r-knee"].y));
        }
    }

    async function parseResponse(response) {
        try {
            return await response.json();
        } catch (error) {
            return {};
        }
    }

    async function loadSession(state) {
        var response = await fetch("/api/workouts/" + state.sessionId, {
            method: "GET",
            credentials: "include",
        });
        var data = await parseResponse(response);

        if (!response.ok) {
            throw new Error(parseApiError(data, "Не удалось загрузить данные тренировки."));
        }

        state.status = normalizeStatus(data.status);
        state.programId = Number(data.program_id || state.programId);
        renderSessionStatus(state);
        updateControlsAvailability(state);
    }

    async function sendMockLog(state) {
        var payload = {
            exercise_id: null,
            set_number: state.logSetNumber,
            reps_done: state.reps,
            form_score_mock: state.formScore,
            notes_mock: "MOCK: Лог создан через кнопку +1 повтор",
        };

        var response = await fetch("/api/workouts/" + state.sessionId + "/log", {
            method: "POST",
            credentials: "include",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(payload),
        });

        var data = await parseResponse(response);
        if (!response.ok) {
            throw new Error(parseApiError(data, "Не удалось сохранить MOCK-лог."));
        }

        var now = new Date();
        state.logHistory.unshift({
            setNumber: state.logSetNumber,
            reps: state.reps,
            formScore: state.formScore,
            time: now.toLocaleTimeString(),
        });
        state.logHistory = state.logHistory.slice(0, 5);
        state.logSetNumber += 1;
        renderLogHistory(state);
    }

    function computeFormScore(reps) {
        var raw = 58 + reps * 3 + Math.floor(Math.random() * 18);
        if (raw > 100) {
            return 100;
        }
        if (raw < 0) {
            return 0;
        }
        return raw;
    }

    function initTimerAndHintsLoops(state) {
        state.timerHandle = window.setInterval(function () {
            runTimerTick(state);
        }, 1000);

        state.hintsHandle = window.setInterval(function () {
            rotateHints(state);
        }, 5000);

        state.skeletonHandle = window.setInterval(function () {
            animateSkeleton(state);
        }, 850);
    }

    function bindLogout() {
        var logoutButton = getElement("logout-btn");
        if (!logoutButton) {
            return;
        }

        logoutButton.addEventListener("click", async function () {
            try {
                await fetch("/api/auth/logout", {
                    method: "POST",
                    credentials: "include",
                });
            } finally {
                window.location.assign("/login");
            }
        });
    }

    function bindCameraToggle(state) {
        var cameraButton = getElement("camera-toggle-btn");
        var webcamFeed = getElement("webcam-feed");
        if (!cameraButton || !webcamFeed) {
            return;
        }

        cameraButton.addEventListener("click", function () {
            if (state.status !== "started") {
                return;
            }

            state.webcamActive = !state.webcamActive;
            webcamFeed.classList.toggle("is-active", state.webcamActive);
            cameraButton.textContent = state.webcamActive
                ? "Выключить камеру (MOCK)"
                : "Включить камеру (MOCK)";
            setStatusMessage(
                state.webcamActive
                    ? "MOCK-камера активирована. Overlay скелета обновляется."
                    : "MOCK-камера отключена.",
                "muted"
            );
        });
    }

    function bindPauseButton(state) {
        var pauseButton = getElement("pause-btn");
        if (!pauseButton) {
            return;
        }

        pauseButton.addEventListener("click", function () {
            if (state.status !== "started") {
                return;
            }

            state.paused = !state.paused;
            updatePauseButton(state);
            updateControlsAvailability(state);
            setStatusMessage(state.paused ? "Тренировка на паузе." : "Тренировка продолжена.", "muted");
        });
    }

    function bindRepButtons(state) {
        var plusButton = getElement("rep-plus-btn");
        var resetButton = getElement("rep-reset-btn");
        if (!plusButton || !resetButton) {
            return;
        }

        plusButton.addEventListener("click", async function () {
            if (state.status !== "started" || state.paused) {
                return;
            }

            state.reps += 1;
            state.formScore = computeFormScore(state.reps);
            renderReps(state);

            try {
                await sendMockLog(state);
                setStatusMessage("MOCK-лог записан.", "success");
            } catch (error) {
                setStatusMessage(error.message || "Ошибка логирования.", "error");
            }
        });

        resetButton.addEventListener("click", function () {
            state.reps = 0;
            state.formScore = null;
            state.logSetNumber = 1;
            renderReps(state);
            setStatusMessage("Счетчик повторений сброшен.", "muted");
        });
    }

    function bindStopButton(state) {
        var stopButton = getElement("stop-btn");
        if (!stopButton) {
            return;
        }

        stopButton.addEventListener("click", async function () {
            stopButton.disabled = true;
            try {
                var response = await fetch("/api/workouts/" + state.sessionId + "/stop", {
                    method: "POST",
                    credentials: "include",
                });
                var data = await parseResponse(response);

                if (!response.ok) {
                    throw new Error(parseApiError(data, "Не удалось остановить тренировку."));
                }

                window.location.assign(data.redirect_url || "/app");
            } catch (error) {
                setStatusMessage(error.message || "Ошибка остановки тренировки.", "error");
                stopButton.disabled = false;
            }
        });
    }

    async function init() {
        if (init._started) {
            return;
        }
        init._started = true;

        var config = window.KINEMATICS_WORKOUT_CONFIG || {};
        var state = createState(config);

        if (!state.sessionId) {
            setStatusMessage("Некорректный session_id.", "error");
            return;
        }

        bindLogout();
        bindCameraToggle(state);
        bindPauseButton(state);
        bindRepButtons(state);
        bindStopButton(state);

        renderTimer(state);
        renderReps(state);
        renderHints(state);
        renderLogHistory(state);
        renderSessionStatus(state);

        try {
            await loadSession(state);
            setStatusMessage("Сессия загружена. Можно начинать тренировку.", "muted");
        } catch (error) {
            setStatusMessage(error.message || "Ошибка загрузки сессии.", "error");
        }

        initTimerAndHintsLoops(state);

        window.addEventListener("beforeunload", function () {
            if (state.timerHandle) {
                clearInterval(state.timerHandle);
            }
            if (state.hintsHandle) {
                clearInterval(state.hintsHandle);
            }
            if (state.skeletonHandle) {
                clearInterval(state.skeletonHandle);
            }
        });
    }

    if (document.readyState === "loading") {
        document.addEventListener("DOMContentLoaded", init);
    } else {
        init();
    }
})();
