(function () {
    var site = window.KinematicsSite || null;

    function getElement(id) {
        return document.getElementById(id);
    }

    function setError(message) {
        var errorNode = getElement("auth-error");
        if (errorNode) {
            errorNode.textContent = message || "";
        }
    }

    function setSuccess(message) {
        var successNode = getElement("auth-success");
        if (successNode) {
            successNode.textContent = message || "";
        }
    }

    async function parseResponse(response) {
        try {
            return await response.json();
        } catch (error) {
            return {};
        }
    }

    function extractErrorMessage(data, fallbackMessage) {
        if (!data) {
            return fallbackMessage;
        }

        if (typeof data.detail === "string") {
            return data.detail;
        }

        if (Array.isArray(data.detail) && data.detail.length > 0) {
            var firstError = data.detail[0];
            if (firstError && typeof firstError.msg === "string") {
                return firstError.msg;
            }
        }

        return fallbackMessage;
    }

    async function handleLoginSubmit(event) {
        event.preventDefault();
        setError("");
        setSuccess("");

        var form = event.currentTarget;
        var payload = {
            email: form.email.value,
            password: form.password.value,
        };

        var response = await fetch("/api/auth/login", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            credentials: "include",
            body: JSON.stringify(payload),
        });

        var data = await parseResponse(response);
        if (!response.ok) {
            setError(extractErrorMessage(data, "Ошибка входа. Проверьте данные."));
            return;
        }

        if (site && typeof site.resolveAppEntryUrl === "function") {
            try {
                var nextUrl = await site.resolveAppEntryUrl({ allowReset: true });
                window.location.assign(nextUrl);
                return;
            } catch (error) {
                window.location.assign("/app");
                return;
            }
        }

        window.location.assign("/app");
    }

    async function handleRegisterSubmit(event) {
        event.preventDefault();
        setError("");

        var form = event.currentTarget;
        var payload = {
            email: form.email.value,
            password: form.password.value,
            name: form.name ? form.name.value : null,
        };

        var response = await fetch("/api/auth/register", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            credentials: "include",
            body: JSON.stringify(payload),
        });

        var data = await parseResponse(response);
        if (!response.ok) {
            setError(extractErrorMessage(data, "Ошибка регистрации. Попробуйте снова."));
            return;
        }

        window.location.assign("/login?registered=1");
    }

    function setupForms() {
        var loginForm = getElement("login-form");
        if (loginForm) {
            loginForm.addEventListener("submit", handleLoginSubmit);

            var params = new URLSearchParams(window.location.search);
            if (params.get("registered") === "1") {
                setSuccess("Регистрация успешна. Теперь выполните вход.");
            }
        }

        var registerForm = getElement("register-form");
        if (registerForm) {
            registerForm.addEventListener("submit", handleRegisterSubmit);
        }
    }

    document.addEventListener("DOMContentLoaded", setupForms);
})();
