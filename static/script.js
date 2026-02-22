const chatMessages = document.getElementById('chat-messages');
const userInput = document.getElementById('user-input');
const sendBtn = document.getElementById('send-btn');

// Auto-resize textarea
userInput.addEventListener('input', function() {
    this.style.height = 'auto';
    this.style.height = (this.scrollHeight) + 'px';
    if(this.value.trim() === '') {
        this.style.height = 'auto';
    }
});

// Handle enter key to send
userInput.addEventListener('keydown', function(e) {
    if (e.key === 'Enter' && !e.shiftKey) {
        e.preventDefault();
        sendMessage();
    }
});

sendBtn.addEventListener('click', sendMessage);

async function sendMessage() {
    const message = userInput.value.trim();
    if (!message) return;

    // Reset textarea
    userInput.value = '';
    userInput.style.height = 'auto';
    userInput.focus();

    // Add user message to UI
    appendMessage(message, 'user');

    // Add loading indicator
    const loadingId = addLoadingIndicator();

    try {
        const response = await fetch('/api/chat', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ message: message })
        });

        const data = await response.json();
        
        // Remove loading indicator
        document.getElementById(loadingId).remove();

        if (response.ok) {
            appendMessage(data.response, 'bot');
        } else {
            appendMessage("ขออภัย เกิดข้อผิดพลาดในการเชื่อมต่อเซิร์ฟเวอร์", 'bot');
            console.error(data.error);
        }
    } catch (error) {
        document.getElementById(loadingId).remove();
        appendMessage("ขออภัย ไม่สามารถเชื่อมต่อกับเซิร์ฟเวอร์ได้", 'bot');
        console.error('Error:', error);
    }
}

function appendMessage(content, sender) {
    const messageDiv = document.createElement('div');
    messageDiv.className = `message ${sender}-message`;
    
    const iconClass = sender === 'user' ? 'fa-user' : 'fa-robot';
    
    // Very basic markdown parsing for bold text
    const formattedContent = content.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
                                    .replace(/\*(.*?)\*/g, '<em>$1</em>');

    messageDiv.innerHTML = `
        <div class="message-avatar">
            <i class="fa-solid ${iconClass}"></i>
        </div>
        <div class="message-bubble">${formattedContent}</div>
    `;
    
    chatMessages.appendChild(messageDiv);
    scrollToBottom();
}

function addLoadingIndicator() {
    const id = 'loading-' + Date.now();
    const loadingDiv = document.createElement('div');
    loadingDiv.className = 'message bot-message fade-in';
    loadingDiv.id = id;
    
    loadingDiv.innerHTML = `
        <div class="message-avatar">
            <i class="fa-solid fa-robot"></i>
        </div>
        <div class="message-bubble">
            <div class="typing-indicator">
                <div class="dot"></div>
                <div class="dot"></div>
                <div class="dot"></div>
            </div>
        </div>
    `;
    
    chatMessages.appendChild(loadingDiv);
    scrollToBottom();
    return id;
}

function scrollToBottom() {
    chatMessages.scrollTop = chatMessages.scrollHeight;
}

function clearChat() {
    if(confirm("คุณต้องการล้างประวัติการสนทนาทั้งหมดหรือไม่?")) {
        // Keep only the first welcome message
        const welcomeMessage = chatMessages.firstElementChild;
        chatMessages.innerHTML = '';
        if (welcomeMessage) {
            chatMessages.appendChild(welcomeMessage);
        }
    }
}

function toggleTheme() {
    const body = document.body;
    const currentTheme = body.getAttribute('data-theme');
    const newTheme = currentTheme === 'light' ? 'dark' : 'light'; // dark is default when attribute is removed/null
    
    if (newTheme === 'light') {
        body.setAttribute('data-theme', 'light');
    } else {
        body.removeAttribute('data-theme'); // default to dark
    }
    
    const icon = document.querySelector('.action-btn[title="สลับโหมด"] i');
    if (newTheme === 'light') {
        icon.className = 'fa-solid fa-moon';
    } else {
        icon.className = 'fa-solid fa-sun';
    }
}
