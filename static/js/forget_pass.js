document.addEventListener("DOMContentLoaded", () => {
    // 1. Initial Animations
    gsap.to("#forgot-card", { duration: 0.7, y: 0, opacity: 1, ease: "power3.out" });
    gsap.from(".gsap-element", { duration: 0.6, y: 15, opacity: 0, stagger: 0.1, ease: "power2.out", delay: 0.2 });

    // UI Elements
    const emailInput = document.getElementById("email");
    const sendOtpBtn = document.getElementById("sendOtpBtn");
    const otpSection = document.getElementById("otpSection");
    
    const otpInput = document.getElementById("otp");
    const verifyOtpBtn = document.getElementById("verifyOtpBtn");
    const resetSection = document.getElementById("resetSection");

    const newPassword = document.getElementById("newPassword");
    const confirmPassword = document.getElementById("confirmPassword");
    const submitResetBtn = document.getElementById("submitResetBtn");
    const passwordMessage = document.getElementById("passwordMessage");
    const msgBox = document.getElementById("msgBox");

    // Helper: Show Error/Success messages nicely
    function showMsg(msg, isError=true) {
        msgBox.textContent = msg;
        msgBox.className = `text-center text-xs p-3 rounded mb-4 font-bold block ${isError ? 'bg-red-500/20 text-red-400 border border-red-500' : 'bg-green-500/20 text-green-400 border border-green-500'}`;
    }

    // ===============================
    // STEP 1: SEND OTP (Talks to Python)
    // ===============================
    if (sendOtpBtn) {
        sendOtpBtn.addEventListener("click", () => {
            const email = emailInput.value;
            if(!email) return showMsg("Please enter your email.");

            sendOtpBtn.innerHTML = "Sending...";
            sendOtpBtn.disabled = true;

            fetch('/api/send-reset-otp', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ email: email })
            }).then(res => res.json()).then(data => {
                sendOtpBtn.innerHTML = "Resend OTP";
                sendOtpBtn.disabled = false;
                
                if(data.success) {
                    showMsg("OTP Sent! Check your email.", false);
                    emailInput.readOnly = true; // Lock email input
                    otpSection.classList.remove("hidden");
                    gsap.from("#otpSection", { y: 20, opacity: 0, duration: 0.5 });
                } else {
                    showMsg(data.message);
                }
            });
        });
    }

    // ===============================
    // STEP 2: VERIFY OTP (Talks to Python)
    // ===============================
    if (verifyOtpBtn) {
        verifyOtpBtn.addEventListener("click", () => {
            const email = emailInput.value;
            const otp = otpInput.value;
            if(!otp) return showMsg("Please enter the OTP.");

            verifyOtpBtn.innerHTML = "Verifying...";
            verifyOtpBtn.disabled = true;

            fetch('/api/verify-reset-otp', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ email: email, otp: otp })
            }).then(res => res.json()).then(data => {
                if(data.success) {
                    showMsg("OTP Verified! Enter new password.", false);
                    otpSection.classList.add("hidden");
                    sendOtpBtn.classList.add("hidden");
                    
                    resetSection.classList.remove("hidden");
                    gsap.from("#resetSection", { y: 30, opacity: 0, duration: 0.6, ease: "power3.out" });
                } else {
                    verifyOtpBtn.innerHTML = "Verify OTP";
                    verifyOtpBtn.disabled = false;
                    showMsg(data.message);
                }
            });
        });
    }

    // ===============================
    // STEP 3: RESET PASSWORD (Talks to Python)
    // ===============================
    if (submitResetBtn) {
        submitResetBtn.addEventListener("click", () => {
            const email = emailInput.value;
            const pw = newPassword.value;

            if(!pw || pw !== confirmPassword.value) return showMsg("Passwords do not match.");

            submitResetBtn.innerHTML = "Updating...";
            submitResetBtn.disabled = true;

            fetch('/api/reset-password', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ email: email, new_password: pw })
            }).then(res => res.json()).then(data => {
                if(data.success) {
                    window.location.href = data.redirect; // Jump to Login Page
                } else {
                    submitResetBtn.innerHTML = "Reset Password";
                    submitResetBtn.disabled = false;
                    showMsg(data.message);
                }
            });
        });
    }

    // Password Match Visualizer
    function checkPasswords() {
        if (!newPassword || !confirmPassword || !passwordMessage) return;
        if (confirmPassword.value === "") { passwordMessage.textContent = ""; return; }
        
        if (newPassword.value === confirmPassword.value) {
            passwordMessage.textContent = "✓ Passwords Match";
            passwordMessage.className = "text-green-400 text-sm mt-2 font-bold";
        } else {
            passwordMessage.textContent = "✗ Passwords Do Not Match";
            passwordMessage.className = "text-red-400 text-sm mt-2 font-bold";
        }
    }
    if (newPassword && confirmPassword) {
        newPassword.addEventListener("input", checkPasswords);
        confirmPassword.addEventListener("input", checkPasswords);
    }
});