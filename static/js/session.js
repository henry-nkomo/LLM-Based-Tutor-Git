// Session activity tracking in minutes
let lastActivity = Date.now();

function checkTimer(lastActivity) {
    timeDifference = Date.now() - lastActivity;

    if(currentTime >= 480000) {
        sendSessionWarning();
    }
    if(currentTime >= 600000) {
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

export  {updateActivity, setupActivityTracking, handleSessionExpiry, checkTimer};




//****************************************Prev updates************************************************** */

/*
// Session activity tracking in minutes
let lastActivity = Date.now();
let SESSION_TIMEOUT = 10 * 60 * 1000; // Default 10 minutes will be updated from backend
const CHECK_INTERVAL = 2 * 60 * 1000; // Check every 2 minutes
const WARNING_TIME = 2 * 60 * 1000; // Show warning 2 minutes before expiry
const username = '';

// Update last activity timestamp
function updateActivity() {
    lastActivity = Date.now();
    console.log('Activity detected, session timer reset');
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

// Check session status with backend
async function checkSession() {
    try {
        const response = await fetch('/check-session');
        const result = await response.json();
        
        if (result.authenticated) {
            console.log('User is logged in:', result.username);
            username = result.username;
            // Update session timeout from backend
            if (result.session_timeout) {
                SESSION_TIMEOUT = result.session_timeout * 1000;
            }
            return true;
        } else {
            console.log('User is not logged in');
            return false;
        }
    } catch (error) {
        console.log('Error checking session:', error);
        return false;
    }
}

//write username on dashboard etc
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

// Get detailed session status
async function getSessionStatus() {
    try {
        const response = await fetch('/session-status');
        const result = await response.json();
        
        if (result.authenticated) {
            return result;
        }
        return null;
    } catch (error) {
        console.log('Error getting session status:', error);
        return null;
    }
}

// Extend session on backend
async function extendSession() {
    try {
        const response = await fetch('/extend-session', {
            method: 'POST'
        });
        
        if (response.ok) {
            console.log('Session extended on backend');
            return true; //might use to catch an error
        }
    } catch (error) {
        console.log('Error extending session:', error);
    }
    return false; //might use to catch an error
}

// Check for frontend session timeout
function checkFrontendTimeout() {
    const timeSinceLastActivity = Date.now() - lastActivity;
    return timeSinceLastActivity >= SESSION_TIMEOUT;
}

// Handle session expiry
async function handleSessionExpiry() {
    console.log('Session expired due to inactivity');
    
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

//might remove////////////////////////////////////////////////
// Show session warning before expiry
async function checkSessionWarning() {
    const sessionStatus = await getSessionStatus();
    
    if (!sessionStatus || !sessionStatus.authenticated) {
        return;
    }
    
    // Check if session expires soon according to backend
    if (sessionStatus.expires_soon) {
        //const minutesLeft = Math.ceil(sessionStatus.time_remaining_seconds / 60);
        const minutesLeft = Math.ceil(sessionStatus.time_remaining_seconds );
        const extend = confirm(`Your session will expire in ${minutesLeft} minutes due to inactivity. Do you want to extend it?`);
        
        if (extend) {
            updateActivity(); // Reset frontend timer
            await extendSession(); // Extend backend session
            alert('Session extended successfully!');
        }
    }
}

// Main session monitoring function
async function monitorSession() {
    // Check frontend timeout
    if (checkFrontendTimeout()) {
        await handleSessionExpiry();
        return;
    }
    
    // Check backend session
    const isValid = await checkSession();
    if (!isValid) {
        await handleSessionExpiry();
        return;
    }
    
    // If user has been active, extend backend session
    const timeSinceLastActivity = Date.now() - lastActivity;
    if (timeSinceLastActivity < CHECK_INTERVAL) {
        await extendSession();
    }
    
    // Check for session warning
    await checkSessionWarning();
}

// Start session monitoring
function startSessionMonitoring() {
    // Monitor session every 5 minutes
    setInterval(monitorSession, CHECK_INTERVAL);
    
    // Check for warnings every minute
    setInterval(checkSessionWarning, 60 * 1000);
}


export  {updateActivity, setupActivityTracking, checkSession, getSessionStatus, extendSession, checkFrontendTimeout, handleSessionExpiry, 
         checkSessionWarning, monitorSession, startSessionMonitoring, getSessionData};*/