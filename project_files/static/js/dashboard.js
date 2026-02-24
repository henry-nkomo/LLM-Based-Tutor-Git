// Sample knowledge state data - replace with actual data from your backend
let knowledgeStateData = {};

async function getSessionData() {
    try {
        const response = await fetch('/check-session');
        const result = await response.json();
        
        if (result.authenticated) {
            document.getElementById('username').textContent = result.username;
            document.getElementById('welcome-title').textContent = `Welcome back, ${result.username}`;
            
            // Update knowledge state data if available from backend
            if (result.knowledge_state) {
                knowledgeStateData = result.knowledge_state;
                console.log('Knowledge state loaded:', knowledgeStateData);
                
                initializeRadarChart();
            }
        }
    } catch (error) {
        console.log('Error checking session:', error);
        return false;
    }
}

let radarChartInstance = null;

// Get color based on proficiency level
function getColorForProficiency(value) {
    if (value >= 70) return '#10b981'; // Green - Proficient
    if (value >= 50) return '#f59e0b'; // Orange - Developing
    return '#ef4444'; // Red - Needs Work
}

// Initialize radar chart
function initializeRadarChart() {
    try {
        const ctx = document.getElementById('radarChart');
        if (!ctx) {
            console.error('Canvas element not found');
            return;
        }

        // Destroy existing chart if it exists
        if (radarChartInstance) {
            radarChartInstance.destroy();
        }
        
        const labels = Object.keys(knowledgeStateData);
        const values = Object.values(knowledgeStateData);
        
        // Generate colors for each point based on proficiency
        const pointColors = values.map(value => getColorForProficiency(value));
        const pointBorderColors = values.map(value => getColorForProficiency(value));

        radarChartInstance = new Chart(ctx, {
            type: 'radar',
            data: {
                labels: labels,
                datasets: [{
                    label: 'Current Proficiency (%)',
                    data: values,
                    fill: true,
                    backgroundColor: 'rgba(102, 126, 234, 0.1)',
                    borderColor: 'rgba(102, 126, 234, 0.6)',
                    borderWidth: 2,
                    pointBackgroundColor: pointColors,
                    pointBorderColor: '#fff',
                    pointHoverBackgroundColor: '#fff',
                    pointHoverBorderColor: pointBorderColors,
                    pointRadius: 6,
                    pointHoverRadius: 8,
                    pointBorderWidth: 2
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: true,
                scales: {
                    r: {
                        beginAtZero: true,
                        max: 100,
                        min: 0,
                        ticks: {
                            stepSize: 20,
                            callback: function(value) {
                                return value + '%';
                            },
                            font: {
                                size: 11
                            }
                        },
                        pointLabels: {
                            font: {
                                size: 13,
                                weight: '600'
                            },
                            color: '#2d3748'
                        },
                        grid: {
                            color: 'rgba(0, 0, 0, 0.1)'
                        },
                        angleLines: {
                            color: 'rgba(0, 0, 0, 0.1)'
                        }
                    }
                },
                plugins: {
                    legend: {
                        display: false
                    },
                    tooltip: {
                        backgroundColor: 'rgba(0, 0, 0, 0.8)',
                        padding: 12,
                        titleFont: {
                            size: 14,
                            weight: 'bold'
                        },
                        bodyFont: {
                            size: 13
                        },
                        callbacks: {
                            label: function(context) {
                                const value = context.parsed.r;
                                const level = value >= 70 ? 'Proficient' : 
                                                value >= 50 ? 'Developing' : 
                                                'Needs Work';
                                return [
                                    `Proficiency: ${value}%`,
                                    `Level: ${level}`
                                ];
                            }
                        }
                    }
                }
            }
        });
        
        console.log('Radar chart initialized successfully');
    } catch (error) {
        console.error('Error initializing radar chart:', error);
    }
}

document.getElementById('settings').addEventListener('click', function() {
    window.location.href = '/settings';
});

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

function fillChatArea(previous_dialogue) {
    console.log('Previous dialogue length:', previous_dialogue);
    if(previous_dialogue.length <= 2) { return }

    const messagesDiv = document.querySelector('.chat-area');
    if (!messagesDiv) {
        console.log('Chat area not found, skipping...');
        return;
    }
    
    messagesDiv.innerHTML = "";
    
    previous_dialogue.forEach(message => {
        const [role, content] = Object.entries(message)[0];
        const label = role === 'HumanMessage' ? 'You': 'Tutor';
        messagesDiv.innerHTML += `<div class="message bot-message"><strong>${label}</strong> ${content}</div>`;
    });
}

document.getElementById('response-input').addEventListener('keypress', function(e) {
    if (e.key === 'Enter' && !e.shiftKey) {
        e.preventDefault();
        userDialogue();
    }
});

async function welcomeUser() {
    const messagesDiv = document.querySelector('.chat-area');
    if (!messagesDiv) {
        console.log('Chat area not found, skipping welcome message...');
        return;
    }

    try {
        const sum_payload = { 
            message: ""  // ✅ CHANGED: Empty string instead of "Initiate a conversation, send initial message"
        };

        const initiateChat = await fetch('/dashboard_dialogue', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify(sum_payload),
        });

        const data = await initiateChat.json();
        console.log('Response data:', data);

        messagesDiv.innerHTML += `<div class="message bot-message"><strong>Tutor:</strong> ${data.message}</div>`;
        if (data.dialogue) {
            fillChatArea(data.dialogue);
        }

        messagesDiv.scrollTop = messagesDiv.scrollHeight;

    } catch (error) {
        console.log('could not initiate dialogue:', error);
        return null;
    }
}

async function userDialogue() {
    const messageInput = document.getElementById('response-input');
    if (!messageInput) {
        console.log('Response input not found, skipping...');
        return;
    }
    
    const message = messageInput.value;
    if (!message.trim()) return;

    const messagesDiv = document.querySelector('.chat-area');
    if (!messagesDiv) {
        console.log('Chat area not found, skipping...');
        return;
    }
    
    messagesDiv.innerHTML += `<div class="message user-message"><strong>You:</strong> ${message}</div>`;

    messageInput.value = '';

    try {
        const sum_payload = { 
            message: message
        };

        const welcomeUserDialogue = await fetch('/dashboard_dialogue', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify(sum_payload),
        });

        const data = await welcomeUserDialogue.json();
        console.log('Response data:', data);

        messagesDiv.innerHTML += `<div class="message bot-message"><strong>Tutor:</strong>${data.message}</div>`;
        messagesDiv.scrollTop = messagesDiv.scrollHeight;

    } catch (error) {
        console.log('could not initiate dialogue:', error);
        return null;
    }
}

document.getElementById('responseSubmitBtn')?.addEventListener('click', userDialogue);

// Study button click handler
document.getElementById('study-btn').addEventListener('click', function() {
    window.location.href = '/study';
});

// Initialize everything on page load
document.addEventListener('DOMContentLoaded', function() {
    
    // Initialize radar chart first (most important)
    setTimeout(() => {
        initializeRadarChart();
    }, 100);
    
    // Then get session data
    getSessionData();
    
    // Only call welcomeUser if chat area exists
    if (document.querySelector('.chat-area')) {
        welcomeUser();
    } else {
        console.log('Chat area not found, skipping welcome dialogue');
    }
    
    // Set up event listeners only if elements exist
    const responseInput = document.getElementById('response-input');
    if (responseInput) {
        responseInput.addEventListener('keypress', function(e) {
            if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                userDialogue();
            }
        });
    }
});