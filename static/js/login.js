 const password = document.getElementById("password");
        const togglePassword = document.getElementById("togglePassword");
        const eyeIcon = document.getElementById("eyeIcon");
            
        togglePassword.addEventListener("click", () => {
            if (password.type === "password") {
                password.type = "text";
                eyeIcon.classList.replace("fa-eye", "fa-eye-slash");
            } else {
                password.type = "password";
                eyeIcon.classList.replace("fa-eye-slash", "fa-eye");
            }
        });