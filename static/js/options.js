// Session activity tracking in minutes
let lastActivity = Date.now();

function checkTimer() {
    let timeDifference = Date.now() - lastActivity;
    if(timeDifference >= 480000) { 
        sendSessionWarning();
    }
    if(timeDifference >= 600000) { 
        handleSessionExpiry();
    }
}

function sendSessionWarning() {
    alert("You're to be logged out soon due to inactivity")
}

// Update last activity timestamp
function updateActivity() {
    lastActivity = Date.now();
}


// Setup activity tracking for all user interactions
function setupActivityTracking() {
    // Mouse movements and clicks
    document.addEventListener('mousemove', updateActivity);
    document.addEventListener('click', updateActivity);
    
    // Keyboard activity
    document.addEventListener('keypress', updateActivity);
    document.addEventListener('keydown', updateActivity);
    
    // Page visibility and focus changes
    document.addEventListener('visibilitychange', function() {
        if (!document.hidden) {
            updateActivity();
        }
    });
    window.addEventListener('focus', updateActivity);
    
    // Scroll and form events
    document.addEventListener('scroll', updateActivity);
    document.addEventListener('input', updateActivity);
    
    // Touch events for mobile
    document.addEventListener('touchstart', updateActivity);
    document.addEventListener('touchmove', updateActivity);
}

// Handle session expiry
async function handleSessionExpiry() {
    
    // Kill session on backend should have used get verify session backend first
    try {
        await fetch('/logout', {
            method: 'POST'
        });
    } catch (error) {
        console.log('Error killing session on backend:', error);
    }
    
    // Clear any frontend storage
    localStorage.clear();
    sessionStorage.clear();
    
    // Notify user and redirect
    alert('Your session has expired due to inactivity. Please log in again.');
    window.location.href = '/'; // Redirect to login page
}

setupActivityTracking();
setInterval(checkTimer, 2000);

async function getSessionData() {
    try {
        const response = await fetch('/check-session');
        const result = await response.json();
        
        if (result.authenticated) {
            document.getElementById('username').textContent = result.username;
            document.getElementById('lessons').textContent = `${result.l_completed}`;
            document.getElementById('compre').textContent = `${result.c_mark}%`;
            document.getElementById('summa').textContent = `${result.s_mark}%`;
            document.getElementById('welcome-title').textContent = `Welcome back, ${result.username}`;
        }
    } catch (error) {
        console.log('Error checking session:', error);
        return false;
    }
}

document.getElementById('logoutButton').addEventListener('click', async function () {
        try {
            const response = await fetch('/logout', {
                method: 'POST'
            });

            if (response.ok) {
                alert('Logged out successfully');
                window.location.href = '/';
            } else {
                alert('Logout failed');
            }
        } catch (error) {
            alert('Error logging out');
        }
});


///////////////////////////////Send messsages ////////////////////////////////////////////////////
//send initial welcom message
async function welcomeUser() {
    try {
        const initiateChat = await fetch('/welcome-user');
        const welcomeUserResponse = await initiateChat.json();

        // Append user message to body
        const messagesDiv = document.querySelector('.chat-area');

        if(welcomeUserResponse.message) {
            // Append bot response to body
            messagesDiv.innerHTML += `<div class="message bot-message"><strong>Tutor:</strong> ${welcomeUserResponse.message}</div>`;
            fillChatArea(welcomeUserResponse.dialogue);
            // Scroll to the bottom of the messages
            //messagesDiv.scrollTop = messagesDiv.scrollHeight;
        }
        return null;
    } catch (error) {
        console.log('could not initiate welcome user messages', error);
        return null
    }
}

/////////////////////////////// Fill the chat area on page load///////////////////////////////////////////
function fillChatArea(previous_dialogue) {
    console.log('Previous dialogue length:', previous_dialogue);
    if(previous_dialogue.length <= 2 ) { return}

    const messagesDiv = document.querySelector('.chat-area');

    //empty chat area
    messagesDiv.innerHTML = "";
    previous_dialogue.forEach(message => {
        const [role, content] = Object.entries(message)[0];
        const label = role === 'HumanMessage' ? 'You': 'Tutor';

        messagesDiv.innerHTML += `<div class="message bot-message"><strong>${label}</strong> ${content}</div>`;
    })
}


//when enter is pressed take action
document.getElementById('response-input').addEventListener('keypress', function(e) {
    if (e.key === 'Enter' && !e.shiftKey) {
        e.preventDefault();
        userDialogue();
    }
});

//user welcome dialogue
async function userDialogue() {
    const message = document.getElementById('response-input').value;
    if (!message.trim()) return; // Prevent sending empty messages

    // Append user message to body
    const messagesDiv = document.querySelector('.chat-area');
    messagesDiv.innerHTML += `<div class="message user-message"><strong>You:</strong> ${message}</div>`;

    // Clear input field
    document.getElementById('response-input').value = '';

    try {
        const sum_payload = { 
            message: message
        };

        const welcomeUserDialogue = await fetch('/welcome-dialogue', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify(sum_payload),
        });

        const data = await welcomeUserDialogue.json();
        console.log('Response data:', data);

        // Append bot response to body
        messagesDiv.innerHTML += `<div class="message bot-message"><strong>Tutor:</strong>${data.message}</div>`;
        // Scroll to the bottom of the messages
        messagesDiv.scrollTop = messagesDiv.scrollHeight;

    } catch (error) {
        console.log('could not initiate dialogue');
        return null
    }
}

document.getElementById('responseSubmitBtn').addEventListener('click', userDialogue);

/////////////////Upon clicking practice sections render the relevant pages/////////////////
document.getElementById('comprehension-study').addEventListener('click', function getComprehension() {
    window.location.href = '/get-comprehension'
})

document.getElementById('summary-study').addEventListener('click', function getComprehension() {
    window.location.href = '/get-summary'
})

document.getElementById('vocabulary-study').addEventListener('click', function getComprehension() {
    window.location.href = '/get-vocabulary'
})

// Initialize everything on page load
document.addEventListener('DOMContentLoaded', function() {
    getSessionData();
    welcomeUser();
});