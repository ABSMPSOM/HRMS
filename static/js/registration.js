// ================================
// Password Show / Hide Function
// ================================

function setupPasswordToggle(inputId, buttonId, iconId) {
    const input = document.getElementById(inputId);
    const button = document.getElementById(buttonId);
    const icon = document.getElementById(iconId);

    if (!input || !button || !icon) return;

    button.addEventListener("click", () => {

        if (input.type === "password") {
            input.type = "text";
            icon.classList.remove("fa-eye");
            icon.classList.add("fa-eye-slash");
        } else {
            input.type = "password";
            icon.classList.remove("fa-eye-slash");
            icon.classList.add("fa-eye");
        }

    });
}

// Password
setupPasswordToggle("password", "togglePassword", "eyeIcon");

// Confirm Password
setupPasswordToggle(
    "confirmPassword",
    "toggleConfirmPassword",
    "confirmEyeIcon"
);

// ================================
// Password Match Checker
// ================================

const password = document.getElementById("password");
const confirmPassword = document.getElementById("confirmPassword");
const passwordMessage = document.getElementById("passwordMessage");

function checkPasswords() {

    if (!password || !confirmPassword || !passwordMessage) return;

    if (confirmPassword.value === "") {
        passwordMessage.textContent = "";
        return;
    }

    if (password.value === confirmPassword.value) {

        passwordMessage.textContent = "✓ Passwords Match";
        passwordMessage.className =
            "text-green-400 text-sm mt-2";

    } else {

        passwordMessage.textContent = "✗ Passwords Do Not Match";
        passwordMessage.className =
            "text-red-400 text-sm mt-2";

    }

}

if (password && confirmPassword) {

    password.addEventListener("input", checkPasswords);
    confirmPassword.addEventListener("input", checkPasswords);

}

// ================================
// Form Validation
// ================================

const form = document.querySelector("form");

if (form) {

    form.addEventListener("submit", function (e) {

        if (password.value !== confirmPassword.value) {

            e.preventDefault();

            alert("Passwords do not match!");

            confirmPassword.focus();

        }

    });

}