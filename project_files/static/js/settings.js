document.addEventListener('DOMContentLoaded', async function() {
    try{
        const userData = await fetch('/check-session');
        const result = await userData.json();

        if (result.authenticated) {
            console.log('User data found:', result); //for debugging
            let firstLetter = result.username.charAt(0).toUpperCase();

            document.getElementById('username').textContent = `${result.username}`;
            document.getElementById('second_username').textContent = `${result.username}`;
            document.getElementById('profile-card').textContent = `${firstLetter}`;;
            document.getElementById('name-input').value = result.username;
            document.getElementById('email-input').value = result.user_email;
            document.getElementById('lessons').textContent = `${result.l_completed}`;
            document.getElementById('compre').textContent = `${result.c_mark}%`;
            document.getElementById('summa').textContent = `${result.s_mark}%`;
        }
    } catch (error) {
        console.log('No user data found', error);
    }
});

function toggleEdit() {
    const nameInput = document.getElementById('name-input');
    const emailInput = document.getElementById('email-input');
    const editButton = document.getElementById('btn-primary');
    const text = document.getElementById('edit-error');
    //const errorMsg = document.getElementById("email-error");

    // Toggle readonly attribute
    if (nameInput.hasAttribute('readonly') && emailInput.hasAttribute('readonly')) {
        nameInput.removeAttribute('readonly');
        //emailInput.removeAttribute('readonly');
        editButton.textContent = 'Save'; // Change button text
    } else {
        //function to send data to backend
        nameInput.setAttribute('readonly', true);
        //emailInput.setAttribute('readonly', true);
        editButton.textContent = 'Edit Profile Data'; // Change button text

        /*emailInput.addEventListener("input", () => {
        const value = emailInput.value;
        if (!value.includes("@")) {
            errorMsg.style.display = "inline";
            return;
        } else {
                errorMsg.style.display = "none";
                }
            });*/

        const updateDetails = async () => {
            try {   
                const response = await fetch('/edit-profile', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json'
                    },
                    body: JSON.stringify({
                        username: nameInput.value,
                        email: emailInput.value
                    })
                });

                const result = await response.json();
                console.log('Response status:', response.status); // Log status code
                console.log('Profile update response:', result); // Log response body

                if (!response.ok) {
                    text.textContent = `${'failed to update profile'}`;
                    text.style.cssText = "color: red;";

                } 
            } catch (error) {
                alert('Error updating profile: ' + error.message);
            }
        };

        updateDetails();

        // Send updated data to backend
        location.reload(); // Reload the page to reflect changes
    }
}

function openDeleteModal() {
    const modal = document.getElementById('deleteModal');
    modal.classList.add('active');
    document.body.style.overflow = 'hidden';
}
        
function closeDeleteModal() {
    const modal = document.getElementById('deleteModal');
    modal.classList.remove('active');
    document.body.style.overflow = 'auto';
}

async function confirmDelete() {
    try{
        const delete_account = await fetch('/delete-account')
        const delete_account_data = await delete_account.json()

        if (delete_account_data.success) {
            window.location.href = '/'; // Redirect to homepage or login page
            location.reload();
        }
    } catch (error) {
        alert('Error deleting account:', error);
    }
    closeDeleteModal();
}

// Close modal when clicking outside
document.getElementById('deleteModal').addEventListener('click', function(e) {
    if (e.target === this) {
        closeDeleteModal();
    }
});

// Close modal on escape key
document.addEventListener('keydown', function(e) {
    if (e.key === 'Escape') {
        closeDeleteModal();
    }
});

document.getElementById('logoutButton').addEventListener('click', async function () {
        try {
            const response = await fetch('/logout', {
                method: 'POST'
            });

            if (response.ok) {
                window.location.href = '/';
            } else {
                alert('Logout failed');
            }
        } catch (error) {
            alert('Error logging out');
        }
});

document.getElementById('logo').addEventListener('click', function() {
    window.location.href = '/dashboard';
});

