let serverData = [];
let currentIndex = 0;

document.addEventListener('DOMContentLoaded', function () {
    //setupActivityTracking();
    //checkSession();
    //startSessionMonitoring();
    getSessionData();
    getVocabularyQuestions();
});

///////////////////////////////////////////////
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
////////////////////////////////////////////////////////////////////////
async function getSessionData() {
    try {
        const response = await fetch('/check-session');
        const result = await response.json();
        
        if (result.authenticated) {
            document.getElementById('username').textContent = result.username;
            document.getElementById('compre').textContent = `${result.c_mark}%`;
            document.getElementById('summa').textContent = `${result.s_mark}%`;
            document.getElementById('welcome-title').textContent = `Welcome back, ${result.username}`;
        }
    } catch (error) {
        console.log('Error checking session:', error);
        return false;
    }
}

async function getVocabularyQuestions() {
    try {
        showTypingIndicator();

        const response = await fetch('/get-vocabulary-questions');
        const data = await response.json();

        if (data.message && data.message.length > 0) {
            serverData = data.message;
            hideTypingIndicator();
            displayQuestion(currentIndex); 
        } else {
            throw new Error("No vocabulary questions received");
        }
    } catch (error) {
        console.error("Failed to fetch questions:", error);
        hideTypingIndicator();
        document.getElementById("question-container").textContent = "Failed to load questions.";
    }
}

function displayQuestion(index) {
    const questionContainer = document.getElementById("question-container");
    const answersContainer = document.getElementById("answers-container");
    const resultContainer = document.getElementById("result-container");
    const submitBtn = document.getElementById("submit-btn");
    const nextBtn = document.getElementById("next-btn");

    const current = serverData[index];
    if (!current) return;

    questionContainer.innerText = current.question;
    answersContainer.innerHTML = "";
    resultContainer.innerHTML = "";
    submitBtn.disabled = false;
    nextBtn.style.display = "none";

    updateProgressBar(index, serverData.length);

    current.answers.forEach(answer => {
        const label = document.createElement("label");
        label.innerHTML = `<input type="radio" name="answer" value="${answer}"> ${answer}`;
        answersContainer.appendChild(label);
        answersContainer.appendChild(document.createElement("br"));
    });
}

document.getElementById("submit-btn").addEventListener("click", () => {
    const selected = document.querySelector('input[name="answer"]:checked');
    const resultContainer = document.getElementById("result-container");
    const nextBtn = document.getElementById("next-btn");

    if (!selected) {
        resultContainer.innerText = "Please select an answer.";
        return;
    }

    const selectedValue = selected.value;
    const correctAnswer = serverData[currentIndex].correctAnswer;

    resultContainer.innerHTML = selectedValue === correctAnswer
        ? `<span style="color:green;">Correct! ✅</span>`
        : `<span style="color:red;">Incorrect. ❌ Correct answer: ${correctAnswer}</span>`;

    document.querySelectorAll('input[name="answer"]').forEach(input => input.disabled = true);
    document.getElementById("submit-btn").disabled = true;
    nextBtn.style.display = currentIndex < serverData.length - 1 ? "inline-block" : "none";
});

document.getElementById("next-btn").addEventListener("click", () => {
    currentIndex++;
    if (currentIndex < serverData.length) {
        displayQuestion(currentIndex);
    }
});

function updateProgressBar(currentIndex, total) {
    const progressBar = document.getElementById("progress-bar");
    const percent = ((currentIndex + 1) / total) * 100;
    progressBar.style.width = `${percent}%`;
}

function showTypingIndicator() {
    typingIndicator.style.display = 'flex';
}

function hideTypingIndicator() {
    typingIndicator.style.display = 'none';
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

document.getElementById('logo').addEventListener('click', function() {
    window.location.href = '/dashboard';
});
