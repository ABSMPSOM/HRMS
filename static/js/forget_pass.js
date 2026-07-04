document.addEventListener("DOMContentLoaded", () => {

    // Card Animation
    gsap.to("#forgot-card", {
        duration: 0.7,
        y: 0,
        opacity: 1,
        ease: "power3.out"
    });

    // Elements Animation
    gsap.from(".gsap-element", {
        duration: 0.6,
        y: 15,
        opacity: 0,
        stagger: 0.1,
        ease: "power2.out",
        delay: 0.2
    });

    // OTP Section
    const sendOtpBtn = document.getElementById("sendOtpBtn");
    const otpSection = document.getElementById("otpSection");

    if (sendOtpBtn && otpSection) {
        sendOtpBtn.addEventListener("click", () => {
            otpSection.classList.remove("hidden");
        });
    }

});