// app/static/js/auth.js
// Authentication functionality for the crypto trading platform

/**
 * Initialize authentication components when DOM is loaded
 */
document.addEventListener('DOMContentLoaded', function() {
    // Initialize login form
    const loginForm = document.getElementById('loginForm');
    if (loginForm) {
        initLoginForm(loginForm);
    }
    
    // Initialize signup form
    const signupForm = document.getElementById('signupForm');
    if (signupForm) {
        initSignupForm(signupForm);
    }
    
    // Initialize OTP verification form
    const otpForm = document.getElementById('otpForm');
    if (otpForm) {
        initOtpForm(otpForm);
    }
    
    // Initialize password reset form
    const resetPasswordForm = document.getElementById('resetPasswordForm');
    if (resetPasswordForm) {
        initResetPasswordForm(resetPasswordForm);
    }
});

/**
 * Initialize login form validation and submission
 * @param {HTMLFormElement} form - The login form element
 */
function initLoginForm(form) {
    form.addEventListener('submit', function(e) {
        e.preventDefault();
        
        // Get form inputs
        const loginIdentifier = form.querySelector('#login_identifier');
        const password = form.querySelector('#password');
        const rememberMe = form.querySelector('#remember_me');
        
        // Validate inputs
        if (!loginIdentifier.value.trim()) {
            showError(loginIdentifier, 'Please enter your email or username.');
            return;
        }
        
        if (!password.value) {
            showError(password, 'Please enter your password.');
            return;
        }
        
        // Create form data
        const formData = new FormData();
        formData.append('login_identifier', loginIdentifier.value.trim());
        formData.append('password', password.value);
        
        if (rememberMe && rememberMe.checked) {
            formData.append('remember_me', 'true');
        }
        
        // Show loading state
        const submitButton = form.querySelector('button[type="submit"]');
        const originalText = submitButton.textContent;
        submitButton.disabled = true;
        submitButton.innerHTML = '<i class="fas fa-spinner fa-spin mr-2"></i> Signing in...';
        
        // Submit the form
        fetch(form.action, {
            method: 'POST',
            body: formData,
            headers: {
                'X-Requested-With': 'XMLHttpRequest'
            }
        })
        .then(response => {
            if (response.redirected) {
                window.location.href = response.url;
                return;
            }
            
            return response.json();
        })
        .then(data => {
            if (data && data.success === false) {
                showFormError(form, data.message || 'Invalid credentials. Please try again.');
                submitButton.disabled = false;
                submitButton.innerHTML = originalText;
            }
        })
        .catch(error => {
            console.error('Error:', error);
            showFormError(form, 'An error occurred. Please try again.');
            submitButton.disabled = false;
            submitButton.innerHTML = originalText;
        });
    });
}

/**
 * Initialize signup form validation and submission
 * @param {HTMLFormElement} form - The signup form element
 */
function initSignupForm(form) {
    // Password strength meter
    const password = form.querySelector('#password');
    const passwordStrengthMeter = document.createElement('div');
    passwordStrengthMeter.className = 'password-strength-meter mt-1 h-1 rounded-full bg-gray-200';
    password.parentNode.appendChild(passwordStrengthMeter);
    
    password.addEventListener('input', function() {
        updatePasswordStrength(this.value, passwordStrengthMeter);
    });
    
    // Form submission
    form.addEventListener('submit', function(e) {
        e.preventDefault();
        
        // Get form inputs
        const username = form.querySelector('#username');
        const email = form.querySelector('#email');
        const phone = form.querySelector('#phone');
        const password = form.querySelector('#password');
        const confirmPassword = form.querySelector('#confirm_password');
        const terms = form.querySelector('#terms');
        
        // Validate inputs
        if (!username.value.trim()) {
            showError(username, 'Please enter a username.');
            return;
        }
        
        if (!validateEmail(email.value)) {
            showError(email, 'Please enter a valid email address.');
            return;
        }
        
        if (!validatePhone(phone.value)) {
            showError(phone, 'Please enter a valid phone number.');
            return;
        }
        
        if (!validatePassword(password.value)) {
            showError(password, 'Password must be at least 8 characters with a number, uppercase, and lowercase letter.');
            return;
        }
        
        if (password.value !== confirmPassword.value) {
            showError(confirmPassword, 'Passwords do not match.');
            return;
        }
        
        if (!terms.checked) {
            showError(terms, 'You must agree to the Terms of Service and Privacy Policy.');
            return;
        }
        
        // Show loading state
        const submitButton = form.querySelector('button[type="submit"]');
        const originalText = submitButton.textContent;
        submitButton.disabled = true;
        submitButton.innerHTML = '<i class="fas fa-spinner fa-spin mr-2"></i> Creating account...';
        
        // Submit the form
        fetch(form.action, {
            method: 'POST',
            body: new FormData(form),
            headers: {
                'X-Requested-With': 'XMLHttpRequest'
            }
        })
        .then(response => {
            if (response.redirected) {
                window.location.href = response.url;
                return;
            }
            
            return response.json();
        })
        .then(data => {
            if (data && data.success === false) {
                showFormError(form, data.message || 'Registration failed. Please try again.');
                submitButton.disabled = false;
                submitButton.innerHTML = originalText;
            }
        })
        .catch(error => {
            console.error('Error:', error);
            showFormError(form, 'An error occurred. Please try again.');
            submitButton.disabled = false;
            submitButton.innerHTML = originalText;
        });
    });
}

/**
 * Initialize OTP verification form
 * @param {HTMLFormElement} form - The OTP form element
 */
function initOtpForm(form) {
    const otpInput = form.querySelector('#otp');
    const resendButton = document.getElementById('resendOtp');
    const countdownElement = document.getElementById('countdown');
    
    // Focus OTP input
    if (otpInput) {
        otpInput.focus();
        
        // Auto-submit when all digits are entered
        otpInput.addEventListener('input', function() {
            if (this.value.length === 6) {
                form.submit();
            }
        });
        
        // Only allow numbers
        otpInput.addEventListener('keypress', function(e) {
            if (isNaN(e.key)) {
                e.preventDefault();
            }
        });
    }
    
    // Initialize resend countdown
    if (resendButton && countdownElement) {
        let countdown = parseInt(countdownElement.textContent);
        resendButton.disabled = true;
        
        const countdownInterval = setInterval(() => {
            countdown--;
            countdownElement.textContent = countdown;
            
            if (countdown <= 0) {
                clearInterval(countdownInterval);
                resendButton.disabled = false;
                resendButton.parentElement.querySelector('#resendTimer').classList.add('hidden');
            }
        }, 1000);
        
        // Handle resend button click
        resendButton.addEventListener('click', function() {
            if (this.disabled) return;
            
            this.disabled = true;
            const timer = this.parentElement.querySelector('#resendTimer');
            timer.classList.remove('hidden');
            
            fetch('/auth/resend-otp', {
                method: 'POST',
                headers: {
                    'X-Requested-With': 'XMLHttpRequest'
                }
            })
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    // Reset countdown
                    countdown = 60;
                    countdownElement.textContent = countdown;
                    
                    // Show success message
                    showSuccessMessage('Verification code sent successfully.');
                    
                    // Restart countdown
                    const newInterval = setInterval(() => {
                        countdown--;
                        countdownElement.textContent = countdown;
                        
                        if (countdown <= 0) {
                            clearInterval(newInterval);
                            resendButton.disabled = false;
                            timer.classList.add('hidden');
                        }
                    }, 1000);
                } else {
                    showErrorMessage(data.message || 'Failed to resend code. Please try again.');
                    resendButton.disabled = false;
                    timer.classList.add('hidden');
                }
            })
            .catch(error => {
                console.error('Error:', error);
                showErrorMessage('An error occurred. Please try again.');
                resendButton.disabled = false;
                timer.classList.add('hidden');
            });
        });
    }
}

/**
 * Initialize password reset form
 * @param {HTMLFormElement} form - The password reset form element
 */
// app/static/js/auth.js (continued)
function initResetPasswordForm(form) {
    form.addEventListener('submit', function(e) {
        e.preventDefault();
        
        // Get form inputs
        const otp = form.querySelector('#otp');
        const newPassword = form.querySelector('#new_password');
        const confirmPassword = form.querySelector('#confirm_password');
        
        // Validate inputs
        if (!otp || !otp.value.trim() || otp.value.length !== 6) {
            showError(otp, 'Please enter a valid verification code.');
            return;
        }
        
        if (!validatePassword(newPassword.value)) {
            showError(newPassword, 'Password must be at least 8 characters with a number, uppercase, and lowercase letter.');
            return;
        }
        
        if (newPassword.value !== confirmPassword.value) {
            showError(confirmPassword, 'Passwords do not match.');
            return;
        }
        
        // Show loading state
        const submitButton = form.querySelector('button[type="submit"]');
        const originalText = submitButton.textContent;
        submitButton.disabled = true;
        submitButton.innerHTML = '<i class="fas fa-spinner fa-spin mr-2"></i> Resetting password...';
        
        // Submit the form
        fetch(form.action, {
            method: 'POST',
            body: new FormData(form),
            headers: {
                'X-Requested-With': 'XMLHttpRequest'
            }
        })
        .then(response => {
            if (response.redirected) {
                window.location.href = response.url;
                return;
            }
            
            return response.json();
        })
        .then(data => {
            if (data && data.success === false) {
                showFormError(form, data.message || 'Password reset failed. Please try again.');
                submitButton.disabled = false;
                submitButton.innerHTML = originalText;
            }
        })
        .catch(error => {
            console.error('Error:', error);
            showFormError(form, 'An error occurred. Please try again.');
            submitButton.disabled = false;
            submitButton.innerHTML = originalText;
        });
    });
}

/**
 * Update password strength meter
 * @param {string} password - The password to check
 * @param {HTMLElement} meter - The password strength meter element
 */
function updatePasswordStrength(password, meter) {
    // Calculate password strength (0-100)
    let strength = 0;
    
    // Add points for length
    if (password.length >= 8) {
        strength += 25;
    }
    
    // Add points for character types
    if (/[A-Z]/.test(password)) {
        strength += 25;
    }
    
    if (/[a-z]/.test(password)) {
        strength += 25;
    }
    
    if (/[0-9]/.test(password)) {
        strength += 25;
    }
    
    // Update meter color based on strength
    let color = '';
    if (strength < 25) {
        color = 'bg-red-500';
    } else if (strength < 50) {
        color = 'bg-orange-500';
    } else if (strength < 75) {
        color = 'bg-yellow-500';
    } else {
        color = 'bg-green-500';
    }
    
    // Remove all color classes and add the appropriate one
    meter.className = 'password-strength-meter mt-1 h-1 rounded-full';
    meter.classList.add(color);
    
    // Set width based on strength
    meter.style.width = strength + '%';
}

/**
 * Show error message for a form input
 * @param {HTMLElement} input - The input element
 * @param {string} message - The error message
 */
function showError(input, message) {
    // Remove any existing error message
    const existingError = input.parentElement.querySelector('.error-message');
    if (existingError) {
        existingError.remove();
    }
    
    // Add error class to input
    input.classList.add('border-red-500');
    
    // Create and insert error message
    const errorElement = document.createElement('div');
    errorElement.className = 'error-message text-red-500 text-xs mt-1';
    errorElement.textContent = message;
    
    // Insert after input or its label for checkboxes
    if (input.type === 'checkbox') {
        input.parentElement.appendChild(errorElement);
    } else {
        input.parentElement.appendChild(errorElement);
    }
    
    // Focus the input
    input.focus();
    
    // Remove error when input changes
    input.addEventListener('input', function() {
        this.classList.remove('border-red-500');
        const error = this.parentElement.querySelector('.error-message');
        if (error) {
            error.remove();
        }
    }, { once: true });
}

/**
 * Show form-level error message
 * @param {HTMLFormElement} form - The form element
 * @param {string} message - The error message
 */
function showFormError(form, message) {
    // Remove any existing form error
    const existingError = form.querySelector('.form-error');
    if (existingError) {
        existingError.remove();
    }
    
    // Create and insert error message at the top of the form
    const errorElement = document.createElement('div');
    errorElement.className = 'form-error bg-red-100 text-red-700 p-3 rounded-lg mb-4';
    errorElement.textContent = message;
    
    form.insertBefore(errorElement, form.firstChild);
}

/**
 * Show success message
 * @param {string} message - The success message
 */
function showSuccessMessage(message) {
    // Create success toast
    const toast = document.createElement('div');
    toast.className = 'fixed top-4 right-4 bg-green-500 text-white p-3 rounded-lg shadow-lg z-50 transform transition-transform duration-300 translate-x-full';
    toast.textContent = message;
    
    // Add to body
    document.body.appendChild(toast);
    
    // Animate in
    setTimeout(() => {
        toast.classList.remove('translate-x-full');
    }, 10);
    
    // Animate out after 3 seconds
    setTimeout(() => {
        toast.classList.add('translate-x-full');
        
        // Remove from DOM after animation
        setTimeout(() => {
            toast.remove();
        }, 300);
    }, 3000);
}

/**
 * Show error message
 * @param {string} message - The error message
 */
function showErrorMessage(message) {
    // Create error toast
    const toast = document.createElement('div');
    toast.className = 'fixed top-4 right-4 bg-red-500 text-white p-3 rounded-lg shadow-lg z-50 transform transition-transform duration-300 translate-x-full';
    toast.textContent = message;
    
    // Add to body
    document.body.appendChild(toast);
    
    // Animate in
    setTimeout(() => {
        toast.classList.remove('translate-x-full');
    }, 10);
    
    // Animate out after 3 seconds
    setTimeout(() => {
        toast.classList.add('translate-x-full');
        
        // Remove from DOM after animation
        setTimeout(() => {
            toast.remove();
        }, 300);
    }, 3000);
}

/**
 * Validate email format
 * @param {string} email - Email to validate
 * @returns {boolean} Whether the email is valid
 */
function validateEmail(email) {
    const re = /^(([^<>()\[\]\\.,;:\s@"]+(\.[^<>()\[\]\\.,;:\s@"]+)*)|(".+"))@((\[[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}])|(([a-zA-Z\-0-9]+\.)+[a-zA-Z]{2,}))$/;
    return re.test(email);
}

/**
 * Validate phone number format
 * @param {string} phone - Phone number to validate
 * @returns {boolean} Whether the phone number is valid
 */
function validatePhone(phone) {
    // Very basic validation - in production, use a more robust solution
    const re = /^\+?[0-9]{8,15}$/;
    return re.test(phone.replace(/[\s\-\(\)]/g, ''));
}

/**
 * Validate password strength
 * @param {string} password - Password to validate
 * @returns {boolean} Whether the password meets requirements
 */
function validatePassword(password) {
    // At least 8 characters with 1 uppercase, 1 lowercase, and 1 number
    const re = /^(?=.*[a-z])(?=.*[A-Z])(?=.*\d).{8,}$/;
    return re.test(password);
}