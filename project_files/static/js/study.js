// Handle session expiry
async function handleSessionExpiry() {
    try {
        await fetch('/logout', {
            method: 'POST'
        });
    } catch (error) {
        console.log('Error killing session on backend:', error);
    }
    
    localStorage.clear();
    sessionStorage.clear();
    
    alert('Your session has expired due to inactivity. Please log in again.');
    window.location.href = '/';
}

// Get session data
async function getSessionData() {
    try {
        const response = await fetch('/check-session');
        const result = await response.json();
        
        if (result.authenticated) {
            document.getElementById('username').textContent = result.username;
        }
    } catch (error) {
        console.log('Error checking session:', error);
        return false;
    }
}

// Logout handler
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

// Logo click handler
document.getElementById('logo').addEventListener('click', function() {
    window.location.href = '/dashboard';
});

const chatMessages = document.getElementById('chatMessages');
const chatInput = document.getElementById('chatInput');
const sendBtn = document.getElementById('sendBtn');
const typingIndicator = document.getElementById('typingIndicator');

let messageCount = 0;

// Fill chat area on page load
function fillChatArea(previous_dialogue) {
    console.log('Previous dialogue length:', previous_dialogue.length);
    if (previous_dialogue.length <= 2) return;

    chatMessages.innerHTML = "";

    previous_dialogue.forEach(message => {
        const [role, content] = Object.entries(message)[0];
        const sender = role === 'HumanMessage' ? 'student' : 'tutor';
        addMessage(content, sender, false);
    });
}

// Auto-resize textarea
chatInput.addEventListener('input', function() {
    this.style.height = 'auto';
    this.style.height = Math.min(this.scrollHeight, 120) + 'px';
    
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

// Initial welcome message
async function compWelcomeUser() {
    try {
        showTypingIndicator();

        const comp_payload = { 
            message: "Initiate a conversation, send initial message"
        };

        const initiateChat = await fetch('/tutoring', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify(comp_payload),
        });

        const data = await initiateChat.json();
        console.log('Response data:', data);

        hideTypingIndicator();
        addMessage(data.message, 'tutor');

        if (data.dialogue) {
            fillChatArea(data.dialogue);
        }

    } catch (error) {
        console.log('Could not initiate dialogue:', error);
        hideTypingIndicator();
    }
}

// Handle user dialogue
async function compDialogue() {
    const message = chatInput.value.trim();
    if (!message) return;

    // Clear empty state if it's the first message
    if (messageCount === 0) {
        chatMessages.innerHTML = '';
    }

    // Add user message
    addMessage(message, 'student');
    
    // Clear input
    chatInput.value = '';
    chatInput.style.height = 'auto';
    sendBtn.disabled = true;

    showTypingIndicator();

    const comp_payload = {
        message: message
    };

    try {
        const response = await fetch('/tutoring', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify(comp_payload),
        });

        if (!response.ok) {
            throw new Error('Network response was not ok');
        }

        const tutor_response = await response.json();

        hideTypingIndicator();
        addMessage(tutor_response.message, 'tutor');

    } catch (error) {
        console.log('Error:', error);
        hideTypingIndicator();
        addMessage('Sorry, I encountered an error. Please try again.', 'tutor');
    }
}

// Add message to chat
function addMessage(text, sender, animate = true) {
    messageCount++;
    
    const messageDiv = document.createElement('div');
    messageDiv.className = `message ${sender}`;
    
    const now = new Date();
    const timeString = now.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
    
    const avatar = sender === 'tutor' ? '🤖' : '👨‍🎓';
    const label = sender === 'tutor' ? 'Tutor' : 'You';
    
    messageDiv.innerHTML = `
        <div class="message-avatar">${avatar}</div>
        <div class="message-content">
            <div class="message-label">${label}</div>
            <div class="message-bubble">${text}</div>
            <div class="message-time">${timeString}</div>
        </div>
    `;
    
    chatMessages.appendChild(messageDiv);
    chatMessages.scrollTop = chatMessages.scrollHeight;
}

// Show typing indicator
function showTypingIndicator() {
    typingIndicator.classList.add('active');
    chatMessages.scrollTop = chatMessages.scrollHeight;
}

// Hide typing indicator
function hideTypingIndicator() {
    typingIndicator.classList.remove('active');
}

// Initialize
sendBtn.disabled = true;

document.addEventListener('DOMContentLoaded', function() {
    getSessionData();
    compWelcomeUser();
});