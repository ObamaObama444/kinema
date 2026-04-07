(function () {
    var site = window.KinematicsSite;
    var poseAssetsPromise = null;

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

    function clamp(value, min, max) {
        return Math.max(min, Math.min(max, value));
    }

    function toNumber(value, fallback) {
        var number = Number(value);
        return Number.isFinite(number) ? number : fallback;
    }

    function distance2d(a, b) {
        var dx = a.x - b.x;
        var dy = a.y - b.y;
        return Math.sqrt(dx * dx + dy * dy);
    }

    function angleDeg(a, b, c) {
        var bax;
        var bay;
        var bcx;
        var bcy;
        var nba;
        var nbc;
        var cosine;

        if (!a || !b || !c) {
            return null;
        }

        bax = a.x - b.x;
        bay = a.y - b.y;
        bcx = c.x - b.x;
        bcy = c.y - b.y;
        nba = Math.sqrt(bax * bax + bay * bay);
        nbc = Math.sqrt(bcx * bcx + bcy * bcy);
        if (nba < 1e-6 || nbc < 1e-6) {
            return null;
        }

        cosine = (bax * bcx + bay * bcy) / (nba * nbc);
        cosine = clamp(cosine, -1, 1);
        return clamp(Math.acos(cosine) * (180 / Math.PI), 5, 180);
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
            visibility: typeof lm.visibility === 'number' ? lm.visibility : 0
        };
    }

    function meanVisibility(landmarks, ids) {
        return ids.reduce(function (sum, id) {
            var lm = landmarks[id];
            return sum + (lm && typeof lm.visibility === 'number' ? lm.visibility : 0);
        }, 0) / Math.max(ids.length, 1);
    }

    function torsoTiltDeg(hip, shoulder) {
        var tx;
        var ty;
        var n;
        var cosine;

        if (!hip || !shoulder) {
            return 0;
        }
        tx = shoulder.x - hip.x;
        ty = shoulder.y - hip.y;
        n = Math.sqrt(tx * tx + ty * ty);
        if (n < 1e-6) {
            return 0;
        }
        cosine = (ty * -1) / n;
        cosine = clamp(cosine, -1, 1);
        return Math.acos(cosine) * (180 / Math.PI);
    }

    function bodyOrientationComponents(landmarks, bodyLen) {
        var lHip = getPoint(landmarks, LANDMARK.L_HIP);
        var rHip = getPoint(landmarks, LANDMARK.R_HIP);
        var lSh = getPoint(landmarks, LANDMARK.L_SHOULDER);
        var rSh = getPoint(landmarks, LANDMARK.R_SHOULDER);
        var xComp;
        var zComp;

        if (!lHip || !rHip || !lSh || !rSh) {
            return { xNorm: 0, zNorm: 0 };
        }

        xComp = (Math.abs(lHip.x - rHip.x) + Math.abs(lSh.x - rSh.x)) / Math.max(bodyLen, 1e-6);
        zComp = 0.5 * (Math.abs(lHip.z - rHip.z) + Math.abs(lSh.z - rSh.z));
        return {
            xNorm: clamp(xComp, 0, 1),
            zNorm: clamp(zComp, 0, 1)
        };
    }

    function axisCloseness(value, target, spread) {
        return clamp(1 - Math.abs(value - target) / Math.max(spread, 1e-6), 0, 1);
    }

    function viewQualityScore(landmarks, bodyLen, viewType) {
        var orientation = bodyOrientationComponents(landmarks, bodyLen);
        var normalizedView = typeof viewType === 'string' ? viewType : 'side';

        if (normalizedView === 'front') {
            return clamp(
                0.62 * axisCloseness(orientation.xNorm, 0.14, 0.14)
                + 0.38 * axisCloseness(orientation.zNorm, 0.01, 0.12),
                0,
                1
            );
        }

        if (normalizedView === 'three_quarter') {
            return clamp(
                0.5 * axisCloseness(orientation.xNorm, 0.08, 0.1)
                + 0.5 * axisCloseness(orientation.zNorm, 0.08, 0.1),
                0,
                1
            );
        }

        return clamp(
            0.52 * (1 - clamp(orientation.xNorm / 0.14, 0, 1))
            + 0.48 * clamp(orientation.zNorm / 0.16, 0, 1),
            0,
            1
        );
    }

    function heelLiftNorm(heel, toe, bodyLen) {
        if (!heel || !toe) {
            return 0;
        }
        return Math.max(0, toe.y - heel.y) / Math.max(bodyLen, 1e-6);
    }

    function buildSquatLikeMetrics(landmarks, viewType) {
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
        var leftKnee = angleDeg(lHip, lKnee, lAnk);
        var rightKnee = angleDeg(rHip, rKnee, rAnk);
        var leftHip = angleDeg(lSh, lHip, lKnee);
        var rightHip = angleDeg(rSh, rHip, rKnee);
        var leftLeg = distance2d(lHip, lKnee) + distance2d(lKnee, lAnk);
        var rightLeg = distance2d(rHip, rKnee) + distance2d(rKnee, rAnk);
        var bodyLen = (leftLeg + rightLeg) / 2;
        var leftVis = meanVisibility(landmarks, [LANDMARK.L_SHOULDER, LANDMARK.L_HIP, LANDMARK.L_KNEE, LANDMARK.L_ANKLE]);
        var rightVis = meanVisibility(landmarks, [LANDMARK.R_SHOULDER, LANDMARK.R_HIP, LANDMARK.R_KNEE, LANDMARK.R_ANKLE]);
        var depthNorm;
        var torso;

        if (!leftKnee || !rightKnee || !leftHip || !rightHip || bodyLen < 1e-6) {
            return null;
        }

        depthNorm = weightedPair((lAnk.y - lHip.y) / bodyLen, (rAnk.y - rHip.y) / bodyLen, leftVis, rightVis);
        torso = weightedPair(torsoTiltDeg(lHip, lSh), torsoTiltDeg(rHip, rSh), leftVis, rightVis);

        return {
            primary_angle: weightedPair(leftKnee, rightKnee, leftVis, rightVis),
            secondary_angle: weightedPair(leftHip, rightHip, leftVis, rightVis),
            depth_norm: depthNorm,
            torso_angle: torso,
            asymmetry: Math.abs(leftKnee - rightKnee),
            hip_asymmetry: Math.abs(leftHip - rightHip),
            side_view_score: viewQualityScore(landmarks, bodyLen, viewType),
            heel_lift_norm: weightedPair(heelLiftNorm(lHeel, lToe, bodyLen), heelLiftNorm(rHeel, rToe, bodyLen), leftVis, rightVis),
            leg_angle: 180,
            posture_tilt_deg: Math.abs(90 - torso),
            hip_ankle_vertical_norm: weightedPair(Math.abs(lHip.y - lAnk.y) / bodyLen, Math.abs(rHip.y - rAnk.y) / bodyLen, leftVis, rightVis)
        };
    }

    function buildHingeLikeMetrics(landmarks, viewType) {
        var squat = buildSquatLikeMetrics(landmarks, viewType);
        if (!squat) {
            return null;
        }
        return {
            primary_angle: squat.secondary_angle,
            secondary_angle: squat.primary_angle,
            depth_norm: squat.hip_ankle_vertical_norm,
            torso_angle: squat.torso_angle,
            asymmetry: squat.hip_asymmetry,
            hip_asymmetry: squat.asymmetry,
            side_view_score: squat.side_view_score,
            heel_lift_norm: squat.heel_lift_norm,
            leg_angle: squat.primary_angle,
            posture_tilt_deg: squat.posture_tilt_deg,
            hip_ankle_vertical_norm: squat.hip_ankle_vertical_norm
        };
    }

    function buildLungeLikeMetrics(landmarks, viewType) {
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
        var leftKnee = angleDeg(lHip, lKnee, lAnk);
        var rightKnee = angleDeg(rHip, rKnee, rAnk);
        var leftHip = angleDeg(lSh, lHip, lKnee);
        var rightHip = angleDeg(rSh, rHip, rKnee);
        var leftLeg = distance2d(lHip, lKnee) + distance2d(lKnee, lAnk);
        var rightLeg = distance2d(rHip, rKnee) + distance2d(rKnee, rAnk);
        var bodyLen = (leftLeg + rightLeg) / 2;
        var activeIsLeft;
        var activeHip;
        var activeSh;
        var activeAnk;
        var activeHeel;
        var activeToe;
        var activeKneeAngle;
        var activeHipAngle;
        var passiveKneeAngle;
        var torso;

        if (!leftKnee || !rightKnee || !leftHip || !rightHip || bodyLen < 1e-6) {
            return null;
        }

        activeIsLeft = leftKnee <= rightKnee;
        activeHip = activeIsLeft ? lHip : rHip;
        activeSh = activeIsLeft ? lSh : rSh;
        activeAnk = activeIsLeft ? lAnk : rAnk;
        activeHeel = activeIsLeft ? lHeel : rHeel;
        activeToe = activeIsLeft ? lToe : rToe;
        activeKneeAngle = activeIsLeft ? leftKnee : rightKnee;
        activeHipAngle = activeIsLeft ? leftHip : rightHip;
        passiveKneeAngle = activeIsLeft ? rightKnee : leftKnee;
        torso = torsoTiltDeg(activeHip, activeSh);

        return {
            primary_angle: activeKneeAngle,
            secondary_angle: activeHipAngle,
            depth_norm: (activeAnk.y - activeHip.y) / bodyLen,
            torso_angle: torso,
            asymmetry: Math.abs(leftKnee - rightKnee),
            hip_asymmetry: Math.abs(leftHip - rightHip),
            side_view_score: viewQualityScore(landmarks, bodyLen, viewType),
            heel_lift_norm: heelLiftNorm(activeHeel, activeToe, bodyLen),
            leg_angle: passiveKneeAngle,
            posture_tilt_deg: Math.abs(90 - torso),
            hip_ankle_vertical_norm: Math.abs(activeHip.y - activeAnk.y) / bodyLen
        };
    }

    function buildPushLikeMetrics(landmarks, viewType) {
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
        var leftElbow = angleDeg(lSh, lEl, lWr);
        var rightElbow = angleDeg(rSh, rEl, rWr);
        var leftBody = angleDeg(lSh, lHip, lAnk);
        var rightBody = angleDeg(rSh, rHip, rAnk);
        var leftLeg = angleDeg(lHip, lKnee, lAnk);
        var rightLeg = angleDeg(rHip, rKnee, rAnk);
        var leftBodyLen = distance2d(lSh, lHip) + distance2d(lHip, lAnk);
        var rightBodyLen = distance2d(rSh, rHip) + distance2d(rHip, rAnk);
        var bodyLen = (leftBodyLen + rightBodyLen) / 2;
        var leftVis = meanVisibility(landmarks, [LANDMARK.L_SHOULDER, LANDMARK.L_ELBOW, LANDMARK.L_WRIST, LANDMARK.L_HIP, LANDMARK.L_ANKLE]);
        var rightVis = meanVisibility(landmarks, [LANDMARK.R_SHOULDER, LANDMARK.R_ELBOW, LANDMARK.R_WRIST, LANDMARK.R_HIP, LANDMARK.R_ANKLE]);
        var leftBodyBreak;
        var rightBodyBreak;
        var bodyBreak;

        if (!leftElbow || !rightElbow || !leftBody || !rightBody || bodyLen < 1e-6) {
            return null;
        }

        leftBodyBreak = Math.max(0, 180 - leftBody);
        rightBodyBreak = Math.max(0, 180 - rightBody);
        bodyBreak = weightedPair(leftBodyBreak, rightBodyBreak, leftVis, rightVis);

        return {
            primary_angle: weightedPair(leftElbow, rightElbow, leftVis, rightVis),
            secondary_angle: weightedPair(leftBody, rightBody, leftVis, rightVis),
            depth_norm: weightedPair((lAnk.y - lSh.y) / leftBodyLen, (rAnk.y - rSh.y) / rightBodyLen, leftVis, rightVis),
            torso_angle: bodyBreak,
            asymmetry: Math.abs(leftElbow - rightElbow),
            hip_asymmetry: Math.abs(leftBody - rightBody),
            side_view_score: viewQualityScore(landmarks, bodyLen, viewType),
            heel_lift_norm: 0,
            leg_angle: weightedPair(leftLeg, rightLeg, leftVis, rightVis),
            posture_tilt_deg: weightedPair(torsoTiltDeg(lHip, lSh), torsoTiltDeg(rHip, rSh), leftVis, rightVis),
            hip_ankle_vertical_norm: weightedPair(Math.abs(lHip.y - lAnk.y) / leftBodyLen, Math.abs(rHip.y - rAnk.y) / rightBodyLen, leftVis, rightVis)
        };
    }

    function buildCoreLikeMetrics(landmarks, viewType) {
        var lSh = getPoint(landmarks, LANDMARK.L_SHOULDER);
        var rSh = getPoint(landmarks, LANDMARK.R_SHOULDER);
        var lHip = getPoint(landmarks, LANDMARK.L_HIP);
        var rHip = getPoint(landmarks, LANDMARK.R_HIP);
        var lKnee = getPoint(landmarks, LANDMARK.L_KNEE);
        var rKnee = getPoint(landmarks, LANDMARK.R_KNEE);
        var lAnk = getPoint(landmarks, LANDMARK.L_ANKLE);
        var rAnk = getPoint(landmarks, LANDMARK.R_ANKLE);
        var leftCore = angleDeg(lSh, lHip, lKnee);
        var rightCore = angleDeg(rSh, rHip, rKnee);
        var leftLeg = angleDeg(lHip, lKnee, lAnk);
        var rightLeg = angleDeg(rHip, rKnee, rAnk);
        var leftBodyLen = distance2d(lSh, lHip) + distance2d(lHip, lKnee);
        var rightBodyLen = distance2d(rSh, rHip) + distance2d(rHip, rKnee);
        var bodyLen = (leftBodyLen + rightBodyLen) / 2;
        var leftVis = meanVisibility(landmarks, [LANDMARK.L_SHOULDER, LANDMARK.L_HIP, LANDMARK.L_KNEE]);
        var rightVis = meanVisibility(landmarks, [LANDMARK.R_SHOULDER, LANDMARK.R_HIP, LANDMARK.R_KNEE]);
        var torso;

        if (!leftCore || !rightCore || bodyLen < 1e-6) {
            return null;
        }

        torso = weightedPair(torsoTiltDeg(lHip, lSh), torsoTiltDeg(rHip, rSh), leftVis, rightVis);

        return {
            primary_angle: weightedPair(leftCore, rightCore, leftVis, rightVis),
            secondary_angle: weightedPair(leftLeg, rightLeg, leftVis, rightVis),
            depth_norm: weightedPair(distance2d(lSh, lKnee) / bodyLen, distance2d(rSh, rKnee) / bodyLen, leftVis, rightVis),
            torso_angle: torso,
            asymmetry: Math.abs(leftCore - rightCore),
            hip_asymmetry: Math.abs(toNumber(leftLeg, 180) - toNumber(rightLeg, 180)),
            side_view_score: viewQualityScore(landmarks, bodyLen, viewType),
            heel_lift_norm: 0,
            leg_angle: weightedPair(leftLeg, rightLeg, leftVis, rightVis),
            posture_tilt_deg: Math.abs(90 - torso),
            hip_ankle_vertical_norm: weightedPair(Math.abs(lHip.y - lKnee.y) / bodyLen, Math.abs(rHip.y - rKnee.y) / bodyLen, leftVis, rightVis)
        };
    }

    function buildMetricFrame(landmarks, motionFamily, viewTypeOrTimestamp, maybeTimestampMs) {
        var metric = null;
        var viewType = 'side';
        var timestampMs = maybeTimestampMs;

        if (typeof viewTypeOrTimestamp === 'string') {
            viewType = viewTypeOrTimestamp;
        } else {
            timestampMs = viewTypeOrTimestamp;
        }

        if (!Array.isArray(landmarks) || !landmarks.length) {
            return null;
        }
        if (motionFamily === 'squat_like') {
            metric = buildSquatLikeMetrics(landmarks, viewType);
        } else if (motionFamily === 'lunge_like') {
            metric = buildLungeLikeMetrics(landmarks, viewType);
        } else if (motionFamily === 'hinge_like') {
            metric = buildHingeLikeMetrics(landmarks, viewType);
        } else if (motionFamily === 'push_like') {
            metric = buildPushLikeMetrics(landmarks, viewType);
        } else if (motionFamily === 'core_like') {
            metric = buildCoreLikeMetrics(landmarks, viewType);
        }

        if (!metric) {
            return null;
        }

        metric.timestamp_ms = Math.round(toNumber(timestampMs, 0));
        return metric;
    }

    function ensurePoseAssets() {
        if (poseAssetsPromise) {
            return poseAssetsPromise;
        }
        poseAssetsPromise = site.loadScript('https://cdn.jsdelivr.net/npm/@mediapipe/pose/pose.js').then(function () {
            return true;
        });
        return poseAssetsPromise;
    }

    function createPoseAnalyzer() {
        return ensurePoseAssets().then(function () {
            var pose;
            var pendingResolve = null;
            var pendingReject = null;

            if (typeof window.Pose !== 'function') {
                throw new Error('MediaPipe Pose не загрузился.');
            }

            pose = new window.Pose({
                locateFile: function (file) {
                    return 'https://cdn.jsdelivr.net/npm/@mediapipe/pose/' + file;
                }
            });
            pose.setOptions({
                modelComplexity: 1,
                smoothLandmarks: true,
                enableSegmentation: false,
                minDetectionConfidence: 0.5,
                minTrackingConfidence: 0.5
            });
            pose.onResults(function (results) {
                var resolve = pendingResolve;
                pendingResolve = null;
                pendingReject = null;
                if (resolve) {
                    resolve(results);
                }
            });

            return {
                analyzeImage: function (image) {
                    return new Promise(function (resolve, reject) {
                        pendingResolve = resolve;
                        pendingReject = reject;
                        Promise.resolve(pose.send({ image: image })).catch(function (error) {
                            pendingResolve = null;
                            pendingReject = null;
                            reject(error);
                        });
                    });
                },
                dispose: function () {
                    pendingResolve = null;
                    if (pendingReject) {
                        pendingReject(new Error('Pose analyzer остановлен.'));
                        pendingReject = null;
                    }
                    if (pose && typeof pose.close === 'function') {
                        try {
                            pose.close();
                        } catch (error) {
                            return;
                        }
                    }
                }
            };
        });
    }

    function waitForEvent(target, eventName) {
        return new Promise(function (resolve, reject) {
            function onSuccess() {
                cleanup();
                resolve();
            }
            function onError() {
                cleanup();
                reject(new Error('Не удалось прочитать видеофайл.'));
            }
            function cleanup() {
                target.removeEventListener(eventName, onSuccess);
                target.removeEventListener('error', onError);
            }
            target.addEventListener(eventName, onSuccess, { once: true });
            target.addEventListener('error', onError, { once: true });
        });
    }

    function average(values) {
        if (!Array.isArray(values) || !values.length) {
            return 0;
        }
        return values.reduce(function (sum, value) {
            return sum + toNumber(value, 0);
        }, 0) / values.length;
    }

    function percentile(values, pct) {
        var ordered;
        var position;
        var left;
        var right;
        var weight;

        if (!Array.isArray(values) || !values.length) {
            return 0;
        }

        ordered = values.slice().sort(function (a, b) {
            return a - b;
        });
        if (ordered.length === 1) {
            return ordered[0];
        }

        position = (ordered.length - 1) * (pct / 100);
        left = Math.floor(position);
        right = Math.min(left + 1, ordered.length - 1);
        if (left === right) {
            return ordered[left];
        }
        weight = position - left;
        return ordered[left] * (1 - weight) + ordered[right] * weight;
    }

    function calculateFrameMetricsDuration(frameMetrics) {
        var firstMetric;
        var lastMetric;
        var firstTimestamp;
        var lastTimestamp;

        if (!Array.isArray(frameMetrics) || frameMetrics.length < 2) {
            return 0;
        }

        firstMetric = frameMetrics[0] || {};
        lastMetric = frameMetrics[frameMetrics.length - 1] || {};
        firstTimestamp = Math.round(toNumber(firstMetric.timestamp_ms, 0));
        lastTimestamp = Math.round(toNumber(lastMetric.timestamp_ms, firstTimestamp));
        return Math.max(0, lastTimestamp - firstTimestamp);
    }

    function normalizeFrameMetricsTimestamps(frameMetrics) {
        var baseTimestamp;

        if (!Array.isArray(frameMetrics) || !frameMetrics.length) {
            return [];
        }

        baseTimestamp = Math.round(toNumber(frameMetrics[0].timestamp_ms, 0));
        return frameMetrics.map(function (metric, index) {
            var nextMetric = Object.assign({}, metric);
            var fallbackTimestamp = index * 100;
            nextMetric.timestamp_ms = Math.max(
                0,
                Math.round(toNumber(metric && metric.timestamp_ms, fallbackTimestamp) - baseTimestamp)
            );
            return nextMetric;
        });
    }

    function metricWindowBaseline(frameMetrics, key) {
        var values = frameMetrics.map(function (metric) {
            return toNumber(metric && metric[key], 0);
        });
        var head = Math.max(1, Math.floor(values.length / 8));
        var samples = values.slice(0, head).concat(values.slice(Math.max(values.length - head, 0)));
        return average(samples);
    }

    function metricWindowAmplitude(frameMetrics, key, baseline) {
        return Math.max(
            frameMetrics.reduce(function (maxValue, metric) {
                return Math.max(maxValue, Math.abs(toNumber(metric && metric[key], baseline) - baseline));
            }, 0),
            1e-6
        );
    }

    function mergeActiveSegments(segments, maxGap) {
        return segments.reduce(function (result, segment) {
            var previous = result.length ? result[result.length - 1] : null;

            if (previous && segment.start - previous.end - 1 <= maxGap) {
                previous.end = segment.end;
                previous.score = previous.score + segment.score;
                return result;
            }

            result.push({
                start: segment.start,
                end: segment.end,
                score: segment.score
            });
            return result;
        }, []);
    }

    function isolateSingleRep(frameMetrics) {
        var baselines;
        var amplitudes;
        var activityScores;
        var maxScore;
        var threshold;
        var segments = [];
        var currentStart = null;
        var scoreSum = 0;
        var bestSegment;
        var selectedFrames;

        if (!Array.isArray(frameMetrics) || !frameMetrics.length) {
            return { frameMetrics: [], durationMs: 0, trimmed: false };
        }

        if (frameMetrics.length < 12) {
            selectedFrames = normalizeFrameMetricsTimestamps(frameMetrics);
            return {
                frameMetrics: selectedFrames,
                durationMs: calculateFrameMetricsDuration(selectedFrames),
                trimmed: false
            };
        }

        baselines = {
            primary_angle: metricWindowBaseline(frameMetrics, 'primary_angle'),
            secondary_angle: metricWindowBaseline(frameMetrics, 'secondary_angle'),
            depth_norm: metricWindowBaseline(frameMetrics, 'depth_norm'),
            torso_angle: metricWindowBaseline(frameMetrics, 'torso_angle')
        };
        amplitudes = {
            primary_angle: metricWindowAmplitude(frameMetrics, 'primary_angle', baselines.primary_angle),
            secondary_angle: metricWindowAmplitude(frameMetrics, 'secondary_angle', baselines.secondary_angle),
            depth_norm: metricWindowAmplitude(frameMetrics, 'depth_norm', baselines.depth_norm),
            torso_angle: metricWindowAmplitude(frameMetrics, 'torso_angle', baselines.torso_angle)
        };

        activityScores = frameMetrics.map(function (metric) {
            return clamp(
                Math.max(
                    Math.abs(toNumber(metric && metric.primary_angle, baselines.primary_angle) - baselines.primary_angle) / amplitudes.primary_angle,
                    Math.abs(toNumber(metric && metric.secondary_angle, baselines.secondary_angle) - baselines.secondary_angle) / amplitudes.secondary_angle,
                    Math.abs(toNumber(metric && metric.depth_norm, baselines.depth_norm) - baselines.depth_norm) / amplitudes.depth_norm,
                    Math.abs(toNumber(metric && metric.torso_angle, baselines.torso_angle) - baselines.torso_angle) / amplitudes.torso_angle
                ),
                0,
                1.6
            );
        });

        maxScore = Math.max.apply(null, activityScores.concat([0]));
        if (maxScore < 0.12) {
            selectedFrames = normalizeFrameMetricsTimestamps(frameMetrics);
            return {
                frameMetrics: selectedFrames,
                durationMs: calculateFrameMetricsDuration(selectedFrames),
                trimmed: false
            };
        }

        threshold = clamp(
            Math.max(
                0.12,
                percentile(activityScores, 70) * 0.92,
                maxScore * 0.28
            ),
            0.12,
            0.48
        );

        activityScores.forEach(function (score, index) {
            if (score >= threshold) {
                if (currentStart === null) {
                    currentStart = index;
                    scoreSum = 0;
                }
                scoreSum += score;
                return;
            }

            if (currentStart !== null) {
                segments.push({
                    start: currentStart,
                    end: index - 1,
                    score: scoreSum
                });
                currentStart = null;
                scoreSum = 0;
            }
        });

        if (currentStart !== null) {
            segments.push({
                start: currentStart,
                end: activityScores.length - 1,
                score: scoreSum
            });
        }

        segments = mergeActiveSegments(segments, 2);
        if (!segments.length) {
            selectedFrames = normalizeFrameMetricsTimestamps(frameMetrics);
            return {
                frameMetrics: selectedFrames,
                durationMs: calculateFrameMetricsDuration(selectedFrames),
                trimmed: false
            };
        }

        bestSegment = segments.reduce(function (best, segment) {
            var segmentLength = segment.end - segment.start + 1;
            var bestLength = best.end - best.start + 1;
            var segmentValue = segment.score * segmentLength;
            var bestValue = best.score * bestLength;
            return segmentValue > bestValue ? segment : best;
        });

        bestSegment = {
            start: Math.max(0, bestSegment.start - 2),
            end: Math.min(frameMetrics.length - 1, bestSegment.end + 2)
        };
        selectedFrames = frameMetrics.slice(bestSegment.start, bestSegment.end + 1);

        if (selectedFrames.length < 10) {
            selectedFrames = normalizeFrameMetricsTimestamps(frameMetrics);
            return {
                frameMetrics: selectedFrames,
                durationMs: calculateFrameMetricsDuration(selectedFrames),
                trimmed: false
            };
        }

        selectedFrames = normalizeFrameMetricsTimestamps(selectedFrames);
        return {
            frameMetrics: selectedFrames,
            durationMs: calculateFrameMetricsDuration(selectedFrames),
            trimmed: bestSegment.start > 0 || bestSegment.end < frameMetrics.length - 1
        };
    }

    function extractReferenceFromFile(file, motionFamily, viewType, onProgress) {
        return createPoseAnalyzer().then(function (analyzer) {
            var objectUrl = window.URL.createObjectURL(file);
            var video = document.createElement('video');
            var frameMetrics = [];
            var disposed = false;

            video.preload = 'auto';
            video.muted = true;
            video.playsInline = true;
            video.src = objectUrl;
            video.load();

            function cleanup() {
                if (disposed) {
                    return;
                }
                disposed = true;
                analyzer.dispose();
                video.pause();
                video.removeAttribute('src');
                video.load();
                window.URL.revokeObjectURL(objectUrl);
            }

            function seekTo(timeSec) {
                return new Promise(function (resolve, reject) {
                    function onSeeked() {
                        cleanupListeners();
                        resolve();
                    }
                    function onError() {
                        cleanupListeners();
                        reject(new Error('Не удалось позиционировать видео.'));
                    }
                    function cleanupListeners() {
                        video.removeEventListener('seeked', onSeeked);
                        video.removeEventListener('error', onError);
                    }

                    video.addEventListener('seeked', onSeeked, { once: true });
                    video.addEventListener('error', onError, { once: true });
                    video.currentTime = timeSec;
                });
            }

            return waitForEvent(video, 'loadedmetadata')
                .then(async function () {
                    var durationSec = Math.max(0.35, Number(video.duration) || 0.35);
                    var sampleCount = Math.max(18, Math.min(72, Math.round(durationSec * 18)));
                    var index;
                    var isolatedRep;

                    for (index = 0; index < sampleCount; index += 1) {
                        var progress = sampleCount <= 1 ? 0 : index / (sampleCount - 1);
                        var targetTime = Math.min(durationSec - 0.01, progress * durationSec);
                        var results;
                        var metric;

                        await seekTo(Math.max(0, targetTime));
                        results = await analyzer.analyzeImage(video);
                        metric = buildMetricFrame(results && results.poseLandmarks, motionFamily, viewType, targetTime * 1000);
                        if (metric) {
                            frameMetrics.push(metric);
                        }
                        if (typeof onProgress === 'function') {
                            onProgress((index + 1) / sampleCount);
                        }
                    }

                    if (frameMetrics.length < 10) {
                        throw new Error('Не удалось уверенно извлечь позу из эталонного ролика.');
                    }

                    isolatedRep = isolateSingleRep(frameMetrics);
                    if (isolatedRep.frameMetrics.length < 10) {
                        throw new Error('Не удалось выделить один чистый повтор из эталонного ролика.');
                    }

                    return {
                        frameMetrics: isolatedRep.frameMetrics,
                        videoMeta: {
                            duration_ms: Math.max(1, isolatedRep.durationMs || Math.round(durationSec * 1000)),
                            width: video.videoWidth || 0,
                            height: video.videoHeight || 0,
                            size_bytes: toNumber(file.size, 0),
                            sample_count: sampleCount,
                            trimmed: isolatedRep.trimmed === true
                        }
                    };
                })
                .finally(function () {
                    cleanup();
                });
        });
    }

    window.KinematicsCustomTechnique = {
        LANDMARK: LANDMARK,
        buildMetricFrame: buildMetricFrame,
        isolateSingleRep: isolateSingleRep,
        createPoseAnalyzer: createPoseAnalyzer,
        ensurePoseAssets: ensurePoseAssets,
        extractReferenceFromFile: extractReferenceFromFile
    };
})();
