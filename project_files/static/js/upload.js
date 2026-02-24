function showSignupModal() {
    document.getElementById('signupModal').classList.add('active');
}

function hideSignupModal() {
    document.getElementById('signupModal').classList.remove('active');
}

function checkPasswordMatch() {
    const password = document.getElementById('newPassword').value;
    const confirmPassword = document.getElementById('confirmPassword').value;
    const matchIndicator = document.getElementById('passwordMatch');
    const submitBtn = document.getElementById('signupSubmitBtn');

    if (confirmPassword === '') {
        matchIndicator.textContent = '';
        matchIndicator.className = 'password-match';
        return;
    }

    if (password === confirmPassword) {
        matchIndicator.textContent = '✓ Passwords match';
        matchIndicator.className = 'password-match match';
        submitBtn.disabled = false;
    } else {
        matchIndicator.textContent = '✗ Passwords do not match';
        matchIndicator.className = 'password-match no-match';
        submitBtn.disabled = true;
    }
}

// Close modal when clicking outside
document.getElementById('signupModal').addEventListener('click', function(e) {
    if (e.target === this) {
        hideSignupModal();
    }
});




/*****starts here */
// Handle login form submission
document.getElementById('loginForm').addEventListener('submit', async function(e) {
    e.preventDefault();
    
    // Prevent double submissions
    const submitButton = this.querySelector('button[type="submit"]');
    if (submitButton.disabled) return;

    const email = document.getElementById('username').value;
    const password = document.getElementById('password').value;
    
    if (!email) {
        alert('Please enter your name or email');
        return;
    }

    if(!password) {
        alert('Please enter your password');
        return;
    }
    
    // Disable button during request
    submitButton.disabled = true;
    submitButton.textContent = 'Logging in...';
    
    try {
        const response = await fetch('/login', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ email: email, password: password })
        });

        const result = await response.json();
        
        if (response.ok) {
            // Redirect to dashboard 
            window.location.href = '/dashboard'; 
        } else {
            console.log(result.error);
        }
        
    } catch (error) {
        console.log('We faiced the following error', error);
    } finally {
        // Re-enable button
        submitButton.disabled = false;
        submitButton.textContent = 'Login';
    }
});

// Handle signup form submission
document.getElementById('signupForm').addEventListener('submit', async function(e) {
    e.preventDefault();
    
    // Prevent double submissions
    const submitButton = this.querySelector('button[type="submit"]');
    if (submitButton.disabled) return;
    
    const name = document.getElementById('fullName').value;
    const email = document.getElementById('email').value;
    const password = document.getElementById('newPassword').value;
    const confirmPassword = document.getElementById('confirmPassword').value;
    
    if (password !== confirmPassword) {
        alert('Passwords do not match!');
        return;
    }
    
    if (name && email && password) {
        // Disable button during request
        submitButton.disabled = true;
        submitButton.textContent = 'Creating Account...';
        
        try {
            const response = await fetch('/signup', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({ username: name, email: email, password: password })
            });

            const result = await response.json();
            if (response.ok) {
                alert('Account created successfully! You can now log in.');
                hideSignupModal();
            } else {
                alert(result.error);
            }
        } finally {
            // Re-enable button
            submitButton.disabled = false;
            submitButton.textContent = 'Sign Up'; 
        }
    }
});

// Escape key to close modal
document.addEventListener('keydown', function(e) {
    if (e.key === 'Escape') {
        hideSignupModal();
    }
});




