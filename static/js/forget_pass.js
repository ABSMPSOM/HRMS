document.addEventListener("DOMContentLoaded", () => {

    // ===============================
    // Card Animation
    // ===============================
    gsap.to("#forgot-card", {
        duration: 0.7,
        y: 0,
        opacity: 1,
        ease: "power3.out"
    });

    gsap.from(".gsap-element", {
        duration: 0.6,
        y: 15,
        opacity: 0,
        stagger: 0.1,
        ease: "power2.out",
        delay: 0.2
    });

    // ===============================
    // Show OTP Section
    // ===============================
    const sendOtpBtn = document.getElementById("sendOtpBtn");
    const otpSection = document.getElementById("otpSection");

    if (sendOtpBtn && otpSection) {

        sendOtpBtn.addEventListener("click", () => {

            otpSection.classList.remove("hidden");

            sendOtpBtn.innerHTML = "Resend OTP";

        });

    }

    // ===============================
    // Verify OTP
    // ===============================
    const verifyOtpBtn = document.getElementById("verifyOtpBtn");
    const verifySection = document.getElementById("verifySection");
    const resetSection = document.getElementById("resetSection");

    if (verifyOtpBtn && verifySection && resetSection) {

        verifyOtpBtn.addEventListener("click", () => {

            // Later Flask OTP Verification

            verifySection.classList.add("hidden");

            resetSection.classList.remove("hidden");

            gsap.from("#resetSection", {
                y: 30,
                opacity: 0,
                duration: 0.6,
                ease: "power3.out"
            });

        });

    }

    // ===============================
    // Password Match Checker
    // ===============================
    const newPassword = document.getElementById("newPassword");
    const confirmPassword = document.getElementById("confirmPassword");
    const passwordMessage = document.getElementById("passwordMessage");

    function checkPasswords() {

        if (!newPassword || !confirmPassword || !passwordMessage) return;

        if (confirmPassword.value === "") {

            passwordMessage.textContent = "";

            return;

        }

        if (newPassword.value === confirmPassword.value) {

            passwordMessage.textContent = "✓ Passwords Match";
            passwordMessage.className = "text-green-400 text-sm mt-2";

        } else {

            passwordMessage.textContent = "✗ Passwords Do Not Match";
            passwordMessage.className = "text-red-400 text-sm mt-2";

        }

    }

    if (newPassword && confirmPassword) {

        newPassword.addEventListener("input", checkPasswords);
        confirmPassword.addEventListener("input", checkPasswords);

    }

    // ===============================
    // Password Show / Hide
    // ===============================
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

    setupPasswordToggle(
        "newPassword",
        "toggleNewPassword",
        "newEyeIcon"
    );

    setupPasswordToggle(
        "confirmPassword",
        "toggleConfirmPassword",
        "confirmEyeIcon"
    );

});