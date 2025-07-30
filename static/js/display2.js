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
/////////////////////////////////////////////////////////////

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

document.getElementById('logo').addEventListener('click', function() {
    window.location.href = '/dashboard';
});

const chatMessages = document.getElementById('chatMessages');
const chatInput = document.getElementById('chatInput');
const sendBtn = document.getElementById('sendBtn');
const typingIndicator = document.getElementById('typingIndicator');

let messageCount = 0;

//Initiate communication with user by sending initial welcome message
async function sumWelcomeUser() {
    
    try {
        showTypingIndicator();
        
        const compInitiateChat = await fetch('/sum-welcome-dialogue');
        const compTutorResponse = await compInitiateChat.json();
        
        if(compTutorResponse.message) {
            addMessage(compTutorResponse.message, 'ai');
            console.log(compTutorResponse.message);
            hideTypingIndicator();
        }
        if(compTutorResponse.dialogue) {
            fillChatArea(compTutorResponse.dialogue);
            hideTypingIndicator();
        }
        return null;
    } catch (error) {
        console.log('could not initiate Summary dialogue ', error);
        hideTypingIndicator();
        return null
    }
}

async function getSessionData() {
    try {
        const response = await fetch('/check-session');
        const result = await response.json();
        
        if (result.authenticated) {
            document.getElementById('username').textContent = result.username;
            document.getElementById('welcome-title').textContent = `Welcome back, ${result.username}`;
        }
    } catch (error) {
        console.log('Error checking session:', error);
        return false;
    }
}

/////////////////////////////// Fill the chat area on page load///////////////////////////////////////////
function fillChatArea(previous_dialogue) {
    console.log('Previous dialogue length:', previous_dialogue);
    if(previous_dialogue.length <= 2 ) { return}

    //empty chat area
    chatMessages.innerHTML = "";

    
    previous_dialogue.forEach(message => {
        const [role, content] = Object.entries(message)[0];
        const label = role === 'HumanMessage' ? 'user': 'ai';

        const messageDiv = document.createElement('div');

        messageDiv.className = `message ${label}`;
    
        const now = new Date();
        const timeString = now.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });

        messageDiv.innerHTML = `
        <div class="message-bubble">${content}</div>
        <div class="message-time">${timeString}</div>
        `;

        chatMessages.appendChild(messageDiv);
        chatMessages.scrollTop = chatMessages.scrollHeight;
        messageCount++;
    })
}



// Auto-resize textarea
chatInput.addEventListener('input', function() {
    this.style.height = 'auto';
    this.style.height = Math.min(this.scrollHeight, 100) + 'px';
    
    // Enable/disable send button
    sendBtn.disabled = this.value.trim() === '';
});

// Send message on Enter (but not Shift+Enter)
chatInput.addEventListener('keypress', function(e) {
    if (e.key === 'Enter' && !e.shiftKey) {
        e.preventDefault();
        compDialogue();
    }
});

// Send button click
sendBtn.addEventListener('click', compDialogue);

async function compDialogue() {
    const message = chatInput.value.trim();
    if (!message) return;

    // Clear empty state if it's the first message
    if (messageCount === 0) {
        chatMessages.innerHTML = '';
    }

    // Add user message
    addMessage(message, 'user');
    
    // Clear input
    chatInput.value = '';
    chatInput.style.height = 'auto';
    sendBtn.disabled = true;

    showTypingIndicator();

    const comp_payload = {
        message: message
    };

    try {
        const response = await fetch('/sum-dialogue', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify(comp_payload),
        });

        if(!response.ok) {
            throw new Error('Network response was not ok');
        }

        const tutor_response = await response.json();

        hideTypingIndicator();
        addMessage(tutor_response.message, 'ai');

    } catch (error) {
        console.log('Error:', error);
        hideTypingIndicator();
    }
}

function addMessage(text, sender) {
    messageCount++;
    
    const messageDiv = document.createElement('div');
    messageDiv.className = `message ${sender}`;
    
    const now = new Date();
    const timeString = now.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
    
    messageDiv.innerHTML = `
        <div class="message-bubble">${text}</div>
        <div class="message-time">${timeString}</div>
    `;
    
    chatMessages.appendChild(messageDiv);
    chatMessages.scrollTop = chatMessages.scrollHeight; //auto scroll to the bottom
}

function showTypingIndicator() {
    typingIndicator.style.display = 'flex';
    chatMessages.scrollTop = chatMessages.scrollHeight;
}

function hideTypingIndicator() {
    typingIndicator.style.display = 'none';
}

// Initialize
sendBtn.disabled = true;

document.addEventListener('DOMContentLoaded', function(){
    getSessionData();
    sumWelcomeUser();
});