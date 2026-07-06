document.addEventListener("DOMContentLoaded", () => {
    // ===============================
    // 1. Initial Animations
    // ===============================
    gsap.to("#forgot-card", { duration: 0.7, y: 0, opacity: 1, ease: "power3.out" });
    gsap.from(".gsap-element", { duration: 0.6, y: 15, opacity: 0, stagger: 0.1, ease: "power2.out", delay: 0.2 });

    // ===============================
    // 2. DOM Elements & Utilities
    // ===============================
    const emailInput = document.getElementById("email");
    const sendOtpBtn = document.getElementById("sendOtpBtn");
    
    const otpSection = document.getElementById("otpSection");
    const emailSection = document.getElementById("emailSection");
    const otpInput = document.getElementById("otp");
    const verifyOtpBtn = document.getElementById("verifyOtpBtn");
    
    const resetSection = document.getElementById("resetSection");
    const newPassword = document.getElementById("newPassword");
    const confirmPassword = document.getElementById("confirmPassword");
    const submitResetBtn = document.getElementById("submitResetBtn");
    const passwordMessage = document.getElementById("passwordMessage");
    
    const msgBox = document.getElementById("msgBox");

    // Helper function to display messages
    function showMessage(msg, isError = false) {
        msgBox.textContent = msg;
        msgBox.className = `text-center text-sm p-3 rounded mb-4 font-bold transition-all ${
            isError 
            ? 'bg-red-500/20 text-red-400 border border-red-500/50' 
            : 'bg-green-500/20 text-green-400 border border-green-500/50'
        }`;
        msgBox.classList.remove("hidden");
    }

    // ===============================
    // 3. API Call: Send OTP
    // ===============================
    if (sendOtpBtn) {
        sendOtpBtn.addEventListener("click", async () => {
            const email = emailInput.value.trim();
            if (!email) {
                showMessage("Please enter your email address first.", true);
                return;
            }

            // Update UI to show loading state
            const originalText = sendOtpBtn.innerHTML;
            sendOtpBtn.innerHTML = `<i class="fa-solid fa-spinner fa-spin"></i> Sending...`;
            sendOtpBtn.disabled = true;

            try {
                const response = await fetch('/api/send-reset-otp', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ email: email })
                });
                
                const data = await response.json();

                if (data.success) {
                    showMessage("OTP sent to your email! It will expire in 10 minutes.");
                    otpSection.classList.remove("hidden");
                    sendOtpBtn.innerHTML = "Resend OTP";
                    
                    gsap.from("#otpSection", { y: 20, opacity: 0, duration: 0.5, ease: "power2.out" });
                } else {
                    showMessage(data.message || "Failed to send OTP. Please try again.", true);
                    sendOtpBtn.innerHTML = originalText;
                }
            } catch (error) {
                showMessage("A network error occurred. Please check your connection.", true);
                sendOtpBtn.innerHTML = originalText;
            } finally {
                sendOtpBtn.disabled = false;
            }
        });
    }

    // ===============================
    // 4. API Call: Verify OTP
    // ===============================
    if (verifyOtpBtn) {
        verifyOtpBtn.addEventListener("click", async () => {
            const email = emailInput.value.trim();
            const otp = otpInput.value.trim();
            
            if (!otp) {
                showMessage("Please enter the 6-digit OTP.", true);
                return;
            }

            const originalText = verifyOtpBtn.innerHTML;
            verifyOtpBtn.innerHTML = `<i class="fa-solid fa-spinner fa-spin"></i> Verifying...`;
            verifyOtpBtn.disabled = true;

            try {
                const response = await fetch('/api/verify-reset-otp', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ email: email, otp: otp })
                });
                
                const data = await response.json();

                if (data.success) {
                    showMessage("OTP Verified Successfully! Please enter your new password.");
                    
                    // Hide previous steps, show reset password form
                    emailSection.classList.add("hidden");
                    otpSection.classList.add("hidden");
                    resetSection.classList.remove("hidden");
                    
                    gsap.from("#resetSection", { y: 20, opacity: 0, duration: 0.6, ease: "power3.out" });
                } else {
                    showMessage(data.message || "Invalid OTP. Please try again.", true);
                    verifyOtpBtn.innerHTML = originalText;
                    verifyOtpBtn.disabled = false;
                }
            } catch (error) {
                showMessage("A network error occurred. Please try again.", true);
                verifyOtpBtn.innerHTML = originalText;
                verifyOtpBtn.disabled = false;
            }
        });
    }

    // ===============================
    // 5. API Call: Reset Password
    // ===============================
    if (submitResetBtn) {
        submitResetBtn.addEventListener("click", async () => {
            const email = emailInput.value.trim();
            const newPass = newPassword.value;
            const confirmPass = confirmPassword.value;

            if (!newPass || newPass !== confirmPass) {
                showMessage("Passwords do not match or are empty.", true);
                return;
            }

            const originalText = submitResetBtn.innerHTML;
            submitResetBtn.innerHTML = `<i class="fa-solid fa-spinner fa-spin"></i> Resetting...`;
            submitResetBtn.disabled = true;

            try {
                const response = await fetch('/api/reset-password', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ email: email, new_password: newPass })
                });
                
                const data = await response.json();

                if (data.success) {
                    showMessage("Password successfully reset! Redirecting to login...");
                    setTimeout(() => {
                        window.location.href = data.redirect;
                    }, 1500);
                } else {
                    showMessage(data.message || "Failed to reset password.", true);
                    submitResetBtn.innerHTML = originalText;
                    submitResetBtn.disabled = false;
                }
            } catch (error) {
                showMessage("A network error occurred. Please try again.", true);
                submitResetBtn.innerHTML = originalText;
                submitResetBtn.disabled = false;
            }
        });
    }

    // ===============================
    // 6. Password Match Checker UI
    // ===============================
    function checkPasswords() {
        if (!newPassword || !confirmPassword || !passwordMessage) return;
        
        if (confirmPassword.value === "") {
            passwordMessage.textContent = "";
            return;
        }

        if (newPassword.value === confirmPassword.value) {
            passwordMessage.textContent = "✓ Passwords Match";
            passwordMessage.className = "text-green-400 text-sm mt-2";
            submitResetBtn.disabled = false;
            submitResetBtn.classList.remove("opacity-50", "cursor-not-allowed");
        } else {
            passwordMessage.textContent = "✗ Passwords Do Not Match";
            passwordMessage.className = "text-red-400 text-sm mt-2";
            submitResetBtn.disabled = true;
            submitResetBtn.classList.add("opacity-50", "cursor-not-allowed");
        }
    }

    if (newPassword && confirmPassword) {
        newPassword.addEventListener("input", checkPasswords);
        confirmPassword.addEventListener("input", checkPasswords);
    }
});