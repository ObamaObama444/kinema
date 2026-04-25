(function () {
    var site = window.KinematicsSite;
    var PUSHUP_DEMO_STORAGE_KEY = 'kinematics-pushup-demo-active-v3';
    var TECHNIQUE_VOICE_STORAGE_KEY = 'kinematics-technique-voice-v1';
    var VOICE_PRIORITY_RANK = { low: 1, med: 2, high: 3 };
    var TECHNIQUE_CUE_AUDIO = {
        squat: {
            good_rep: '/assets/media/technique/squat/good_rep.mp3',
            heel_lift: '/assets/media/technique/squat/heel_lift.mp3',
            undersquat: '/assets/media/technique/squat/undersquat.mp3',
            camera_side_view: '/assets/media/technique/squat/camera_side_view.mp3'
        }
    };
    var mountedController = null;
    var EXERCISE_CONFIG = {
        squat: {
            primaryDirection: 'drop',
            minStateFrames: 2,
            cooldownFrames: 5,
            minRepFrames: 8,
            maxRepFrames: 150,
            downEnterPrimaryDrop: 26.0,
            downEnterDepthDelta: 0.08,
            risingRecoverPrimary: 18.0,
            risingRecoverDepth: 0.045,
            upPrimaryTolerance: 14.0,
            upDepthTolerance: 0.05,
            minPrimaryAmplitude: 26.0,
            minDepthAmplitude: 0.08,
            maxMeanAsymmetry: 22.0,
            maxPeakAsymmetry: 42.0,
            minTorsoMotion: 2.5,
            preRollFrames: 6
        },
        pushup: {
            primaryDirection: 'drop',
            minStateFrames: 3,
            cooldownFrames: 5,
            minRepFrames: 6,
            maxRepFrames: 420,
            downEnterPrimaryDrop: 24.0,
            downEnterDepthDelta: 0.07,
            risingRecoverPrimary: 13.0,
            risingRecoverDepth: 0.04,
            upPrimaryTolerance: 20.0,
            upDepthTolerance: 0.06,
            minPrimaryAmplitude: 26.0,
            minDepthAmplitude: 0.10,
            maxMeanAsymmetry: 24.0,
            maxPeakAsymmetry: 38.0,
            minTorsoMotion: 1.2,
            preRollFrames: 5
        },
        lunge: {
            primaryDirection: 'drop',
            minStateFrames: 2,
            cooldownFrames: 6,
            minRepFrames: 10,
            maxRepFrames: 170,
            downEnterPrimaryDrop: 22.0,
            downEnterDepthDelta: 0.06,
            risingRecoverPrimary: 14.0,
            risingRecoverDepth: 0.035,
            upPrimaryTolerance: 16.0,
            upDepthTolerance: 0.045,
            minPrimaryAmplitude: 22.0,
            minDepthAmplitude: 0.06,
            maxMeanAsymmetry: 26.0,
            maxPeakAsymmetry: 46.0,
            minTorsoMotion: 2.2,
            preRollFrames: 6
        },
        glute_bridge: {
            primaryDirection: 'rise',
            minStateFrames: 2,
            cooldownFrames: 6,
            minRepFrames: 10,
            maxRepFrames: 200,
            downEnterPrimaryDrop: 18.0,
            downEnterDepthDelta: 0.02,
            risingRecoverPrimary: 12.0,
            risingRecoverDepth: 0.01,
            upPrimaryTolerance: 16.0,
            upDepthTolerance: 0.03,
            minPrimaryAmplitude: 20.0,
            minDepthAmplitude: 0.015,
            maxMeanAsymmetry: 24.0,
            maxPeakAsymmetry: 40.0,
            minTorsoMotion: 1.0,
            preRollFrames: 6
        },
        leg_raise: {
            primaryDirection: 'drop',
            minStateFrames: 2,
            cooldownFrames: 6,
            minRepFrames: 10,
            maxRepFrames: 220,
            downEnterPrimaryDrop: 18.0,
            downEnterDepthDelta: 0.03,
            risingRecoverPrimary: 11.0,
            risingRecoverDepth: 0.016,
            upPrimaryTolerance: 16.0,
            upDepthTolerance: 0.03,
            minPrimaryAmplitude: 18.0,
            minDepthAmplitude: 0.03,
            maxMeanAsymmetry: 26.0,
            maxPeakAsymmetry: 42.0,
            minTorsoMotion: 1.0,
            preRollFrames: 6
        },
        crunch: {
            primaryDirection: 'drop',
            minStateFrames: 2,
            cooldownFrames: 6,
            minRepFrames: 10,
            maxRepFrames: 180,
            downEnterPrimaryDrop: 16.0,
            downEnterDepthDelta: 0.025,
            risingRecoverPrimary: 10.0,
            risingRecoverDepth: 0.015,
            upPrimaryTolerance: 15.0,
            upDepthTolerance: 0.03,
            minPrimaryAmplitude: 16.0,
            minDepthAmplitude: 0.025,
            maxMeanAsymmetry: 24.0,
            maxPeakAsymmetry: 40.0,
            minTorsoMotion: 0.8,
            preRollFrames: 6
        }
    };
    var LANDMARK = {
        L_SHOULDER: 11,
        R_SHOULDER: 12,
        L_ELBOW: 13,
        R_ELBOW: 14,
        L_WRIST: 15,
        R_WRIST: 16,
        L_HIP: 23,
        R_HIP: 24,
        L_KNEE: 25,
        R_KNEE: 26,
        L_ANKLE: 27,
        R_ANKLE: 28,
        L_HEEL: 29,
        R_HEEL: 30,
        L_FOOT_INDEX: 31,
        R_FOOT_INDEX: 32
    };
    var DEMO_REP_SCENARIOS = {
        squat: [
            {
                repScore: 100,
                hintMessage: 'У вас блестящая техника, продолжайте в том же духе!',
                hintTone: 'low',
                errors: [],
                tips: ['Повтор чистый: держите тот же темп и такую же глубину.'],
                hintCodes: ['good_rep'],
                metrics: {
                    min_knee_angle: 95.0,
                    min_hip_angle: 104.0,
                    max_depth_delta: 0.242,
                    depth_ratio: 1.01,
                    knee_ratio: 1.0,
                    hip_ratio: 1.0,
                    max_torso_forward: 24.0,
                    p90_heel_lift: 0.011,
                    mean_side_view_score: 0.76
                },
                penaltyParts: {},
                ruleFlags: {
                    heel_fail: false,
                    poor_depth: false,
                    undersquat: false,
                    undersquat_severe: false,
                    good_pose: true,
                    excellent_pose: true
                }
            },
            {
                repScore: 1,
                hintMessage: 'Пятки отрываются от пола. Удерживайте стопу полностью на опоре.',
                hintTone: 'high',
                errors: ['Отрыв пяток (критично)'],
                tips: ['Пятки на пол, уменьшите глубину на 10-15% и сохраняйте темп.'],
                hintCodes: ['heel_lift'],
                metrics: {
                    min_knee_angle: 101.0,
                    min_hip_angle: 109.0,
                    max_depth_delta: 0.226,
                    depth_ratio: 0.97,
                    knee_ratio: 0.95,
                    hip_ratio: 0.94,
                    max_torso_forward: 27.0,
                    p90_heel_lift: 0.128,
                    mean_side_view_score: 0.74
                },
                penaltyParts: {
                    heel: 99.0
                },
                ruleFlags: {
                    heel_fail: true,
                    poor_depth: false,
                    undersquat: false,
                    undersquat_severe: false,
                    good_pose: false,
                    excellent_pose: false
                }
            },
            {
                repScore: 65,
                hintMessage: 'Опуститесь чуть ниже, чтобы вернуть рабочую глубину приседа.',
                hintTone: 'med',
                errors: ['Недостаточная глубина приседа'],
                tips: ['Недосед: добавьте глубину до рабочего уровня и фиксируйте низ на 0.3-0.5 сек.'],
                hintCodes: ['undersquat'],
                metrics: {
                    min_knee_angle: 118.0,
                    min_hip_angle: 121.0,
                    max_depth_delta: 0.192,
                    depth_ratio: 0.84,
                    knee_ratio: 0.89,
                    hip_ratio: 0.88,
                    max_torso_forward: 29.0,
                    p90_heel_lift: 0.018,
                    mean_side_view_score: 0.72
                },
                penaltyParts: {
                    depth: 21.0,
                    knee: 14.0
                },
                ruleFlags: {
                    heel_fail: false,
                    poor_depth: true,
                    undersquat: false,
                    undersquat_severe: false,
                    good_pose: false,
                    excellent_pose: false
                }
            },
            {
                repScore: 95,
                hintMessage: 'Отличное завершение, техника снова на высоте!',
                hintTone: 'low',
                errors: [],
                tips: ['Повтор чистый: держите тот же темп и такую же глубину.'],
                hintCodes: ['good_rep'],
                metrics: {
                    min_knee_angle: 96.0,
                    min_hip_angle: 105.0,
                    max_depth_delta: 0.238,
                    depth_ratio: 0.99,
                    knee_ratio: 0.99,
                    hip_ratio: 0.99,
                    max_torso_forward: 25.0,
                    p90_heel_lift: 0.012,
                    mean_side_view_score: 0.77
                },
                penaltyParts: {
                    torso: 2.0
                },
                ruleFlags: {
                    heel_fail: false,
                    poor_depth: false,
                    undersquat: false,
                    undersquat_severe: false,
                    good_pose: true,
                    excellent_pose: true
                }
            }
        ],
        pushup: [
            {
                repScore: 100,
                hintMessage: 'Отличный повтор: корпус ровный и амплитуда полная.',
                hintTone: 'low',
                errors: [],
                tips: ['Повтор чистый: держите ту же линию корпуса и глубину движения.'],
                hintCodes: ['good_rep'],
                metrics: {
                    min_elbow_angle: 86.0,
                    min_leg_knee_angle: 171.0,
                    p90_depth_delta: 0.208,
                    max_depth_delta: 0.224,
                    p90_body_bend: 7.2,
                    mean_elbow_asym: 2.4,
                    mean_body_asym: 2.8,
                    mean_side_view_score: 0.83,
                    elbow_ratio: 1.0,
                    depth_ratio: 1.01
                },
                penaltyParts: {},
                ruleFlags: {
                    body_fail: false,
                    poor_depth: false,
                    asymmetry: false,
                    good_pose: true,
                    excellent_pose: true
                }
            },
            {
                repScore: 35,
                hintMessage: 'Не задирайте таз: держите тело прямой линией от плеч до пяток.',
                hintTone: 'high',
                errors: ['Ломается линия корпуса'],
                tips: ['Не задирайте таз и не провисайте: соберите корпус в одну прямую линию.'],
                hintCodes: ['body_line_break'],
                metrics: {
                    min_elbow_angle: 89.0,
                    min_leg_knee_angle: 165.0,
                    p90_depth_delta: 0.196,
                    max_depth_delta: 0.209,
                    p90_body_bend: 25.6,
                    mean_elbow_asym: 3.6,
                    mean_body_asym: 4.1,
                    mean_side_view_score: 0.79,
                    elbow_ratio: 0.96,
                    depth_ratio: 0.94
                },
                penaltyParts: {
                    torso: 44.0,
                    stability: 20.0
                },
                ruleFlags: {
                    body_fail: true,
                    poor_depth: false,
                    asymmetry: false,
                    good_pose: false,
                    excellent_pose: false
                }
            },
            {
                repScore: 60,
                hintMessage: 'Не хватает амплитуды: опуститесь ниже и завершайте повтор полностью.',
                hintTone: 'med',
                errors: ['Недостаточная глубина'],
                tips: ['Опускайтесь ниже, чтобы локти сгибались до рабочей глубины без потери контроля корпуса.'],
                hintCodes: ['partial_range'],
                metrics: {
                    min_elbow_angle: 108.0,
                    min_leg_knee_angle: 170.0,
                    p90_depth_delta: 0.126,
                    max_depth_delta: 0.141,
                    p90_body_bend: 8.6,
                    mean_elbow_asym: 3.1,
                    mean_body_asym: 3.3,
                    mean_side_view_score: 0.81,
                    elbow_ratio: 0.79,
                    depth_ratio: 0.63
                },
                penaltyParts: {
                    depth: 26.0,
                    elbow: 12.0
                },
                ruleFlags: {
                    body_fail: false,
                    poor_depth: true,
                    asymmetry: false,
                    good_pose: false,
                    excellent_pose: false
                }
            }
        ]
    };

    function byId(id) {
        return document.getElementById(id);
    }

    function clamp(value, min, max) {
        return Math.max(min, Math.min(max, value));
    }

    function toNumber(value, fallback) {
        var number = Number(value);
        return Number.isFinite(number) ? number : fallback;
    }

    function meanNumber(values, fallback) {
        if (!values || !values.length) {
            return fallback;
        }
        return values.reduce(function (sum, value) {
            return sum + toNumber(value, fallback);
        }, 0) / values.length;
    }

    function calibrationFloor(values, fallback) {
        var numbers;
        var takeCount;

        if (!values || !values.length) {
            return fallback;
        }

        numbers = values.map(function (value) {
            return toNumber(value, fallback);
        }).filter(function (value) {
            return Number.isFinite(value);
        }).sort(function (a, b) {
            return a - b;
        });

        if (!numbers.length) {
            return fallback;
        }

        takeCount = Math.max(3, Math.min(numbers.length, Math.ceil(numbers.length / 3)));
        return meanNumber(numbers.slice(0, takeCount), fallback);
    }

    function formatTime(seconds) {
        var total = Math.max(0, Number(seconds) || 0);
        var mins = Math.floor(total / 60);
        var secs = total % 60;
        return String(mins).padStart(2, '0') + ':' + String(secs).padStart(2, '0');
    }

    function formatScore(value) {
        if (!Number.isFinite(Number(value))) {
            return '-';
        }
        return String(Math.round(Number(value)));
    }

    function qualityLabelForScore(score) {
        if (score >= 85) {
            return 'Отлично';
        }
        if (score >= 60) {
            return 'Нормально';
        }
        return 'Нужно улучшить';
    }

    function loadVoiceSetting() {
        if (!site || typeof site.safeGetStorage !== 'function') {
            return true;
        }
        return site.safeGetStorage(TECHNIQUE_VOICE_STORAGE_KEY) !== '0';
    }

    function persistVoiceSetting(enabled) {
        if (!site || typeof site.safeSetStorage !== 'function') {
            return;
        }
        site.safeSetStorage(TECHNIQUE_VOICE_STORAGE_KEY, enabled ? '1' : '0');
    }

    function isSpeechSupported() {
        return (
            typeof window.Audio === 'function'
            || (!!window.speechSynthesis && typeof window.SpeechSynthesisUtterance === 'function')
        );
    }

    function normalizeSpeechText(text) {
        return String(text || '').replace(/\s+/g, ' ').trim();
    }

    function pickSpeechVoice() {
        var synth = window.speechSynthesis;
        var voices;
        var i;
        var lang;

        if (!synth || typeof synth.getVoices !== 'function') {
            return null;
        }

        voices = synth.getVoices() || [];
        for (i = 0; i < voices.length; i += 1) {
            lang = String(voices[i].lang || '').toLowerCase();
            if (lang === 'ru-ru') {
                return voices[i];
            }
        }
        for (i = 0; i < voices.length; i += 1) {
            lang = String(voices[i].lang || '').toLowerCase();
            if (lang.indexOf('ru') === 0) {
                return voices[i];
            }
        }
        return voices.length ? voices[0] : null;
    }

    function cancelTechniqueVoice(state) {
        if (!state || !state.voiceSupported) {
            return;
        }
        try {
            if (state.currentCueAudio) {
                state.currentCueAudio.pause();
                state.currentCueAudio.currentTime = 0;
            }
            if (window.speechSynthesis) {
                window.speechSynthesis.cancel();
            }
        } catch (error) {
            return;
        }
    }

    function markTechniqueCueSpoken(state, normalizedText, priority) {
        state.lastSpokenText = normalizedText;
        state.lastSpokenTs = Date.now();
        state.lastSpokenPriority = priority;
    }

    function getTechniqueCueAudioUrl(state, code) {
        var exerciseMap;

        if (!state || !code) {
            return '';
        }

        exerciseMap = TECHNIQUE_CUE_AUDIO[state.exerciseSlug] || {};
        return exerciseMap[String(code)] || '';
    }

    function speakTechniqueCueWithBrowser(state, normalizedText, priority, interrupt) {
        var synth;
        var utterance;
        var voice;

        if (!window.speechSynthesis || typeof window.SpeechSynthesisUtterance !== 'function') {
            return;
        }

        synth = window.speechSynthesis;
        if (!synth) {
            return;
        }

        try {
            if (interrupt) {
                synth.cancel();
            } else if (synth.speaking || synth.pending) {
                return;
            }

            utterance = new window.SpeechSynthesisUtterance(normalizedText);
            utterance.lang = 'ru-RU';
            utterance.rate = priority === 'high' ? 0.98 : 1.03;
            utterance.pitch = 1.0;
            voice = pickSpeechVoice();
            if (voice) {
                utterance.voice = voice;
            }

            markTechniqueCueSpoken(state, normalizedText, priority);
            synth.speak(utterance);
        } catch (error) {
            return;
        }
    }

    function speakTechniqueCueWithAudio(state, normalizedText, priority, interrupt, audioUrl) {
        var audio;
        var playResult;

        if (!audioUrl || typeof window.Audio !== 'function') {
            return false;
        }

        try {
            state.cueAudioCache = state.cueAudioCache || {};
            audio = state.cueAudioCache[audioUrl];
            if (!audio) {
                audio = new window.Audio(audioUrl);
                audio.preload = 'auto';
                state.cueAudioCache[audioUrl] = audio;
            }

            if (state.currentCueAudio && state.currentCueAudio !== audio) {
                state.currentCueAudio.pause();
                state.currentCueAudio.currentTime = 0;
            } else if (state.currentCueAudio && interrupt) {
                state.currentCueAudio.pause();
                state.currentCueAudio.currentTime = 0;
            }

            if (window.speechSynthesis) {
                window.speechSynthesis.cancel();
            }

            audio.currentTime = 0;
            state.currentCueAudio = audio;
            playResult = audio.play();
            if (playResult && typeof playResult.then === 'function') {
                playResult
                    .then(function () {
                        markTechniqueCueSpoken(state, normalizedText, priority);
                    })
                    .catch(function () {
                        speakTechniqueCueWithBrowser(state, normalizedText, priority, interrupt);
                    });
            } else {
                markTechniqueCueSpoken(state, normalizedText, priority);
            }
            return true;
        } catch (error) {
            return false;
        }
    }

    function speakTechniqueCue(state, text, options) {
        var normalizedText = normalizeSpeechText(text);
        var now = Date.now();
        var priority = options && options.priority ? String(options.priority) : 'med';
        var dedupeMs = options && Number.isFinite(Number(options.dedupeMs)) ? Number(options.dedupeMs) : 5000;
        var minGapMs = options && Number.isFinite(Number(options.minGapMs)) ? Number(options.minGapMs) : 2200;
        var interrupt = !!(options && options.interrupt);
        var code = options && options.code ? String(options.code) : '';
        var priorityRank;
        var lastPriorityRank;
        var audioUrl;

        if (!state || !state.voiceEnabled || !state.voiceSupported || !normalizedText) {
            return;
        }

        priorityRank = VOICE_PRIORITY_RANK[priority] || VOICE_PRIORITY_RANK.med;
        lastPriorityRank = VOICE_PRIORITY_RANK[state.lastSpokenPriority || 'low'] || VOICE_PRIORITY_RANK.low;

        if (normalizedText === state.lastSpokenText && (now - state.lastSpokenTs) < dedupeMs) {
            return;
        }
        if ((now - state.lastSpokenTs) < minGapMs && priorityRank <= lastPriorityRank && !interrupt) {
            return;
        }

        audioUrl = getTechniqueCueAudioUrl(state, code);
        if (speakTechniqueCueWithAudio(state, normalizedText, priority, interrupt, audioUrl)) {
            return;
        }

        speakTechniqueCueWithBrowser(state, normalizedText, priority, interrupt);
    }

    function maybeSpeakHint(state, text, tone) {
        return;
    }

    function phaseLabel(phase) {
        if (phase === 'WAIT_READY') {
            return 'Калибровка';
        }
        if (phase === 'TOP') {
            return 'Верхняя точка';
        }
        if (phase === 'DOWN') {
            return 'Опускание';
        }
        if (phase === 'RISING') {
            return 'Подъём';
        }
        return 'Ожидание';
    }

    function sessionStatusLabel(state) {
        if (state.isFinishing) {
            return 'Сохраняю сессию';
        }
        if (state.approachActive) {
            return 'Подход активен';
        }
        if (state.cameraReady) {
            return 'Камера готова';
        }
        if (state.loadingCamera) {
            return 'Подключаю камеру';
        }
        return 'Ожидание старта';
    }

    function escapeHtml(text) {
        return site && typeof site.escapeHtml === 'function'
            ? site.escapeHtml(text)
            : String(text == null ? '' : text);
    }

    function distance2d(a, b) {
        var dx = a.x - b.x;
        var dy = a.y - b.y;
        return Math.sqrt(dx * dx + dy * dy);
    }

    function angleDeg(a, b, c) {
        if (!a || !b || !c) {
            return null;
        }
        var bax = a.x - b.x;
        var bay = a.y - b.y;
        var bcx = c.x - b.x;
        var bcy = c.y - b.y;
        var nba = Math.sqrt(bax * bax + bay * bay);
        var nbc = Math.sqrt(bcx * bcx + bcy * bcy);
        var cosine;
        var angle;

        if (nba < 1e-6 || nbc < 1e-6) {
            return null;
        }

        cosine = (bax * bcx + bay * bcy) / (nba * nbc);
        cosine = clamp(cosine, -1, 1);
        angle = Math.acos(cosine) * (180 / Math.PI);
        if (angle <= 12.0) {
            return 10.0;
        }
        return clamp(angle, 10.0, 180.0);
    }

    function pointLineDistance(point, a, b) {
        var abx = b.x - a.x;
        var aby = b.y - a.y;
        var apx = point.x - a.x;
        var apy = point.y - a.y;
        var denom = Math.max(Math.sqrt(abx * abx + aby * aby), 1e-6);
        var cross = Math.abs(abx * apy - aby * apx);
        return cross / denom;
    }

    function weightedPair(a, b, wa, wb) {
        if (a === null && b === null) {
            return null;
        }
        if (a === null) {
            return b;
        }
        if (b === null) {
            return a;
        }
        return (wa * a + wb * b) / Math.max(wa + wb, 1e-6);
    }

    function getPoint(landmarks, index) {
        var lm = landmarks[index];
        if (!lm) {
            return null;
        }
        return {
            x: lm.x,
            y: lm.y,
            z: lm.z || 0,
            visibility: lm.visibility || 0
        };
    }

    function meanVisibility(landmarks, ids) {
        return ids.reduce(function (sum, id) {
            var lm = landmarks[id];
            return sum + (lm && typeof lm.visibility === 'number' ? lm.visibility : 1);
        }, 0) / Math.max(ids.length, 1);
    }

    function estimateSquatSideScore(landmarks, legLen) {
        var lHip = getPoint(landmarks, LANDMARK.L_HIP);
        var rHip = getPoint(landmarks, LANDMARK.R_HIP);
        var lSh = getPoint(landmarks, LANDMARK.L_SHOULDER);
        var rSh = getPoint(landmarks, LANDMARK.R_SHOULDER);
        var xHipNorm;
        var xShNorm;
        var zHipDiff;
        var zShDiff;
        var xComp;
        var xTerm;
        var zComp;
        var zTerm;

        if (!lHip || !rHip || !lSh || !rSh) {
            return 0;
        }

        xHipNorm = Math.abs(lHip.x - rHip.x) / Math.max(legLen, 1e-6);
        xShNorm = Math.abs(lSh.x - rSh.x) / Math.max(legLen, 1e-6);
        zHipDiff = Math.abs(lHip.z - rHip.z);
        zShDiff = Math.abs(lSh.z - rSh.z);
        xComp = 0.65 * xHipNorm + 0.35 * xShNorm;
        xTerm = 1 - clamp(xComp / 0.09, 0, 1);
        zComp = 0.5 * (zHipDiff + zShDiff);
        zTerm = clamp(zComp / 0.16, 0, 1);
        return clamp(0.55 * xTerm + 0.45 * zTerm, 0, 1);
    }

    function estimatePushupSideScore(landmarks, bodyLen) {
        var lHip = getPoint(landmarks, LANDMARK.L_HIP);
        var rHip = getPoint(landmarks, LANDMARK.R_HIP);
        var lSh = getPoint(landmarks, LANDMARK.L_SHOULDER);
        var rSh = getPoint(landmarks, LANDMARK.R_SHOULDER);
        var xHipNorm;
        var xShNorm;
        var zHipDiff;
        var zShDiff;
        var xComp;
        var xTerm;
        var zComp;
        var zTerm;

        if (!lHip || !rHip || !lSh || !rSh) {
            return 0;
        }

        xHipNorm = Math.abs(lHip.x - rHip.x) / Math.max(bodyLen, 1e-6);
        xShNorm = Math.abs(lSh.x - rSh.x) / Math.max(bodyLen, 1e-6);
        zHipDiff = Math.abs(lHip.z - rHip.z);
        zShDiff = Math.abs(lSh.z - rSh.z);
        xComp = 0.6 * xHipNorm + 0.4 * xShNorm;
        xTerm = 1 - clamp(xComp / 0.12, 0, 1);
        zComp = 0.5 * (zHipDiff + zShDiff);
        zTerm = clamp(zComp / 0.12, 0, 1);
        return clamp(0.52 * xTerm + 0.48 * zTerm, 0, 1);
    }

    function torsoTiltDeg(hip, shoulder) {
        var tx = shoulder.x - hip.x;
        var ty = shoulder.y - hip.y;
        var n = Math.sqrt(tx * tx + ty * ty);
        var cosine;

        if (n < 1e-6) {
            return 0;
        }

        cosine = (ty * -1) / n;
        cosine = clamp(cosine, -1, 1);
        return Math.acos(cosine) * (180 / Math.PI);
    }

    function buildSquatMetrics(landmarks) {
        var lSh = getPoint(landmarks, LANDMARK.L_SHOULDER);
        var rSh = getPoint(landmarks, LANDMARK.R_SHOULDER);
        var lHip = getPoint(landmarks, LANDMARK.L_HIP);
        var rHip = getPoint(landmarks, LANDMARK.R_HIP);
        var lKnee = getPoint(landmarks, LANDMARK.L_KNEE);
        var rKnee = getPoint(landmarks, LANDMARK.R_KNEE);
        var lAnk = getPoint(landmarks, LANDMARK.L_ANKLE);
        var rAnk = getPoint(landmarks, LANDMARK.R_ANKLE);
        var lHeel = getPoint(landmarks, LANDMARK.L_HEEL);
        var rHeel = getPoint(landmarks, LANDMARK.R_HEEL);
        var lToe = getPoint(landmarks, LANDMARK.L_FOOT_INDEX);
        var rToe = getPoint(landmarks, LANDMARK.R_FOOT_INDEX);
        var leftKnee;
        var rightKnee;
        var leftHip;
        var rightHip;
        var leftLeg;
        var rightLeg;
        var legLen;
        var leftVis;
        var rightVis;
        var leftValid;
        var rightValid;
        var lw;
        var rw;
        var avgKnee;
        var avgHip;
        var leftDepth;
        var rightDepth;
        var depthNorm;
        var leftHipAnkleVertical;
        var rightHipAnkleVertical;
        var hipAnkleVerticalNorm;
        var leftTorso;
        var rightTorso;
        var torso;
        var leftHeelLift;
        var rightHeelLift;
        var heelLift;

        if (!lSh || !rSh || !lHip || !rHip || !lKnee || !rKnee || !lAnk || !rAnk) {
            return null;
        }

        leftKnee = angleDeg(lHip, lKnee, lAnk);
        rightKnee = angleDeg(rHip, rKnee, rAnk);
        leftHip = angleDeg(lSh, lHip, lKnee);
        rightHip = angleDeg(rSh, rHip, rKnee);
        leftLeg = distance2d(lHip, lKnee) + distance2d(lKnee, lAnk);
        rightLeg = distance2d(rHip, rKnee) + distance2d(rKnee, rAnk);
        legLen = (leftLeg + rightLeg) / 2;
        leftVis = meanVisibility(landmarks, [LANDMARK.L_SHOULDER, LANDMARK.L_HIP, LANDMARK.L_KNEE, LANDMARK.L_ANKLE]);
        rightVis = meanVisibility(landmarks, [LANDMARK.R_SHOULDER, LANDMARK.R_HIP, LANDMARK.R_KNEE, LANDMARK.R_ANKLE]);
        leftValid = leftKnee !== null && leftHip !== null;
        rightValid = rightKnee !== null && rightHip !== null;

        if (!leftValid && !rightValid) {
            return null;
        }

        lw = leftValid ? leftVis : 0;
        rw = rightValid ? rightVis : 0;
        if (lw + rw < 1e-6) {
            lw = leftValid ? 1 : 0;
            rw = rightValid ? 1 : 0;
        }

        avgKnee = weightedPair(leftKnee, rightKnee, lw, rw);
        avgHip = weightedPair(leftHip, rightHip, lw, rw);
        leftDepth = leftValid ? (lAnk.y - lHip.y) / Math.max(leftLeg, 1e-6) : null;
        rightDepth = rightValid ? (rAnk.y - rHip.y) / Math.max(rightLeg, 1e-6) : null;
        depthNorm = weightedPair(leftDepth, rightDepth, lw, rw);
        leftHipAnkleVertical = leftValid ? Math.abs(lHip.y - lAnk.y) / Math.max(leftLeg, 1e-6) : null;
        rightHipAnkleVertical = rightValid ? Math.abs(rHip.y - rAnk.y) / Math.max(rightLeg, 1e-6) : null;
        hipAnkleVerticalNorm = weightedPair(leftHipAnkleVertical, rightHipAnkleVertical, lw, rw);

        if (avgKnee === null || avgHip === null || depthNorm === null || hipAnkleVerticalNorm === null) {
            return null;
        }

        leftTorso = leftValid ? torsoTiltDeg(lHip, lSh) : null;
        rightTorso = rightValid ? torsoTiltDeg(rHip, rSh) : null;
        torso = weightedPair(leftTorso, rightTorso, lw, rw);
        if (torso === null) {
            torso = 0;
        }

        leftHeelLift = leftValid && lHeel && lToe
            ? Math.max(0, lToe.y - lHeel.y) / Math.max(leftLeg, 1e-6)
            : null;
        rightHeelLift = rightValid && rHeel && rToe
            ? Math.max(0, rToe.y - rHeel.y) / Math.max(rightLeg, 1e-6)
            : null;
        heelLift = weightedPair(leftHeelLift, rightHeelLift, lw, rw);
        if (heelLift === null) {
            heelLift = 0;
        }

        return {
            primary_angle: avgKnee,
            secondary_angle: avgHip,
            depth_norm: depthNorm,
            torso_angle: torso,
            asymmetry: leftKnee !== null && rightKnee !== null ? Math.abs(leftKnee - rightKnee) : 0,
            hip_asymmetry: leftHip !== null && rightHip !== null ? Math.abs(leftHip - rightHip) : 0,
            side_view_score: estimateSquatSideScore(landmarks, legLen),
            heel_lift_norm: heelLift,
            leg_angle: 180,
            posture_tilt_deg: Math.abs(90 - torso),
            hip_ankle_vertical_norm: hipAnkleVerticalNorm
        };
    }

    function buildPushupMetrics(landmarks) {
        var lSh = getPoint(landmarks, LANDMARK.L_SHOULDER);
        var rSh = getPoint(landmarks, LANDMARK.R_SHOULDER);
        var lEl = getPoint(landmarks, LANDMARK.L_ELBOW);
        var rEl = getPoint(landmarks, LANDMARK.R_ELBOW);
        var lWr = getPoint(landmarks, LANDMARK.L_WRIST);
        var rWr = getPoint(landmarks, LANDMARK.R_WRIST);
        var lHip = getPoint(landmarks, LANDMARK.L_HIP);
        var rHip = getPoint(landmarks, LANDMARK.R_HIP);
        var lKnee = getPoint(landmarks, LANDMARK.L_KNEE);
        var rKnee = getPoint(landmarks, LANDMARK.R_KNEE);
        var lAnk = getPoint(landmarks, LANDMARK.L_ANKLE);
        var rAnk = getPoint(landmarks, LANDMARK.R_ANKLE);
        var lLowerAnchor = lAnk || lKnee || lHip;
        var rLowerAnchor = rAnk || rKnee || rHip;
        var leftElbow;
        var rightElbow;
        var leftBody;
        var rightBody;
        var leftLegKnee;
        var rightLegKnee;
        var leftBodyLen;
        var rightBodyLen;
        var bodyLen;
        var leftVis;
        var rightVis;
        var leftValid;
        var rightValid;
        var lw;
        var rw;
        var avgElbow;
        var avgBody;
        var avgLeg;
        var leftDepth;
        var rightDepth;
        var depthNorm;
        var leftHipAnkleVertical;
        var rightHipAnkleVertical;
        var hipAnkleVerticalNorm;
        var leftTilt;
        var rightTilt;
        var postureTilt;
        var leftBreak;
        var rightBreak;
        var bodyBreak;
        var leftDev;
        var rightDev;
        var hipDeviation;

        if (!lSh || !rSh || !lEl || !rEl || !lWr || !rWr || !lHip || !rHip || (!lLowerAnchor && !rLowerAnchor)) {
            return null;
        }

        leftElbow = angleDeg(lSh, lEl, lWr);
        rightElbow = angleDeg(rSh, rEl, rWr);
        leftBody = lLowerAnchor ? angleDeg(lSh, lHip, lLowerAnchor) : null;
        rightBody = rLowerAnchor ? angleDeg(rSh, rHip, rLowerAnchor) : null;
        leftLegKnee = lKnee && lLowerAnchor ? angleDeg(lHip, lKnee, lLowerAnchor) : null;
        rightLegKnee = rKnee && rLowerAnchor ? angleDeg(rHip, rKnee, rLowerAnchor) : null;
        leftBodyLen = lLowerAnchor ? distance2d(lSh, lHip) + distance2d(lHip, lLowerAnchor) : 0;
        rightBodyLen = rLowerAnchor ? distance2d(rSh, rHip) + distance2d(rHip, rLowerAnchor) : 0;
        bodyLen = (leftBodyLen + rightBodyLen) / 2;
        leftVis = meanVisibility(landmarks, [LANDMARK.L_SHOULDER, LANDMARK.L_ELBOW, LANDMARK.L_WRIST, LANDMARK.L_HIP, lAnk ? LANDMARK.L_ANKLE : LANDMARK.L_KNEE]);
        rightVis = meanVisibility(landmarks, [LANDMARK.R_SHOULDER, LANDMARK.R_ELBOW, LANDMARK.R_WRIST, LANDMARK.R_HIP, rAnk ? LANDMARK.R_ANKLE : LANDMARK.R_KNEE]);
        leftValid = leftElbow !== null && leftBody !== null;
        rightValid = rightElbow !== null && rightBody !== null;

        if (!leftValid && !rightValid) {
            return null;
        }

        lw = leftValid ? leftVis : 0;
        rw = rightValid ? rightVis : 0;
        if (lw + rw < 1e-6) {
            lw = leftValid ? 1 : 0;
            rw = rightValid ? 1 : 0;
        }

        avgElbow = weightedPair(leftElbow, rightElbow, lw, rw);
        avgBody = weightedPair(leftBody, rightBody, lw, rw);
        avgLeg = weightedPair(leftLegKnee, rightLegKnee, lw, rw);
        leftDepth = leftValid && lLowerAnchor ? (lLowerAnchor.y - lSh.y) / Math.max(leftBodyLen, 1e-6) : null;
        rightDepth = rightValid && rLowerAnchor ? (rLowerAnchor.y - rSh.y) / Math.max(rightBodyLen, 1e-6) : null;
        depthNorm = weightedPair(leftDepth, rightDepth, lw, rw);
        leftHipAnkleVertical = leftValid && lLowerAnchor ? Math.abs(lHip.y - lLowerAnchor.y) / Math.max(leftBodyLen, 1e-6) : null;
        rightHipAnkleVertical = rightValid && rLowerAnchor ? Math.abs(rHip.y - rLowerAnchor.y) / Math.max(rightBodyLen, 1e-6) : null;
        hipAnkleVerticalNorm = weightedPair(leftHipAnkleVertical, rightHipAnkleVertical, lw, rw);
        leftTilt = leftValid
            ? Math.atan2(Math.abs(lSh.y - lHip.y), Math.max(Math.abs(lSh.x - lHip.x), 1e-6)) * (180 / Math.PI)
            : null;
        rightTilt = rightValid
            ? Math.atan2(Math.abs(rSh.y - rHip.y), Math.max(Math.abs(rSh.x - rHip.x), 1e-6)) * (180 / Math.PI)
            : null;
        postureTilt = weightedPair(leftTilt, rightTilt, lw, rw);

        if (avgElbow === null || avgBody === null || depthNorm === null || hipAnkleVerticalNorm === null || postureTilt === null) {
            return null;
        }

        leftBreak = leftValid ? Math.max(0, 180 - leftBody) : null;
        rightBreak = rightValid ? Math.max(0, 180 - rightBody) : null;
        bodyBreak = weightedPair(leftBreak, rightBreak, lw, rw);
        if (bodyBreak === null) {
            bodyBreak = 0;
        }

        leftDev = leftValid && lLowerAnchor ? pointLineDistance(lHip, lSh, lLowerAnchor) / Math.max(leftBodyLen, 1e-6) : null;
        rightDev = rightValid && rLowerAnchor ? pointLineDistance(rHip, rSh, rLowerAnchor) / Math.max(rightBodyLen, 1e-6) : null;
        hipDeviation = weightedPair(leftDev, rightDev, lw, rw);
        if (hipDeviation === null) {
            hipDeviation = 0;
        }

        return {
            primary_angle: avgElbow,
            secondary_angle: avgBody,
            depth_norm: depthNorm,
            torso_angle: bodyBreak,
            asymmetry: leftElbow !== null && rightElbow !== null ? Math.abs(leftElbow - rightElbow) : 0,
            hip_asymmetry: leftBody !== null && rightBody !== null ? Math.abs(leftBody - rightBody) : 0,
            side_view_score: estimatePushupSideScore(landmarks, bodyLen),
            heel_lift_norm: Math.max(0, hipDeviation),
            leg_angle: avgLeg === null ? 180 : avgLeg,
            posture_tilt_deg: postureTilt,
            hip_ankle_vertical_norm: hipAnkleVerticalNorm
        };
    }

    function buildPushupDemoSide(shoulder, elbow, wrist, hip, knee, ankle, landmarks) {
        var lowerAnchor = ankle || knee || hip;
        var bodyLen;
        var elbowAngle;
        var bodyAngle;
        var depthNorm;
        var hipLowerVerticalNorm;
        var postureTilt;
        var bodyBreak;
        var hipDeviation;
        var legAngle;

        if (!shoulder || !hip || !lowerAnchor) {
            return null;
        }

        bodyLen = distance2d(shoulder, hip) + distance2d(hip, lowerAnchor);
        if (bodyLen < 1e-6) {
            return null;
        }

        elbowAngle = elbow
            ? angleDeg(shoulder, elbow, wrist || hip || lowerAnchor)
            : null;
        bodyAngle = angleDeg(shoulder, hip, lowerAnchor);
        depthNorm = (lowerAnchor.y - shoulder.y) / Math.max(bodyLen, 1e-6);
        hipLowerVerticalNorm = Math.abs(hip.y - lowerAnchor.y) / Math.max(bodyLen, 1e-6);
        postureTilt = Math.atan2(
            Math.abs(shoulder.y - hip.y),
            Math.max(Math.abs(shoulder.x - hip.x), 1e-6)
        ) * (180 / Math.PI);
        bodyBreak = bodyAngle === null ? Math.max(0, 90 - postureTilt) : Math.max(0, 180 - bodyAngle);
        hipDeviation = pointLineDistance(hip, shoulder, lowerAnchor) / Math.max(bodyLen, 1e-6);
        legAngle = knee ? angleDeg(hip, knee, lowerAnchor) : 180;

        return {
            primaryAngle: elbowAngle,
            bodyAngle: bodyAngle,
            depthNorm: depthNorm,
            hipLowerVerticalNorm: hipLowerVerticalNorm,
            postureTilt: postureTilt,
            bodyBreak: bodyBreak,
            hipDeviation: hipDeviation,
            legAngle: legAngle === null ? 180 : legAngle,
            sideViewScore: estimatePushupSideScore(landmarks, bodyLen),
            bodyLen: bodyLen
        };
    }

    function buildPushupDemoMetrics(landmarks) {
        var left = buildPushupDemoSide(
            getPoint(landmarks, LANDMARK.L_SHOULDER),
            getPoint(landmarks, LANDMARK.L_ELBOW),
            getPoint(landmarks, LANDMARK.L_WRIST),
            getPoint(landmarks, LANDMARK.L_HIP),
            getPoint(landmarks, LANDMARK.L_KNEE),
            getPoint(landmarks, LANDMARK.L_ANKLE),
            landmarks
        );
        var right = buildPushupDemoSide(
            getPoint(landmarks, LANDMARK.R_SHOULDER),
            getPoint(landmarks, LANDMARK.R_ELBOW),
            getPoint(landmarks, LANDMARK.R_WRIST),
            getPoint(landmarks, LANDMARK.R_HIP),
            getPoint(landmarks, LANDMARK.R_KNEE),
            getPoint(landmarks, LANDMARK.R_ANKLE),
            landmarks
        );
        var lw;
        var rw;
        var bodyLen;
        var avgPrimary;
        var avgBody;
        var avgDepth;
        var avgHipLower;
        var avgTilt;
        var avgBodyBreak;
        var avgDeviation;
        var avgLeg;

        if (!left && !right) {
            return null;
        }

        lw = left ? 1 : 0;
        rw = right ? 1 : 0;
        bodyLen = ((left ? left.bodyLen : 0) + (right ? right.bodyLen : 0)) / Math.max(lw + rw, 1);
        avgPrimary = weightedPair(left && left.primaryAngle, right && right.primaryAngle, lw, rw);
        avgBody = weightedPair(left && left.bodyAngle, right && right.bodyAngle, lw, rw);
        avgDepth = weightedPair(left && left.depthNorm, right && right.depthNorm, lw, rw);
        avgHipLower = weightedPair(left && left.hipLowerVerticalNorm, right && right.hipLowerVerticalNorm, lw, rw);
        avgTilt = weightedPair(left && left.postureTilt, right && right.postureTilt, lw, rw);
        avgBodyBreak = weightedPair(left && left.bodyBreak, right && right.bodyBreak, lw, rw);
        avgDeviation = weightedPair(left && left.hipDeviation, right && right.hipDeviation, lw, rw);
        avgLeg = weightedPair(left && left.legAngle, right && right.legAngle, lw, rw);

        return {
            primary_angle: avgPrimary === null ? 170 : avgPrimary,
            secondary_angle: avgBody === null ? 176 : avgBody,
            depth_norm: avgDepth === null ? 0.46 : avgDepth,
            torso_angle: avgBodyBreak === null ? 0 : avgBodyBreak,
            asymmetry: left && right && left.primaryAngle !== null && right.primaryAngle !== null
                ? Math.abs(left.primaryAngle - right.primaryAngle)
                : 0,
            hip_asymmetry: left && right && left.bodyAngle !== null && right.bodyAngle !== null
                ? Math.abs(left.bodyAngle - right.bodyAngle)
                : 0,
            side_view_score: Math.max(
                0.08,
                weightedPair(left && left.sideViewScore, right && right.sideViewScore, lw, rw) || estimatePushupSideScore(landmarks, bodyLen || 1)
            ),
            heel_lift_norm: Math.max(0, avgDeviation === null ? 0 : avgDeviation),
            leg_angle: avgLeg === null ? 180 : avgLeg,
            posture_tilt_deg: avgTilt === null ? 45 : avgTilt,
            hip_ankle_vertical_norm: avgHipLower === null ? 0.72 : avgHipLower
        };
    }

    function smoothMetric(queue, value, maxSize) {
        queue.push(value);
        if (queue.length > maxSize) {
            queue.shift();
        }
        return queue.reduce(function (sum, item) {
            return sum + item;
        }, 0) / queue.length;
    }

    function createController(options) {
        var state = {
            sessionId: toNumber(options.sessionId, 0),
            exerciseSlug: String(options.exerciseSlug || 'squat'),
            exerciseTitle: String(options.exerciseTitle || 'Упражнение'),
            motionFamily: String(options.motionFamily || 'squat_like'),
            viewType: String(options.viewType || 'side'),
            profileId: toNumber(options.profileId, null),
            referenceBased: options.referenceBased !== false,
            cameraReady: false,
            cameraTone: 'loading',
            cameraMessage: 'Подключаю камеру...',
            loadingCamera: false,
            approachActive: false,
            pose: null,
            stream: null,
            animationFrame: null,
            poseBusy: false,
            timerHandle: null,
            startTs: null,
            elapsedSec: 0,
            calibrationFrames: [],
            baselinePrimary: null,
            baselineDepth: null,
            baselineHeel: null,
            baselinePrimaryInitial: null,
            baselineDepthInitial: null,
            currentState: 'WAIT_READY',
            preRoll: [],
            repFrames: [],
            reps: [],
            repIndex: 0,
            minPrimary: 999,
            maxDepth: 0,
            maxTorso: 0,
            downCounter: 0,
            riseCounter: 0,
            upCounter: 0,
            cooldown: 0,
            postureMismatchFrames: 0,
            smoothPrimary: [],
            smoothDepth: [],
            smoothSecondary: [],
            smoothHeel: [],
            latestQuality: 'Ожидание',
            latestRepScore: null,
            latestHint: 'Развернитесь боком к камере и нажмите «Начать».',
            liveHintTone: 'low',
            repHintPinned: false,
            lastHintUpdateTs: 0,
            hintLockUntilTs: 0,
            descentArmed: false,
            descentTrendCounter: 0,
            lastPrimaryAngle: null,
            topReadyFrames: 0,
            avgScore: null,
            scoringRep: false,
            liveRequestPending: false,
            lastLiveRequestTs: 0,
            isFinishing: false,
            sessionFinished: false,
            redirectUrl: '/app/catalog',
            destroyed: false,
            assetsPromise: null,
            finishedUi: null,
            voiceEnabled: loadVoiceSetting(),
            voiceSupported: isSpeechSupported(),
            lastSpokenText: '',
            lastSpokenTs: 0,
            lastSpokenPriority: 'low',
            cueAudioCache: {},
            currentCueAudio: null
        };

        function isPushupDemoMode() {
            return (
                state.exerciseSlug === 'pushup'
                && !!site
                && typeof site.safeGetStorage === 'function'
                && site.safeGetStorage(PUSHUP_DEMO_STORAGE_KEY) === '1'
            );
        }

        function getConfig() {
            var baseConfig = EXERCISE_CONFIG[state.exerciseSlug] || EXERCISE_CONFIG.squat;

            if (isPushupDemoMode()) {
                return Object.assign({}, baseConfig, {
                    minStateFrames: 1,
                    minRepFrames: 4,
                    downEnterPrimaryDrop: 7.0,
                    downEnterDepthDelta: 0.012,
                    risingRecoverPrimary: 3.0,
                    risingRecoverDepth: 0.006,
                    upPrimaryTolerance: 34.0,
                    upDepthTolerance: 0.12,
                    minPrimaryAmplitude: 7.0,
                    minDepthAmplitude: 0.012,
                    minTorsoMotion: 0.1,
                    preRollFrames: 3
                });
            }

            return baseConfig;
        }

        function currentCompareEndpoint() {
            return '/api/technique/sessions/' + state.sessionId + '/compare';
        }

        function currentLiveEndpoint() {
            return '/api/technique/sessions/' + state.sessionId + '/live';
        }

        function primaryTravel(cfg, baseline, currentValue) {
            if (cfg.primaryDirection === 'rise') {
                return Math.max(0, currentValue - baseline);
            }
            return Math.max(0, baseline - currentValue);
        }

        function updatePrimaryExtremum(cfg, previous, currentValue, initializing) {
            if (initializing) {
                return currentValue;
            }
            if (cfg.primaryDirection === 'rise') {
                return Math.max(previous, currentValue);
            }
            return Math.min(previous, currentValue);
        }

        function recoverFromExtremum(cfg, currentValue, extremum, recoverThreshold) {
            if (cfg.primaryDirection === 'rise') {
                return currentValue <= extremum - recoverThreshold;
            }
            return currentValue >= extremum + recoverThreshold;
        }

        function withinTopTolerance(cfg, currentValue, baseline, tolerance) {
            if (cfg.primaryDirection === 'rise') {
                return currentValue <= baseline + tolerance;
            }
            return currentValue >= baseline - tolerance;
        }

        function averageScore(reps) {
            if (!reps.length) {
                return null;
            }
            return reps.reduce(function (sum, rep) {
                return sum + toNumber(rep.repScore, 0);
            }, 0) / reps.length;
        }

        function updateSummary() {
            var summarySection = byId('tech-summary-section');
            var summaryNode = byId('tech-summary');
            var avg;
            var errorCounter;
            var tipCounter;
            var topErrors;
            var topTips;
            var lastRepsHtml;

            if (!summaryNode) {
                return;
            }

            if (summarySection) {
                summarySection.hidden = !state.sessionFinished;
            }

            if (!state.sessionFinished) {
                summaryNode.innerHTML = '';
                return;
            }

            if (state.finishedUi && state.finishedUi.summary) {
                summaryNode.innerHTML = [
                    '<div class="tech-summary-grid">',
                    '<article class="tech-summary-tile"><span>Средний score</span><strong>', formatScore(state.finishedUi.summary.score), '</strong></article>',
                    '<article class="tech-summary-tile"><span>Качество</span><strong>', escapeHtml(state.finishedUi.summary.qualityLabel || 'нужно улучшить'), '</strong></article>',
                    '<article class="tech-summary-tile"><span>Повторы</span><strong>', formatScore(state.finishedUi.summary.repsCount), '</strong></article>',
                    '</div>',
                    '<div class="tech-summary-stack">',
                    (state.finishedUi.topIssues || []).slice(0, 2).map(function (issue) {
                        return '<article class="tech-summary-note"><strong>' + escapeHtml(issue.title || 'Техника') + '</strong><p>' + escapeHtml(issue.explanation || '') + '</p></article>';
                    }).join(''),
                    (state.finishedUi.recommendations || []).slice(0, 2).map(function (item) {
                        return '<article class="tech-summary-note is-accent"><strong>Следующий фокус</strong><p>' + escapeHtml(item.advice || '') + '</p></article>';
                    }).join(''),
                    '</div>'
                ].join('');
                return;
            }

            if (!state.reps.length) {
                summaryNode.innerHTML = '<p class="muted-text">Подход завершен без засчитанных повторов.</p>';
                return;
            }

            avg = averageScore(state.reps);
            errorCounter = {};
            tipCounter = {};
            state.reps.forEach(function (rep) {
                rep.errors.forEach(function (error) {
                    errorCounter[error] = (errorCounter[error] || 0) + 1;
                });
                rep.tips.forEach(function (tip) {
                    tipCounter[tip] = (tipCounter[tip] || 0) + 1;
                });
            });
            topErrors = Object.keys(errorCounter).sort(function (a, b) {
                return errorCounter[b] - errorCounter[a];
            }).slice(0, 2);
            topTips = Object.keys(tipCounter).sort(function (a, b) {
                return tipCounter[b] - tipCounter[a];
            }).slice(0, 2);
            lastRepsHtml = state.reps.slice(-3).map(function (rep) {
                return '<span class="tech-rep-chip">#' + rep.repIndex + ' · ' + formatScore(rep.repScore) + '</span>';
            }).join('');

            summaryNode.innerHTML = [
                '<div class="tech-summary-grid">',
                '<article class="tech-summary-tile"><span>Средний score</span><strong>', formatScore(avg), '</strong></article>',
                '<article class="tech-summary-tile"><span>Повторы</span><strong>', state.reps.length, '</strong></article>',
                '<article class="tech-summary-tile"><span>Последний</span><strong>', formatScore(state.latestRepScore), '</strong></article>',
                '</div>',
                '<div class="tech-summary-chips">', lastRepsHtml, '</div>',
                '<div class="tech-summary-stack">',
                topErrors.length ? '<article class="tech-summary-note"><strong>Главная ошибка</strong><p>' + escapeHtml(topErrors[0]) + '</p></article>' : '',
                topTips.length ? '<article class="tech-summary-note is-accent"><strong>Следующий фокус</strong><p>' + escapeHtml(topTips[0]) + '</p></article>' : '',
                '</div>'
            ].join('');
        }

        function renderTechniqueUi() {
            var repCounter = byId('tech-rep-counter');
            var timerNode = byId('tech-timer');
            var lastScoreNode = byId('tech-last-score');
            var qualityNode = byId('tech-quality-pill');
            var hintNode = byId('tech-live-hint');
            var cameraBadge = byId('tech-camera-badge');
            var startButton = byId('tech-start-btn');
            var voiceButton = byId('tech-voice-btn');
            var stopButton = byId('tech-stop-btn');

            if (repCounter) {
                repCounter.textContent = String(state.reps.length);
            }
            if (timerNode) {
                timerNode.textContent = formatTime(state.elapsedSec);
            }
            if (lastScoreNode) {
                lastScoreNode.textContent = formatScore(state.latestRepScore);
            }
            if (qualityNode) {
                qualityNode.textContent = state.latestQuality;
                qualityNode.classList.remove('is-good', 'is-mid', 'is-bad');
                if (state.latestQuality === 'Отлично') {
                    qualityNode.classList.add('is-good');
                } else if (state.latestQuality === 'Нормально') {
                    qualityNode.classList.add('is-mid');
                } else if (state.latestQuality === 'Нужно улучшить') {
                    qualityNode.classList.add('is-bad');
                }
            }
            if (hintNode) {
                hintNode.textContent = state.latestHint;
                hintNode.classList.remove('is-high', 'is-med', 'is-low');
                hintNode.classList.add('is-' + (state.liveHintTone || 'low'));
            }
            if (cameraBadge) {
                cameraBadge.textContent = state.cameraMessage;
                cameraBadge.classList.remove('is-loading', 'is-live', 'is-error');
                cameraBadge.classList.add(state.cameraTone === 'error' ? 'is-error' : (state.cameraReady ? 'is-live' : 'is-loading'));
            }
            if (startButton) {
                startButton.disabled = state.loadingCamera || state.approachActive || state.isFinishing || state.sessionFinished;
            }
            if (voiceButton) {
                voiceButton.disabled = !state.voiceSupported;
                voiceButton.textContent = state.voiceSupported
                    ? (state.voiceEnabled ? 'Голос: вкл' : 'Голос: выкл')
                    : 'Голос недоступен';
                voiceButton.setAttribute('aria-pressed', state.voiceEnabled ? 'true' : 'false');
            }
            if (stopButton) {
                stopButton.disabled = state.isFinishing || (!state.sessionFinished && !state.cameraReady && !state.reps.length && !state.approachActive);
                if (state.isFinishing) {
                    stopButton.textContent = 'Сохраняю...';
                } else if (state.sessionFinished) {
                    stopButton.textContent = 'К упражнениям';
                } else {
                    stopButton.textContent = 'Стоп';
                }
            }

            updateSummary();
        }

        function resetTechniqueState(clearReps) {
            state.approachActive = false;
            state.startTs = null;
            state.elapsedSec = 0;
            state.calibrationFrames = [];
            state.baselinePrimary = null;
            state.baselineDepth = null;
            state.baselineHeel = null;
            state.baselinePrimaryInitial = null;
            state.baselineDepthInitial = null;
            state.currentState = 'WAIT_READY';
            state.preRoll = [];
            state.repFrames = [];
            state.minPrimary = getConfig().primaryDirection === 'rise' ? -999 : 999;
            state.maxDepth = 0;
            state.maxTorso = 0;
            state.downCounter = 0;
            state.riseCounter = 0;
            state.upCounter = 0;
            state.cooldown = 0;
            state.postureMismatchFrames = 0;
            state.smoothPrimary = [];
            state.smoothDepth = [];
            state.smoothSecondary = [];
            state.smoothHeel = [];
            state.latestQuality = 'Ожидание';
            state.latestRepScore = null;
            state.latestHint = 'Развернитесь боком к камере и нажмите «Начать».';
            state.liveHintTone = 'low';
            state.repHintPinned = false;
            state.lastHintUpdateTs = 0;
            state.hintLockUntilTs = 0;
            state.descentArmed = false;
            state.descentTrendCounter = 0;
            state.lastPrimaryAngle = null;
            state.topReadyFrames = 0;
            state.finishedUi = null;
            state.sessionFinished = false;
            state.lastSpokenText = '';
            state.lastSpokenTs = 0;
            state.lastSpokenPriority = 'low';

            if (clearReps) {
                state.reps = [];
                state.repIndex = 0;
                state.avgScore = null;
            }

            if (state.timerHandle) {
                window.clearInterval(state.timerHandle);
                state.timerHandle = null;
            }
        }

        function isExercisePostureMatch(frame) {
            if (!frame) {
                return false;
            }

            if (state.motionFamily === 'squat_like' || state.motionFamily === 'lunge_like') {
                return (
                    toNumber(frame.side_view_score, 0) >= 0.22
                    && toNumber(frame.torso_angle, 90) <= 68
                    && toNumber(frame.hip_ankle_vertical_norm, 0) >= 0.22
                );
            }

            if (isPushupDemoMode()) {
                return (
                    toNumber(frame.side_view_score, 0) >= 0.02
                    && toNumber(frame.posture_tilt_deg, 90) <= 85
                    && toNumber(frame.hip_ankle_vertical_norm, 1) <= 1.1
                );
            }

            if (state.motionFamily === 'push_like') {
                return (
                    toNumber(frame.side_view_score, 0) >= 0.35
                    && toNumber(frame.posture_tilt_deg, 90) <= 34
                    && toNumber(frame.hip_ankle_vertical_norm, 1) <= 0.45
                );
            }

            return (
                toNumber(frame.side_view_score, 0) >= 0.35
                && toNumber(frame.posture_tilt_deg, 90) <= 48
            );
        }

        function buildLocalRealtimeHint(current, phase, cfg) {
            if (state.motionFamily === 'squat_like' || state.motionFamily === 'lunge_like') {
                var baselinePrimary = toNumber(state.baselinePrimary, current.primary_angle);
                var baselineHeel = Math.max(0, toNumber(state.baselineHeel, 0));
                var primaryDrop = primaryTravel(cfg, baselinePrimary, toNumber(current.primary_angle, baselinePrimary));
                var depthDelta = toNumber(current.depth_delta, 0);
                var heelLift = toNumber(current.heel_lift_norm, 0);
                var heelLiftDelta = Math.max(0, heelLift - baselineHeel);
                var torsoAngle = toNumber(current.torso_angle, 0);
                var asymmetry = toNumber(current.asymmetry, 0);
                var sideView = toNumber(current.side_view_score, 0);

                if (
                    (phase === 'DOWN' || phase === 'RISING')
                    && sideView >= 0.62
                    && primaryDrop >= cfg.downEnterPrimaryDrop * 0.4
                    && depthDelta >= cfg.downEnterDepthDelta * 0.75
                    && heelLiftDelta > 0.055
                    && heelLift > Math.max(0.075, baselineHeel + 0.03)
                ) {
                    return { tone: 'high', text: 'Пятки на пол, уменьшите глубину на 10-15%.' };
                }
                if (phase === 'DOWN' && primaryDrop >= cfg.downEnterPrimaryDrop * 0.45 && depthDelta < cfg.downEnterDepthDelta * 0.84) {
                    return { tone: 'med', text: 'Добавьте глубину приседа до рабочего уровня.' };
                }
                if (torsoAngle > 52) {
                    return { tone: 'med', text: 'Грудь выше, темп вниз медленнее.' };
                }
                if (asymmetry > 14) {
                    return { tone: 'med', text: 'Двигайтесь симметрично, без перекоса сторон.' };
                }
                if (phase === 'RISING') {
                    return { tone: 'low', text: 'Поднимайтесь ровно, без рывка.' };
                }
                return { tone: 'low', text: 'Темп ровный, амплитуда стабильная.' };
            }

            if (state.motionFamily === 'push_like') {
                if (toNumber(current.leg_angle, 180) < 132) {
                    return { tone: 'high', text: 'Выпрямите ноги и держите корпус одной линией.' };
                }
                if (toNumber(current.torso_angle, 0) > 16) {
                    return { tone: 'med', text: 'Не проваливайте таз, корпус держите ровнее.' };
                }
                if (phase === 'DOWN' && toNumber(current.depth_delta, 0) < cfg.downEnterDepthDelta * 0.7) {
                    return { tone: 'med', text: 'Опуститесь чуть ниже без провала внизу.' };
                }
                return { tone: 'low', text: phase === 'RISING' ? 'Поднимайтесь без рывка.' : 'Контролируйте локти и глубину.' };
            }

            if (state.exerciseSlug === 'glute_bridge') {
                if (primaryTravel(cfg, toNumber(state.baselinePrimary, current.primary_angle), current.primary_angle) < cfg.minPrimaryAmplitude * 0.5 && phase === 'DOWN') {
                    return { tone: 'med', text: 'Поднимайте таз выше и фиксируйте верхнюю точку.' };
                }
                if (toNumber(current.asymmetry, 0) > 16) {
                    return { tone: 'med', text: 'Держите таз ровно, без перекоса сторон.' };
                }
                return { tone: 'low', text: phase === 'RISING' ? 'Опускайтесь плавно.' : 'Подъём таза под контролем.' };
            }

            if (toNumber(current.asymmetry, 0) > 18) {
                return { tone: 'med', text: 'Двигайтесь симметрично и без раскачки.' };
            }
            if (phase === 'DOWN' && toNumber(current.depth_delta, 0) < cfg.downEnterDepthDelta * 0.7) {
                return { tone: 'med', text: 'Добавьте амплитуду без рывка.' };
            }
            return { tone: 'low', text: phase === 'RISING' ? 'Возвращайтесь плавно.' : 'Корпус стабилен, темп ровный.' };
        }

        function applyRealtimeHint(current, phase, cfg) {
            var hint = buildLocalRealtimeHint(current, phase, cfg);
            var toneRank = { low: 1, med: 2, high: 3 };
            var now = Date.now();
            var currentTone = state.liveHintTone || 'low';
            var nextTone = hint.tone || 'low';
            var currentRank = toneRank[currentTone] || 1;
            var nextRank = toneRank[nextTone] || 1;
            var minInterval = nextRank > currentRank ? 100 : 700;
            var textChanged = hint.text !== state.latestHint;
            var timePassed = (now - (state.lastHintUpdateTs || 0)) >= minInterval;

            if (!textChanged && currentTone === nextTone) {
                return;
            }
            if (currentTone === 'high' && now < (state.hintLockUntilTs || 0) && nextRank < currentRank) {
                return;
            }
            if (!timePassed && nextRank <= currentRank) {
                return;
            }

            state.latestHint = hint.text;
            state.liveHintTone = nextTone;
            state.lastHintUpdateTs = now;
            if (nextTone === 'high') {
                state.hintLockUntilTs = now + 900;
            }
            maybeSpeakHint(state, hint.text, nextTone);
        }

        function requestLiveHint(current, phase) {
            var now = Date.now();
            var payload;

            if (isDemoScoringEnabled() || !state.approachActive || state.liveRequestPending || (now - state.lastLiveRequestTs) < 320) {
                return;
            }

            state.liveRequestPending = true;
            state.lastLiveRequestTs = now;
            payload = {
                phase: phase,
                frame_metric: current,
                baseline_snapshot: {
                    baseline_primary: state.baselinePrimary,
                    baseline_depth: state.baselineDepth,
                    baseline_heel: state.baselineHeel,
                    baseline_primary_initial: state.baselinePrimaryInitial,
                    baseline_depth_initial: state.baselineDepthInitial
                }
            };

            site.sendJson(
                currentLiveEndpoint(),
                'POST',
                payload,
                'Не удалось получить live-подсказку.'
            )
                .then(function (response) {
                    if (state.destroyed) {
                        return;
                    }
                    if (state.repHintPinned && response.tone !== 'high') {
                        return;
                    }
                    state.latestHint = String(response.hint || state.latestHint);
                    state.liveHintTone = String(response.tone || state.liveHintTone);
                    maybeSpeakHint(state, state.latestHint, state.liveHintTone);
                    renderTechniqueUi();
                })
                .catch(function (error) {
                    if (error && String(error.message || '').indexOf('не совпадает с текущей technique-сессией') >= 0) {
                        site.requireJson(
                            '/api/technique/sessions/' + state.sessionId,
                            null,
                            'Не удалось обновить technique-сессию.'
                        )
                            .then(function (session) {
                                var exercise = site.ensureObject(session.exercise);
                                var titleNode = byId('tech-exercise-name');

                                state.exerciseSlug = site.ensureString(exercise.slug, state.exerciseSlug);
                                state.exerciseTitle = site.ensureString(exercise.title, state.exerciseTitle);
                                state.motionFamily = site.ensureString(exercise.motion_family, state.motionFamily);
                                state.viewType = site.ensureString(exercise.view_type, state.viewType);
                                state.profileId = site.ensureFiniteNumber(exercise.profile_id);
                                state.referenceBased = exercise.reference_based === true;
                                if (titleNode) {
                                    titleNode.textContent = state.exerciseTitle;
                                }
                            })
                            .catch(function () {
                                return;
                            });
                    }
                    return;
                })
                .finally(function () {
                    state.liveRequestPending = false;
                });
        }

        function validateRep(repFrames, cfg) {
            var postureMatchCount;
            var primaryAngles;
            var depthValues;
            var asymValues;
            var torsoValues;
            var primaryAmp;
            var depthAmp;
            var meanAsym;
            var peakAsym;
            var torsoMotion;
            var meanSquatTorso;
            var meanSquatHipAnkle;
            var meanSquatSide;
            var meanPushTilt;
            var meanPushHipAnkle;
            var meanPushSide;

            if (!repFrames || repFrames.length < cfg.minRepFrames || repFrames.length > cfg.maxRepFrames) {
                return false;
            }

            if (isDemoScoringEnabled()) {
                return true;
            }

            postureMatchCount = repFrames.filter(isExercisePostureMatch).length;
            if ((postureMatchCount / repFrames.length) < 0.8) {
                return false;
            }

            primaryAngles = repFrames.map(function (frame) { return frame.primary_angle; });
            depthValues = repFrames.map(function (frame) { return frame.depth_delta; });
            asymValues = repFrames.map(function (frame) { return frame.asymmetry || 0; });
            torsoValues = repFrames.map(function (frame) { return frame.torso_angle || 0; });
            primaryAmp = Math.max.apply(null, primaryAngles.map(function (value) {
                return primaryTravel(cfg, state.baselinePrimary, value);
            }));
            depthAmp = Math.max.apply(null, depthValues);
            meanAsym = asymValues.reduce(function (a, b) { return a + b; }, 0) / asymValues.length;
            peakAsym = Math.max.apply(null, asymValues);
            torsoMotion = Math.max.apply(null, torsoValues) - Math.min.apply(null, torsoValues);

            if (state.motionFamily === 'squat_like' || state.motionFamily === 'lunge_like') {
                meanSquatTorso = meanNumber(repFrames.map(function (frame) { return frame.torso_angle; }), 90);
                meanSquatHipAnkle = meanNumber(repFrames.map(function (frame) { return frame.hip_ankle_vertical_norm; }), 0);
                meanSquatSide = meanNumber(repFrames.map(function (frame) { return frame.side_view_score; }), 0);

                if (meanSquatTorso > 70 || meanSquatHipAnkle < 0.20 || meanSquatSide < 0.20) {
                    return false;
                }
                if (meanAsym > cfg.maxMeanAsymmetry && depthAmp < cfg.minDepthAmplitude * 0.9) {
                    return false;
                }
                if (peakAsym > cfg.maxPeakAsymmetry && depthAmp < cfg.minDepthAmplitude * 1.05) {
                    return false;
                }
                if (torsoMotion < cfg.minTorsoMotion * 0.75 && depthAmp < cfg.minDepthAmplitude * 0.9) {
                    return false;
                }

                return (
                    (primaryAmp >= cfg.minPrimaryAmplitude && depthAmp >= cfg.minDepthAmplitude)
                    || (primaryAmp >= cfg.minPrimaryAmplitude * 0.78 && depthAmp >= cfg.minDepthAmplitude * 0.48)
                    || (depthAmp >= cfg.minDepthAmplitude * 0.78 && primaryAmp >= cfg.minPrimaryAmplitude * 0.55)
                    || (primaryAmp >= cfg.minPrimaryAmplitude * 0.40 && depthAmp >= cfg.minDepthAmplitude * 0.35)
                );
            }

            if (state.motionFamily === 'push_like') {
            meanPushTilt = meanNumber(repFrames.map(function (frame) { return frame.posture_tilt_deg; }), 90);
            meanPushHipAnkle = meanNumber(repFrames.map(function (frame) { return frame.hip_ankle_vertical_norm; }), 1);
            meanPushSide = meanNumber(repFrames.map(function (frame) { return frame.side_view_score; }), 0);

            if (meanPushTilt > 34 || meanPushHipAnkle > 0.45 || meanPushSide < 0.35) {
                return false;
            }
            if (torsoMotion < cfg.minTorsoMotion && depthAmp < cfg.minDepthAmplitude * 0.75) {
                return false;
            }

            return (
                (primaryAmp >= cfg.minPrimaryAmplitude && depthAmp >= cfg.minDepthAmplitude)
                || (primaryAmp >= cfg.minPrimaryAmplitude * 0.9 && depthAmp >= cfg.minDepthAmplitude * 0.55)
                || (depthAmp >= cfg.minDepthAmplitude && primaryAmp >= cfg.minPrimaryAmplitude * 0.65)
            );
            }

            return (
                primaryAmp >= cfg.minPrimaryAmplitude * 0.75
                || depthAmp >= cfg.minDepthAmplitude
                || (primaryAmp >= cfg.minPrimaryAmplitude * 0.55 && torsoMotion >= cfg.minTorsoMotion * 0.75)
            );
        }

        function repFeedback(responseData) {
            var hintCodes = responseData.details && Array.isArray(responseData.details.hint_codes)
                ? responseData.details.hint_codes
                : [];
            var quality = String(responseData.quality || 'Нужно улучшить');
            var tone = responseData.hint_tone
                ? String(responseData.hint_tone)
                : (quality === 'Отлично' ? 'low' : (quality === 'Нормально' ? 'med' : 'high'));
            var customMessage = responseData.hint_message ? String(responseData.hint_message) : '';
            var message = 'Повтор засчитан.';
            var firstError = responseData.errors && responseData.errors[0] ? String(responseData.errors[0]) : '';
            var firstTip = responseData.tips && responseData.tips[0] ? String(responseData.tips[0]) : '';

            if (customMessage) {
                message = customMessage;
            } else if (hintCodes.indexOf('good_rep') >= 0 || Number(responseData.rep_score) >= 85) {
                message = 'Ты молодец, так держать.';
            } else if (hintCodes.indexOf('heel_lift') >= 0) {
                message = 'Не отрывайте пятки от пола.';
            } else if (hintCodes.indexOf('undersquat') >= 0) {
                message = 'Добавьте глубину приседа.';
            } else if (hintCodes.indexOf('torso_forward') >= 0) {
                message = 'Грудь выше, темп вниз медленнее.';
            } else if (hintCodes.indexOf('asymmetry') >= 0) {
                message = 'Выравняйте стороны: одинаковая глубина и скорость.';
            } else if (hintCodes.indexOf('body_line_break') >= 0) {
                message = 'Держите корпус прямой линией.';
            } else if (hintCodes.indexOf('partial_range') >= 0) {
                message = 'Опуститесь ниже.';
            } else if (hintCodes.indexOf('leg_line_break') >= 0) {
                message = 'Не сгибайте ноги.';
            } else if (hintCodes.indexOf('excessive_depth_drop') >= 0) {
                message = 'Не проваливайтесь в нижней точке.';
            } else if (firstError) {
                message = firstError;
            } else if (firstTip) {
                message = firstTip;
            }

            return {
                message: message,
                tone: tone
            };
        }

        function isDemoScoringEnabled() {
            var hasDemoQuery = false;

            if (typeof window !== 'undefined' && window.location) {
                hasDemoQuery = /(?:^|[?&])tech_demo=1(?:&|$)/.test(String(window.location.search || ''));
            }

            return (
                hasDemoQuery
                && state.exerciseSlug === 'pushup'
                && !!site
                && typeof site.safeGetStorage === 'function'
                && site.safeGetStorage(PUSHUP_DEMO_STORAGE_KEY) === '1'
            );
        }

        function updatePushupDemoMachine(current, cfg) {
            var primaryDrop;
            var downCondition;
            var bottomReached;
            var recoverCondition;
            var upCondition;
            var repCopy;

            if (state.currentState === 'WAIT_READY') {
                state.calibrationFrames.push(current);
                state.latestHint = 'Калибровка... зафиксируйте верхнюю точку.';
                state.liveHintTone = 'low';
                if (state.calibrationFrames.length >= 8) {
                    state.baselinePrimary = state.calibrationFrames.map(function (item) {
                        return item.primary_angle;
                    }).reduce(function (a, b) { return a + b; }, 0) / state.calibrationFrames.length;
                    state.baselineDepth = state.calibrationFrames.map(function (item) {
                        return item.depth_norm;
                    }).reduce(function (a, b) { return a + b; }, 0) / state.calibrationFrames.length;
                    state.baselinePrimaryInitial = state.baselinePrimary;
                    state.baselineDepthInitial = state.baselineDepth;
                    state.currentState = 'TOP';
                    state.preRoll = [];
                    state.repFrames = [];
                    state.downCounter = 0;
                    state.riseCounter = 0;
                    state.upCounter = 0;
                    state.topReadyFrames = 0;
                    state.latestHint = 'Готово. Выполните отжимание.';
                }
                return;
            }

            if (state.baselinePrimary === null || state.baselineDepth === null) {
                return;
            }

            current.depth_delta = Math.max(0, state.baselineDepth - current.depth_norm);
            state.preRoll.push(current);
            if (state.preRoll.length > cfg.preRollFrames) {
                state.preRoll.shift();
            }

            if (state.cooldown > 0) {
                state.cooldown -= 1;
            }

            primaryDrop = state.baselinePrimary - current.primary_angle;

            if (state.currentState === 'TOP') {
                downCondition = (
                    (primaryDrop >= cfg.downEnterPrimaryDrop || current.depth_delta >= cfg.downEnterDepthDelta)
                    && state.cooldown === 0
                );
                state.downCounter = downCondition ? Math.min(state.downCounter + 1, 6) : Math.max(0, state.downCounter - 1);
                applyRealtimeHint(current, 'TOP', cfg);

                if (state.downCounter >= 1) {
                    state.currentState = 'DOWN';
                    state.repHintPinned = false;
                    state.repFrames = state.preRoll.slice();
                    state.minPrimary = current.primary_angle;
                    state.maxDepth = current.depth_delta;
                    state.riseCounter = 0;
                    state.upCounter = 0;
                }
                return;
            }

            if (state.currentState === 'DOWN') {
                state.repFrames.push(current);
                state.minPrimary = Math.min(state.minPrimary, current.primary_angle);
                state.maxDepth = Math.max(state.maxDepth, current.depth_delta);
                bottomReached = (
                    (state.baselinePrimary - state.minPrimary) >= cfg.minPrimaryAmplitude
                    || state.maxDepth >= cfg.minDepthAmplitude
                );
                recoverCondition = bottomReached && (
                    current.primary_angle >= state.minPrimary + cfg.risingRecoverPrimary
                    || current.depth_delta <= Math.max(0, state.maxDepth - cfg.risingRecoverDepth)
                );
                state.riseCounter = recoverCondition ? Math.min(state.riseCounter + 1, 6) : Math.max(0, state.riseCounter - 1);
                applyRealtimeHint(current, 'DOWN', cfg);

                if (state.riseCounter >= 1) {
                    state.currentState = 'RISING';
                    state.upCounter = 0;
                }
                if (state.repFrames.length > cfg.maxRepFrames) {
                    state.currentState = 'TOP';
                    state.repFrames = [];
                    state.cooldown = cfg.cooldownFrames;
                }
                return;
            }

            if (state.currentState === 'RISING') {
                state.repFrames.push(current);
                state.minPrimary = Math.min(state.minPrimary, current.primary_angle);
                state.maxDepth = Math.max(state.maxDepth, current.depth_delta);
                upCondition = (
                    current.primary_angle >= state.baselinePrimary - cfg.upPrimaryTolerance
                    || current.depth_delta <= cfg.upDepthTolerance
                );
                state.upCounter = upCondition ? Math.min(state.upCounter + 1, 6) : Math.max(0, state.upCounter - 1);
                applyRealtimeHint(current, 'RISING', cfg);

                if (state.upCounter >= 1 && state.repFrames.length >= cfg.minRepFrames) {
                    repCopy = state.repFrames.slice();
                    state.currentState = 'TOP';
                    state.cooldown = cfg.cooldownFrames;
                    state.downCounter = 0;
                    state.riseCounter = 0;
                    state.upCounter = 0;
                    state.preRoll = [current];
                    state.repFrames = [];
                    state.minPrimary = 999;
                    state.maxDepth = 0;
                    finalizeRep(repCopy);
                }
            }
        }

        function getDemoRepPreset(repNumber) {
            var presets = DEMO_REP_SCENARIOS[state.exerciseSlug] || [];
            var presetIndex;

            if (!presets.length) {
                return null;
            }

            presetIndex = clamp(repNumber - 1, 0, presets.length - 1);
            return presets[presetIndex];
        }

        function buildDemoRepResponse(repFrames) {
            var repNumber = state.repIndex + 1;
            var preset = getDemoRepPreset(repNumber);
            var repScore;
            var ruleFlags;

            if (!preset) {
                return null;
            }

            repScore = Number(preset.repScore);
            ruleFlags = Object.assign({}, preset.ruleFlags || {});

            return {
                rep_index: repNumber,
                rep_score: repScore,
                quality: qualityLabelForScore(repScore),
                errors: (preset.errors || []).slice(),
                tips: (preset.tips || []).slice(),
                metrics: Object.assign({}, preset.metrics || {}),
                details: {
                    demo_preset: true,
                    hint_codes: (preset.hintCodes || []).slice(),
                    rule_flags: ruleFlags,
                    score_breakdown: {
                        base_score: 100,
                        penalty_total: Math.max(0, 100 - repScore),
                        penalty_parts: Object.assign({}, preset.penaltyParts || {}),
                        boost_applied: repScore >= 95 ? 'demo_clean_rep' : 'none',
                        boost_value: 0,
                        hard_caps: {
                            heel_fail_to_1: !!ruleFlags.heel_fail,
                            poor_depth_cap_65: !!ruleFlags.poor_depth,
                            undersquat_cap_40: !!ruleFlags.undersquat,
                            undersquat_severe_cap_30: !!ruleFlags.undersquat_severe
                        },
                        rule_flags: ruleFlags,
                        final_score: repScore
                    }
                },
                hint_message: String(preset.hintMessage || ''),
                hint_tone: String(preset.hintTone || 'low'),
                frame_metrics: repFrames
            };
        }

        function scoreRepViaApi(repFrames) {
            return site.sendJson(
                currentCompareEndpoint(),
                'POST',
                {
                    rep_index: state.repIndex + 1,
                    frame_metrics: repFrames
                },
                'Не удалось сравнить повтор с эталоном.'
            );
        }

        function scoreRep(repFrames) {
            var demoResponse;

            if (isDemoScoringEnabled()) {
                demoResponse = buildDemoRepResponse(repFrames);
                if (demoResponse) {
                    return Promise.resolve(demoResponse);
                }
            }

            // Original API-based scoring is kept intact for the normal runtime flow.
            return scoreRepViaApi(repFrames);
        }

        function finalizeRep(repFrames) {
            if (!repFrames.length || state.scoringRep) {
                return;
            }

            state.scoringRep = true;
            scoreRep(repFrames)
                .then(function (responseData) {
                    var feedback;
                    var hintCodes;
                    var voiceFeedback;
                    var voiceCode;
                    var spokenMessage;
                    var shouldSpeakRepFeedback;

                    state.repIndex += 1;
                    state.reps.push({
                        repIndex: responseData.rep_index,
                        repScore: responseData.rep_score,
                        quality: responseData.quality,
                        errors: responseData.errors || [],
                        tips: responseData.tips || [],
                        metrics: responseData.metrics || {},
                        details: responseData.details || {},
                        frameMetrics: repFrames
                    });
                    state.latestRepScore = Number(responseData.rep_score);
                    state.avgScore = averageScore(state.reps);
                    state.latestQuality = String(responseData.quality || 'Нужно улучшить');
                    feedback = repFeedback(responseData);
                    hintCodes = responseData.details && Array.isArray(responseData.details.hint_codes)
                        ? responseData.details.hint_codes
                        : [];
                    voiceFeedback = responseData.details && responseData.details.voice_feedback
                        ? responseData.details.voice_feedback
                        : null;
                    voiceCode = voiceFeedback && voiceFeedback.code
                        ? String(voiceFeedback.code)
                        : '';
                    spokenMessage = voiceFeedback && voiceFeedback.message
                        && (
                            voiceCode === 'good_rep'
                            || voiceCode === 'error'
                            || hintCodes.indexOf(voiceCode) >= 0
                        )
                        ? String(voiceFeedback.message)
                        : feedback.message;
                    shouldSpeakRepFeedback = !!(
                        (responseData.errors && responseData.errors.length)
                        || voiceCode === 'good_rep'
                        || Number(responseData.rep_score) >= 85
                    );
                    state.latestHint = feedback.message;
                    state.liveHintTone = feedback.tone;
                    state.repHintPinned = true;
                    if (shouldSpeakRepFeedback) {
                        speakTechniqueCue(
                            state,
                            spokenMessage,
                            {
                                priority: voiceFeedback && voiceFeedback.priority
                                    ? String(voiceFeedback.priority)
                                    : String(feedback.tone || 'med'),
                                code: voiceCode || (hintCodes.length ? String(hintCodes[0]) : ''),
                                minGapMs: 900,
                                dedupeMs: 2600,
                                interrupt: true
                            }
                        );
                    }
                    renderTechniqueUi();
                })
                .catch(function (error) {
                    state.latestQuality = 'Нужно улучшить';
                    state.latestHint = error.message || 'Ошибка сравнения повтора.';
                    state.liveHintTone = 'high';
                    state.repHintPinned = true;
                    renderTechniqueUi();
                })
                .finally(function () {
                    state.scoringRep = false;
                });
        }

        function updateRepMachine(metrics) {
            var cfg = getConfig();
            var current = {
                primary_angle: smoothMetric(state.smoothPrimary, metrics.primary_angle, 5),
                secondary_angle: smoothMetric(state.smoothSecondary, metrics.secondary_angle, 5),
                depth_norm: smoothMetric(state.smoothDepth, metrics.depth_norm, 5),
                torso_angle: metrics.torso_angle,
                asymmetry: metrics.asymmetry,
                hip_asymmetry: metrics.hip_asymmetry,
                side_view_score: metrics.side_view_score,
                heel_lift_norm: smoothMetric(state.smoothHeel, metrics.heel_lift_norm, 5),
                leg_angle: metrics.leg_angle,
                posture_tilt_deg: metrics.posture_tilt_deg,
                hip_ankle_vertical_norm: metrics.hip_ankle_vertical_norm,
                timestamp_ms: Date.now(),
                depth_delta: 0
            };
            var postureMatch = isExercisePostureMatch(current);
            var primaryDrop;
            var armCondition;
            var deepCondition;
            var stableTop;
            var reachedWorkingDepth;
            var recoverCondition;
            var upCondition;
            var repCopy;
            var repValid;

            if (isPushupDemoMode()) {
                updatePushupDemoMachine(current, cfg);
                return;
            }

            if (!postureMatch) {
                state.postureMismatchFrames += 1;
                if (state.postureMismatchFrames >= 8) {
                    state.currentState = 'WAIT_READY';
                    state.calibrationFrames = [];
                    state.baselinePrimary = null;
                    state.baselineDepth = null;
                    state.baselineHeel = null;
                    state.baselinePrimaryInitial = null;
                    state.baselineDepthInitial = null;
                    state.preRoll = [];
                    state.repFrames = [];
                    state.downCounter = 0;
                    state.riseCounter = 0;
                    state.upCounter = 0;
                    state.smoothPrimary = [];
                    state.smoothDepth = [];
                    state.smoothSecondary = [];
                    state.smoothHeel = [];
                    state.cooldown = cfg.cooldownFrames;
                    state.descentArmed = false;
                    state.descentTrendCounter = 0;
                    state.topReadyFrames = 0;
                }
                state.latestQuality = 'Нужно улучшить';
                state.latestHint = state.motionFamily === 'push_like'
                    ? 'Примите упор лёжа боком к камере и выпрямите корпус.'
                    : (state.motionFamily === 'core_like'
                        ? 'Лягте боком к камере и держите корпус с ногами в кадре.'
                        : 'Встаньте боком к камере и держите ноги с корпусом в кадре.');
                state.liveHintTone = 'high';
                return;
            }
            state.postureMismatchFrames = 0;

            if (state.currentState === 'WAIT_READY') {
                state.calibrationFrames.push(current);
                state.latestHint = 'Калибровка стартовой позиции...';
                state.liveHintTone = 'low';
                if (state.calibrationFrames.length >= 12) {
                    state.baselinePrimary = state.calibrationFrames.map(function (item) {
                        return item.primary_angle;
                    }).reduce(function (a, b) { return a + b; }, 0) / state.calibrationFrames.length;
                    state.baselineDepth = state.calibrationFrames.map(function (item) {
                        return item.depth_norm;
                    }).reduce(function (a, b) { return a + b; }, 0) / state.calibrationFrames.length;
                    state.baselineHeel = calibrationFloor(state.calibrationFrames.map(function (item) {
                        return item.heel_lift_norm;
                    }), 0);
                    state.baselinePrimaryInitial = state.baselinePrimary;
                    state.baselineDepthInitial = state.baselineDepth;
                    state.currentState = 'TOP';
                    state.preRoll = [];
                    state.latestHint = 'Готово. Выполните полный повтор.';
                    state.liveHintTone = 'low';
                    state.topReadyFrames = 0;
                    state.descentArmed = false;
                    state.descentTrendCounter = 0;
                }
                return;
            }

            if (state.baselinePrimary === null || state.baselineDepth === null) {
                return;
            }

            current.depth_delta = Math.max(0, state.baselineDepth - current.depth_norm);
            state.preRoll.push(current);
            if (state.preRoll.length > cfg.preRollFrames) {
                state.preRoll.shift();
            }

            if (state.cooldown > 0) {
                state.cooldown -= 1;
            }

            if (state.currentState === 'TOP') {
                primaryDrop = primaryTravel(cfg, state.baselinePrimary, current.primary_angle);
                armCondition = primaryDrop >= cfg.downEnterPrimaryDrop * 0.28 && current.depth_delta >= cfg.downEnterDepthDelta * 0.16;
                state.descentTrendCounter = armCondition
                    ? Math.min(state.descentTrendCounter + 1, 8)
                    : Math.max(state.descentTrendCounter - 1, 0);
                if (state.descentTrendCounter >= 2) {
                    state.descentArmed = true;
                }
                deepCondition = (
                    state.descentArmed
                    && (primaryDrop >= cfg.downEnterPrimaryDrop || current.depth_delta >= cfg.downEnterDepthDelta)
                    && primaryDrop >= cfg.downEnterPrimaryDrop * 0.52
                    && current.depth_delta >= cfg.downEnterDepthDelta * 0.40
                    && state.cooldown === 0
                    && state.topReadyFrames >= 1
                );
                state.downCounter = deepCondition
                    ? Math.min(state.downCounter + 1, 8)
                    : Math.max(0, state.downCounter - 1);

                if (!state.repHintPinned) {
                    applyRealtimeHint(current, 'TOP', cfg);
                    requestLiveHint(current, 'TOP');
                }

                stableTop = primaryDrop <= cfg.downEnterPrimaryDrop * 0.35 && current.depth_delta <= cfg.downEnterDepthDelta * 0.42;
                if (stableTop) {
                    state.topReadyFrames = Math.min(state.topReadyFrames + 1, 20);
                    if (primaryDrop <= cfg.downEnterPrimaryDrop * 0.12 && current.depth_delta <= cfg.downEnterDepthDelta * 0.2) {
                        state.descentArmed = false;
                    }
                } else {
                    state.topReadyFrames = Math.max(0, state.topReadyFrames - 1);
                }

                if (state.downCounter >= cfg.minStateFrames) {
                    state.currentState = 'DOWN';
                    state.repHintPinned = false;
                    state.repFrames = state.preRoll.slice();
                    state.minPrimary = current.primary_angle;
                    state.maxDepth = current.depth_delta;
                    state.maxTorso = current.torso_angle || 0;
                    state.riseCounter = 0;
                    state.upCounter = 0;
                    state.descentArmed = false;
                    state.descentTrendCounter = 0;
                    applyRealtimeHint(current, 'DOWN', cfg);
                    requestLiveHint(current, 'DOWN');
                }
                return;
            }

            if (state.currentState === 'DOWN') {
                state.repFrames.push(current);
                state.minPrimary = updatePrimaryExtremum(cfg, state.minPrimary, current.primary_angle, false);
                state.maxDepth = Math.max(state.maxDepth, current.depth_delta);
                state.maxTorso = Math.max(state.maxTorso, current.torso_angle || 0);
                reachedWorkingDepth = (
                    primaryTravel(cfg, state.baselinePrimary, state.minPrimary) >= cfg.minPrimaryAmplitude * 0.35
                    || state.maxDepth >= cfg.minDepthAmplitude * 0.40
                );
                recoverCondition = (
                    (recoverFromExtremum(cfg, current.primary_angle, state.minPrimary, cfg.risingRecoverPrimary)
                        || current.depth_delta <= Math.max(0, state.maxDepth - cfg.risingRecoverDepth))
                    && recoverFromExtremum(cfg, current.primary_angle, state.minPrimary, cfg.risingRecoverPrimary * 0.28)
                    && current.depth_delta <= Math.max(0, state.maxDepth - cfg.risingRecoverDepth * 0.28)
                    && reachedWorkingDepth
                );
                state.riseCounter = recoverCondition
                    ? Math.min(state.riseCounter + 1, 8)
                    : Math.max(0, state.riseCounter - 1);
                applyRealtimeHint(current, 'DOWN', cfg);
                requestLiveHint(current, 'DOWN');

                if (state.riseCounter >= cfg.minStateFrames) {
                    state.currentState = 'RISING';
                    state.upCounter = 0;
                }
                if (state.repFrames.length > cfg.maxRepFrames) {
                    state.currentState = 'TOP';
                    state.repFrames = [];
                    state.cooldown = cfg.cooldownFrames;
                }
                return;
            }

            if (state.currentState === 'RISING') {
                state.repFrames.push(current);
                state.minPrimary = updatePrimaryExtremum(cfg, state.minPrimary, current.primary_angle, false);
                state.maxDepth = Math.max(state.maxDepth, current.depth_delta);
                state.maxTorso = Math.max(state.maxTorso, current.torso_angle || 0);

                if (state.exerciseSlug === 'pushup') {
                    upCondition = (
                        (withinTopTolerance(cfg, current.primary_angle, state.baselinePrimary, cfg.upPrimaryTolerance)
                            && primaryTravel(cfg, state.baselinePrimary, state.minPrimary) >= cfg.minPrimaryAmplitude * 0.68)
                        || (withinTopTolerance(cfg, current.primary_angle, state.baselinePrimary, cfg.upPrimaryTolerance * 1.3)
                            && current.depth_delta <= cfg.upDepthTolerance)
                    );
                } else {
                    upCondition = (
                        withinTopTolerance(cfg, current.primary_angle, state.baselinePrimary, cfg.upPrimaryTolerance)
                        && current.depth_delta <= cfg.upDepthTolerance
                    );
                }

                state.upCounter = upCondition ? state.upCounter + 1 : 0;
                if (!upCondition) {
                    state.upCounter = Math.max(0, state.upCounter - 1);
                }
                applyRealtimeHint(current, 'RISING', cfg);
                requestLiveHint(current, 'RISING');

                if (state.upCounter >= cfg.minStateFrames) {
                    repCopy = state.repFrames.slice();
                    repValid = validateRep(repCopy, cfg);
                    state.currentState = 'TOP';
                    state.cooldown = cfg.cooldownFrames;
                    state.downCounter = 0;
                    state.riseCounter = 0;
                    state.upCounter = 0;
                    state.topReadyFrames = 0;
                    state.preRoll = [current];
                    state.repFrames = [];
                    state.minPrimary = cfg.primaryDirection === 'rise' ? -999 : 999;
                    state.maxDepth = 0;
                    state.maxTorso = 0;
                    state.descentArmed = false;
                    state.descentTrendCounter = 0;

                    if (repValid) {
                        finalizeRep(repCopy);
                    }
                }
            }
        }

        var OVERLAY_LANDMARK_IDS = [
            LANDMARK.L_SHOULDER,
            LANDMARK.R_SHOULDER,
            LANDMARK.L_ELBOW,
            LANDMARK.R_ELBOW,
            LANDMARK.L_WRIST,
            LANDMARK.R_WRIST,
            LANDMARK.L_HIP,
            LANDMARK.R_HIP,
            LANDMARK.L_KNEE,
            LANDMARK.R_KNEE,
            LANDMARK.L_ANKLE,
            LANDMARK.R_ANKLE,
            LANDMARK.L_HEEL,
            LANDMARK.R_HEEL,
            LANDMARK.L_FOOT_INDEX,
            LANDMARK.R_FOOT_INDEX
        ];
        var OVERLAY_CONNECTIONS = [
            [LANDMARK.L_SHOULDER, LANDMARK.R_SHOULDER],
            [LANDMARK.L_SHOULDER, LANDMARK.L_ELBOW],
            [LANDMARK.L_ELBOW, LANDMARK.L_WRIST],
            [LANDMARK.R_SHOULDER, LANDMARK.R_ELBOW],
            [LANDMARK.R_ELBOW, LANDMARK.R_WRIST],
            [LANDMARK.L_SHOULDER, LANDMARK.L_HIP],
            [LANDMARK.R_SHOULDER, LANDMARK.R_HIP],
            [LANDMARK.L_HIP, LANDMARK.R_HIP],
            [LANDMARK.L_HIP, LANDMARK.L_KNEE],
            [LANDMARK.L_KNEE, LANDMARK.L_ANKLE],
            [LANDMARK.R_HIP, LANDMARK.R_KNEE],
            [LANDMARK.R_KNEE, LANDMARK.R_ANKLE],
            [LANDMARK.L_ANKLE, LANDMARK.L_HEEL],
            [LANDMARK.L_HEEL, LANDMARK.L_FOOT_INDEX],
            [LANDMARK.R_ANKLE, LANDMARK.R_HEEL],
            [LANDMARK.R_HEEL, LANDMARK.R_FOOT_INDEX]
        ];
        var OVERLAY_MAJOR_JOINTS = [
            LANDMARK.L_SHOULDER,
            LANDMARK.R_SHOULDER,
            LANDMARK.L_HIP,
            LANDMARK.R_HIP
        ].reduce(function (lookup, id) {
            lookup[id] = true;
            return lookup;
        }, {});
        var OVERLAY_MID_JOINTS = [
            LANDMARK.L_ELBOW,
            LANDMARK.R_ELBOW,
            LANDMARK.L_KNEE,
            LANDMARK.R_KNEE
        ].reduce(function (lookup, id) {
            lookup[id] = true;
            return lookup;
        }, {});
        var OVERLAY_EDGE_JOINTS = [
            LANDMARK.L_WRIST,
            LANDMARK.R_WRIST,
            LANDMARK.L_ANKLE,
            LANDMARK.R_ANKLE
        ].reduce(function (lookup, id) {
            lookup[id] = true;
            return lookup;
        }, {});
        var OVERLAY_FOOT_JOINTS = [
            LANDMARK.L_HEEL,
            LANDMARK.R_HEEL,
            LANDMARK.L_FOOT_INDEX,
            LANDMARK.R_FOOT_INDEX
        ].reduce(function (lookup, id) {
            lookup[id] = true;
            return lookup;
        }, {});
        var OVERLAY_LANDMARK_LOOKUP = OVERLAY_LANDMARK_IDS.reduce(function (lookup, id) {
            lookup[id] = true;
            return lookup;
        }, {});

        function overlayScale(width, height) {
            return Math.max(1, Math.min(width, height) / 420);
        }

        function overlayRadius(scale, landmarkId) {
            if (OVERLAY_MAJOR_JOINTS[landmarkId]) {
                return 8.6 * scale;
            }
            if (OVERLAY_MID_JOINTS[landmarkId]) {
                return 7.6 * scale;
            }
            if (OVERLAY_EDGE_JOINTS[landmarkId]) {
                return 7.8 * scale;
            }
            if (OVERLAY_FOOT_JOINTS[landmarkId]) {
                return 7.2 * scale;
            }
            return 7.1 * scale;
        }

        function visibleOverlayPoint(landmarks, landmarkId, width, height) {
            var landmark = landmarks[landmarkId];
            var visibility;

            if (!landmark) {
                return null;
            }

            visibility = typeof landmark.visibility === 'number' ? landmark.visibility : 1;
            if (visibility < 0.35) {
                return null;
            }

            return {
                x: landmark.x * width,
                y: landmark.y * height,
                visibility: visibility
            };
        }

        function jointOpacity(point) {
            return Math.max(0.5, Math.min(1, point.visibility || 1));
        }

        function drawOverlayConnection(ctx, startPoint, endPoint, scale) {
            var gradient = ctx.createLinearGradient(startPoint.x, startPoint.y, endPoint.x, endPoint.y);
            var alpha = Math.min(jointOpacity(startPoint), jointOpacity(endPoint));

            gradient.addColorStop(0, 'rgba(226, 255, 242, ' + (0.92 * alpha) + ')');
            gradient.addColorStop(0.5, 'rgba(52, 211, 153, ' + (0.94 * alpha) + ')');
            gradient.addColorStop(1, 'rgba(16, 185, 129, ' + (0.88 * alpha) + ')');

            ctx.save();
            ctx.lineCap = 'round';
            ctx.lineJoin = 'round';
            ctx.strokeStyle = 'rgba(4, 16, 18, ' + (0.5 * alpha) + ')';
            ctx.lineWidth = 8.5 * scale;
            ctx.beginPath();
            ctx.moveTo(startPoint.x, startPoint.y);
            ctx.lineTo(endPoint.x, endPoint.y);
            ctx.stroke();

            ctx.strokeStyle = gradient;
            ctx.shadowColor = 'rgba(52, 211, 153, ' + (0.26 * alpha) + ')';
            ctx.shadowBlur = 12 * scale;
            ctx.lineWidth = 5 * scale;
            ctx.beginPath();
            ctx.moveTo(startPoint.x, startPoint.y);
            ctx.lineTo(endPoint.x, endPoint.y);
            ctx.stroke();
            ctx.restore();
        }

        function landmarkGradient(ctx, point, radius, isMajor, isFoot) {
            var gradient = ctx.createRadialGradient(
                point.x - radius * 0.35,
                point.y - radius * 0.45,
                radius * 0.18,
                point.x,
                point.y,
                radius
            );
            var alpha = jointOpacity(point);

            if (isFoot) {
                gradient.addColorStop(0, 'rgba(255, 255, 255, ' + alpha + ')');
                gradient.addColorStop(0.5, 'rgba(214, 244, 255, ' + alpha + ')');
                gradient.addColorStop(1, 'rgba(121, 210, 255, ' + (0.96 * alpha) + ')');
                return gradient;
            }

            if (isMajor) {
                gradient.addColorStop(0, 'rgba(255, 255, 255, ' + alpha + ')');
                gradient.addColorStop(0.48, 'rgba(226, 248, 255, ' + alpha + ')');
                gradient.addColorStop(1, 'rgba(136, 219, 255, ' + (0.96 * alpha) + ')');
                return gradient;
            }

            gradient.addColorStop(0, 'rgba(255, 255, 255, ' + alpha + ')');
            gradient.addColorStop(0.56, 'rgba(232, 248, 255, ' + alpha + ')');
            gradient.addColorStop(1, 'rgba(160, 226, 255, ' + (0.94 * alpha) + ')');
            return gradient;
        }

        function drawOverlayLandmark(ctx, point, scale, landmarkId) {
            var radius = overlayRadius(scale, landmarkId);
            var isMajor = !!OVERLAY_MAJOR_JOINTS[landmarkId];
            var isFoot = !!OVERLAY_FOOT_JOINTS[landmarkId];
            var ringRadius = Math.max(3.6 * scale, radius - 1.35 * scale);
            var alpha = jointOpacity(point);

            ctx.save();
            ctx.fillStyle = 'rgba(8, 20, 32, ' + (0.76 * alpha) + ')';
            ctx.beginPath();
            ctx.arc(point.x, point.y, radius + 4.4 * scale, 0, Math.PI * 2);
            ctx.fill();

            ctx.fillStyle = landmarkGradient(ctx, point, radius, isMajor, isFoot);
            ctx.shadowColor = isFoot
                ? ('rgba(121, 210, 255, ' + (0.38 * alpha) + ')')
                : ('rgba(160, 226, 255, ' + (0.34 * alpha) + ')');
            ctx.shadowBlur = 16 * scale;
            ctx.beginPath();
            ctx.arc(point.x, point.y, radius, 0, Math.PI * 2);
            ctx.fill();

            ctx.strokeStyle = 'rgba(245, 252, 255, ' + (0.96 * alpha) + ')';
            ctx.lineWidth = 2 * scale;
            ctx.beginPath();
            ctx.arc(point.x, point.y, ringRadius, 0, Math.PI * 2);
            ctx.stroke();

            ctx.fillStyle = 'rgba(248, 253, 255, ' + (0.98 * alpha) + ')';
            ctx.beginPath();
            ctx.arc(point.x, point.y, Math.max(2.8 * scale, radius * (isMajor ? 0.38 : 0.33)), 0, Math.PI * 2);
            ctx.fill();
            ctx.restore();
        }

        function drawOverlaySkeleton(ctx, landmarks, width, height) {
            var scale = overlayScale(width, height);

            OVERLAY_CONNECTIONS.forEach(function (ids) {
                var startPoint;
                var endPoint;

                startPoint = visibleOverlayPoint(landmarks, ids[0], width, height);
                endPoint = visibleOverlayPoint(landmarks, ids[1], width, height);
                if (!startPoint || !endPoint) {
                    return;
                }

                drawOverlayConnection(ctx, startPoint, endPoint, scale);
            });

            OVERLAY_LANDMARK_IDS.forEach(function (landmarkId) {
                var point = visibleOverlayPoint(landmarks, landmarkId, width, height);
                if (!point) {
                    return;
                }
                drawOverlayLandmark(ctx, point, scale, landmarkId);
            });
        }

        function drawOverlay(results) {
            var canvas = byId('tech-overlay');
            var video = byId('tech-video');
            var width;
            var height;
            var ctx;

            if (!canvas || !video) {
                return;
            }

            width = video.videoWidth || video.clientWidth;
            height = video.videoHeight || video.clientHeight;
            if (!width || !height) {
                return;
            }

            if (canvas.width !== width) {
                canvas.width = width;
            }
            if (canvas.height !== height) {
                canvas.height = height;
            }

            ctx = canvas.getContext('2d');
            ctx.clearRect(0, 0, width, height);

            if (!results.poseLandmarks) {
                return;
            }

            drawOverlaySkeleton(ctx, results.poseLandmarks, width, height);
        }

        function onPoseResults(results) {
            var metrics;
            var techniqueUtils = window.KinematicsCustomTechnique;

            drawOverlay(results);

            if (!state.approachActive || !results.poseLandmarks) {
                return;
            }

            if (isPushupDemoMode()) {
                metrics = buildPushupDemoMetrics(results.poseLandmarks);
            } else if (techniqueUtils && typeof techniqueUtils.buildMetricFrame === 'function') {
                metrics = techniqueUtils.buildMetricFrame(
                    results.poseLandmarks,
                    state.motionFamily || 'squat_like',
                    state.viewType || 'side',
                    Date.now()
                );
            } else {
                metrics = state.exerciseSlug === 'squat'
                    ? buildSquatMetrics(results.poseLandmarks)
                    : buildPushupMetrics(results.poseLandmarks);
            }

            if (!metrics) {
                state.latestHint = 'Ключевые точки корпуса вне кадра. Вернитесь в позицию.';
                state.liveHintTone = 'high';
                renderTechniqueUi();
                return;
            }

            updateRepMachine(metrics);
            renderTechniqueUi();
        }

        function processCameraFrame() {
            var video = byId('tech-video');

            if (state.destroyed || !state.pose || !state.stream || !video) {
                return;
            }
            if (video.readyState < 2) {
                state.animationFrame = window.requestAnimationFrame(processCameraFrame);
                return;
            }
            if (state.poseBusy) {
                state.animationFrame = window.requestAnimationFrame(processCameraFrame);
                return;
            }

            state.poseBusy = true;
            state.pose.send({ image: video })
                .catch(function () {
                    return;
                })
                .finally(function () {
                    state.poseBusy = false;
                    if (!state.destroyed && state.stream) {
                        state.animationFrame = window.requestAnimationFrame(processCameraFrame);
                    }
                });
        }

        function stopCamera() {
            var video = byId('tech-video');

            cancelTechniqueVoice(state);
            if (state.animationFrame) {
                window.cancelAnimationFrame(state.animationFrame);
                state.animationFrame = null;
            }
            if (state.timerHandle) {
                window.clearInterval(state.timerHandle);
                state.timerHandle = null;
            }
            if (state.stream) {
                state.stream.getTracks().forEach(function (track) {
                    track.stop();
                });
                state.stream = null;
            }
            if (video) {
                video.srcObject = null;
            }
            state.cameraReady = false;
        }

        function loadPoseAssets() {
            if (state.assetsPromise) {
                return state.assetsPromise;
            }
            state.assetsPromise = Promise.all([
                site.loadScript('https://cdn.jsdelivr.net/npm/@mediapipe/drawing_utils/drawing_utils.js'),
                site.loadScript('https://cdn.jsdelivr.net/npm/@mediapipe/pose/pose.js')
            ]).then(function () {
                return true;
            });
            return state.assetsPromise;
        }

        function initPoseModel() {
            if (state.pose) {
                return;
            }
            if (typeof window.Pose !== 'function') {
                throw new Error('MediaPipe Pose не загрузился.');
            }

            state.pose = new window.Pose({
                locateFile: function (file) {
                    return 'https://cdn.jsdelivr.net/npm/@mediapipe/pose/' + file;
                }
            });
            state.pose.setOptions({
                modelComplexity: 1,
                smoothLandmarks: true,
                enableSegmentation: false,
                minDetectionConfidence: 0.5,
                minTrackingConfidence: 0.5
            });
            state.pose.onResults(onPoseResults);
        }

        function startCamera() {
            if (state.stream) {
                state.cameraReady = true;
                state.cameraTone = 'live';
                state.cameraMessage = 'Камера включена';
                renderTechniqueUi();
                return Promise.resolve();
            }

            return navigator.mediaDevices.getUserMedia({
                video: {
                    facingMode: 'user',
                    width: { ideal: 960 },
                    height: { ideal: 540 }
                },
                audio: false
            })
                .then(function (stream) {
                    var video = byId('tech-video');

                    if (!video) {
                        throw new Error('Не найден элемент video.');
                    }

                    state.stream = stream;
                    video.srcObject = stream;
                    return video.play().catch(function () {
                        return Promise.resolve();
                    });
                })
                .then(function () {
                    state.cameraReady = true;
                    state.cameraTone = 'live';
                    state.cameraMessage = 'Камера включена';
                    processCameraFrame();
                    renderTechniqueUi();
                });
        }

        function ensurePreview() {
            state.loadingCamera = true;
            state.cameraTone = 'loading';
            state.cameraMessage = 'Подключаю камеру...';
            renderTechniqueUi();

            return loadPoseAssets()
                .then(function () {
                    initPoseModel();
                    return startCamera();
                })
                .catch(function (error) {
                    state.cameraReady = false;
                    state.cameraTone = 'error';
                    state.cameraMessage = error.message || 'Камера недоступна';
                    state.latestHint = state.cameraMessage;
                    state.liveHintTone = 'high';
                    renderTechniqueUi();
                    throw error;
                })
                .finally(function () {
                    state.loadingCamera = false;
                    renderTechniqueUi();
                });
        }

        function startApproach() {
            if (state.voiceSupported && window.speechSynthesis && typeof window.speechSynthesis.getVoices === 'function') {
                try {
                    window.speechSynthesis.getVoices();
                } catch (error) {
                    // Speech warm-up is optional.
                }
            }
            ensurePreview()
                .then(function () {
                    resetTechniqueState(true);
                    state.approachActive = true;
                    state.currentState = 'WAIT_READY';
                    state.startTs = Date.now();
                    state.latestHint = 'Калибровка... Встаньте в стартовую позицию.';
                    state.liveHintTone = 'low';
                    state.timerHandle = window.setInterval(function () {
                        if (!state.approachActive || !state.startTs) {
                            return;
                        }
                        state.elapsedSec = Math.floor((Date.now() - state.startTs) / 1000);
                        renderTechniqueUi();
                    }, 500);
                    renderTechniqueUi();
                })
                .catch(function () {
                    return;
                });
        }

        function buildAggregates() {
            var total;
            var avg;
            var worstRep;
            var summaryTips;

            if (!state.reps.length) {
                return null;
            }

            total = state.reps.reduce(function (sum, rep) {
                return sum + rep.repScore;
            }, 0);
            avg = total / state.reps.length;
            worstRep = state.reps.reduce(function (currentWorst, rep) {
                if (!currentWorst || rep.repScore < currentWorst.repScore) {
                    return rep;
                }
                return currentWorst;
            }, null);
            summaryTips = state.reps.reduce(function (acc, rep) {
                (rep.tips || []).forEach(function (tip) {
                    if (acc.indexOf(tip) < 0) {
                        acc.push(tip);
                    }
                });
                return acc;
            }, []).slice(0, 3);

            return {
                avgScore: Number(avg.toFixed(2)),
                worstMetrics: worstRep ? worstRep.metrics : {},
                summaryTips: summaryTips
            };
        }

        function finishSession() {
            var payload;
            var redirectUrl = '/app/catalog';
            var submitPayload;
            var handleSuccess;
            var handleError;

            if (state.isFinishing) {
                return;
            }

            state.isFinishing = true;
            state.approachActive = false;
            if (state.timerHandle) {
                window.clearInterval(state.timerHandle);
                state.timerHandle = null;
            }
            state.latestHint = state.reps.length
                ? 'Сохраняю результаты сессии...'
                : 'Закрываю сессию.';
            state.liveHintTone = 'low';
            renderTechniqueUi();

            payload = {
                exercise: state.exerciseSlug,
                reps: state.reps.map(function (rep) {
                    return {
                        repIndex: rep.repIndex,
                        repScore: rep.repScore,
                        metrics: rep.metrics,
                        errors: rep.errors,
                        tips: rep.tips,
                        details: rep.details || {},
                        frameMetrics: rep.frameMetrics || []
                    };
                }),
                aggregates: buildAggregates()
            };

            submitPayload = function () {
                return site.sendJson(
                    '/api/technique/sessions/' + state.sessionId + '/finish',
                    'POST',
                    payload,
                    'Не удалось завершить technique-сессию.'
                );
            };

            handleSuccess = function (response) {
                redirectUrl = String(response.redirect_url || redirectUrl);
                state.redirectUrl = redirectUrl;
                if (response.ui) {
                    state.finishedUi = response.ui;
                }
                state.latestHint = state.reps.length
                    ? 'Подход завершен.'
                    : 'Сессия остановлена.';
                state.liveHintTone = 'low';
                state.sessionFinished = true;
                state.isFinishing = false;
                renderTechniqueUi();
                stopCamera();
            };

            handleError = function (error) {
                state.isFinishing = false;
                state.latestHint = error.message || 'Не удалось завершить technique-сессию.';
                state.liveHintTone = 'high';
                renderTechniqueUi();
            };

            submitPayload()
                .then(handleSuccess)
                .catch(function (error) {
                    if (error && String(error.message || '').indexOf('не совпадает с текущей technique-сессией') >= 0) {
                        return site.requireJson(
                            '/api/technique/sessions/' + state.sessionId,
                            null,
                            'Не удалось обновить technique-сессию.'
                        )
                            .then(function (session) {
                                var exercise = site.ensureObject(session.exercise);
                                var titleNode = byId('tech-exercise-name');

                                state.exerciseSlug = site.ensureString(exercise.slug, state.exerciseSlug);
                                state.exerciseTitle = site.ensureString(exercise.title, state.exerciseTitle);
                                state.motionFamily = site.ensureString(exercise.motion_family, state.motionFamily);
                                state.viewType = site.ensureString(exercise.view_type, state.viewType);
                                state.profileId = site.ensureFiniteNumber(exercise.profile_id);
                                state.referenceBased = exercise.reference_based === true;
                                payload.exercise = state.exerciseSlug;
                                if (titleNode) {
                                    titleNode.textContent = state.exerciseTitle;
                                }
                                return submitPayload();
                            })
                            .then(handleSuccess)
                            .catch(handleError);
                    }
                    handleError(error);
                });
        }

        function bindActions() {
            var startButton = byId('tech-start-btn');
            var stopButton = byId('tech-stop-btn');
            var backButton = byId('tech-back-link');
            var voiceButton = byId('tech-voice-btn');
            var guideButton = byId('tech-guide-ready-btn');

            if (guideButton) {
                guideButton.addEventListener('click', function () {
                    var guideSection = byId('tech-guide-section');
                    var stageShell = byId('tech-stage-shell');
                    var inlineStatus = byId('tech-inline-status');
                    var liveHint = byId('tech-live-hint');
                    var controls = byId('tech-controls-inline');

                    if (guideSection) {
                        guideSection.hidden = true;
                    }
                    [stageShell, inlineStatus, liveHint, controls].forEach(function (node) {
                        if (node) {
                            node.hidden = false;
                        }
                    });
                    ensurePreview().catch(function () {
                        return null;
                    });
                    renderTechniqueUi();
                });
            }

            if (startButton) {
                startButton.addEventListener('click', function () {
                    if (state.sessionFinished) {
                        return;
                    }
                    startApproach();
                });
            }
            if (stopButton) {
                stopButton.addEventListener('click', function () {
                    if (state.sessionFinished) {
                        window.location.assign(state.redirectUrl || '/app/catalog');
                        return;
                    }
                    finishSession();
                });
            }
            if (voiceButton) {
                voiceButton.addEventListener('click', function () {
                    state.voiceEnabled = !state.voiceEnabled;
                    persistVoiceSetting(state.voiceEnabled);
                    if (!state.voiceEnabled) {
                        cancelTechniqueVoice(state);
                    }
                    renderTechniqueUi();
                });
            }
            if (backButton) {
                backButton.addEventListener('click', function (event) {
                    event.preventDefault();
                    if (state.sessionFinished) {
                        window.location.assign(state.redirectUrl || '/app/catalog');
                        return;
                    }
                    finishSession();
                });
            }
        }

        function destroy() {
            if (state.destroyed) {
                return;
            }
            state.destroyed = true;
            state.approachActive = false;
            stopCamera();
        }

        bindActions();
        renderTechniqueUi();
        ensurePreview().catch(function () {
            return;
        });

        return {
            start: startApproach,
            stop: finishSession,
            destroy: destroy
        };
    }

    window.KinematicsTechniqueRuntime = {
        mount: function (options) {
            if (mountedController) {
                mountedController.destroy();
            }
            mountedController = createController(options || {});
            return mountedController;
        },
        destroy: function () {
            if (mountedController) {
                mountedController.destroy();
                mountedController = null;
            }
        }
    };

    window.addEventListener('pagehide', function () {
        if (mountedController) {
            mountedController.destroy();
        }
    });
})();
