
        // File type to icon mapping
        const fileIcons = {
            'pdf': 'far fa-file-pdf',
            'doc': 'far fa-file-word',
            'docx': 'far fa-file-word',
            'xls': 'far fa-file-excel',
            'xlsx': 'far fa-file-excel',
            'ppt': 'far fa-file-powerpoint',
            'pptx': 'far fa-file-powerpoint',
            'zip': 'far fa-file-archive',
            'rar': 'far fa-file-archive',
            'txt': 'far fa-file-alt',
            'csv': 'far fa-file-csv',
            'jpg': 'far fa-file-image',
            'jpeg': 'far fa-file-image',
            'png': 'far fa-file-image',
            'gif': 'far fa-file-image',
            'default': 'far fa-file'
        };
        
        // Format file size
        function formatFileSize(bytes) {
            if (bytes === 0) return '0 Bytes';
            const k = 1024;
            const sizes = ['Bytes', 'KB', 'MB', 'GB'];
            const i = Math.floor(Math.log(bytes) / Math.log(k));
            return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
        }
        
        // Get file icon class
        function getFileIcon(filename) {
            const ext = filename.split('.').pop().toLowerCase();
            return fileIcons[ext] || fileIcons['default'];
        }
        
        
        document.addEventListener('DOMContentLoaded', function() {
            const contactId = window.USER_CHAT_CONTACT_ID;
            const contactName = window.USER_CHAT_CONTACT_NAME || 'Support Team';
            const ticketIds = Array.isArray(window.USER_CHAT_TICKET_IDS) ? window.USER_CHAT_TICKET_IDS : [];
            const ticketAdmins = window.USER_CHAT_TICKET_ADMINS || {};
            let currentTicketId = window.USER_CHAT_TICKET_ID || (ticketIds[0] || '');
            
            // Debug logging
            console.log('Chat Debug Info:');
            console.log('contactId:', contactId);
            console.log('contactName:', contactName);
            console.log('ticketIds:', ticketIds);
            console.log('ticketAdmins:', ticketAdmins);
            console.log('currentTicketId:', currentTicketId);

            if (contactId) {
                const conversationListEl = document.getElementById('conversationList');
                const chatMessagesEl = document.getElementById('chatMessages');
                const inputEl = document.querySelector('.chat-input');
                const sendBtn = document.getElementById('sendMessage');

                if (!conversationListEl || !chatMessagesEl || !inputEl || !sendBtn) {
                    return;
                }

                function getCookie(name) {
                    let cookieValue = null;
                    if (document.cookie && document.cookie !== '') {
                        const cookies = document.cookie.split(';');
                        for (let i = 0; i < cookies.length; i++) {
                            const cookie = cookies[i].trim();
                            if (cookie.substring(0, name.length + 1) === (name + '=')) {
                                cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                                break;
                            }
                        }
                    }
                    return cookieValue;
                }

                function renderTicketConversations() {
                    if (!ticketIds.length) {
                        conversationListEl.innerHTML = `
                            <div class="empty-state">
                                <i class="far fa-comment-dots"></i>
                                <p>No tickets found.</p>
                                <p class="text-muted">Create a ticket to start chat.</p>
                            </div>`;
                        return;
                    }

                    conversationListEl.innerHTML = ticketIds.map(tid => {
                        const activeClass = (tid === currentTicketId) ? ' active' : '';
                        // Get the admin for this specific ticket
                        const adminInfo = ticketAdmins[tid];
                        console.log(`Ticket ${tid} admin info:`, adminInfo);
                        const adminName = adminInfo ? 
                            (adminInfo.get_full_name || adminInfo.username || 'Support Team') : 
                            contactName;
                        
                        console.log(`Ticket ${tid} admin name:`, adminName);
                        
                        return `
                            <div class="conversation${activeClass}" data-ticket-id="${tid}" data-admin-id="${adminInfo ? adminInfo.id : contactId}">
                                <div class="conversation-header">
                                    <span class="conversation-name">${adminName}</span>
                                    <span class="conversation-time"></span>
                                </div>
                                <div class="conversation-preview">Ticket: ${tid}</div>
                            </div>`;
                    }).join('');

                    conversationListEl.querySelectorAll('.conversation').forEach(el => {
                        el.addEventListener('click', () => {
                            const tid = el.getAttribute('data-ticket-id') || '';
                            const adminId = el.getAttribute('data-admin-id') || '';
                            if (!tid || tid === currentTicketId) return;
                            currentTicketId = tid;
                            window.USER_CHAT_TICKET_ID = tid;
                            
                            // Update current admin when switching tickets
                            const adminInfo = ticketAdmins[tid];
                            if (adminInfo) {
                                window.USER_CHAT_CONTACT_ID = adminInfo.id;
                                window.USER_CHAT_CONTACT_NAME = adminInfo.get_full_name || adminInfo.username || 'Support Team';
                            }
                            
                            renderTicketConversations();
                            loadMessages();
                        });
                    });
                }

                function renderMessages(results) {
                    if (!results || !results.length) {
                        chatMessagesEl.innerHTML = `
                            <div class="empty-state">
                                <i class="far fa-comments"></i>
                                <h3>Welcome to TicketHub Support</h3>
                                <p>Start a conversation with our support team. We're here to help!</p>
                            </div>`;
                        return;
                    }

                    chatMessagesEl.innerHTML = results.map(m => {
                        let messageContent = '';
                        
                        // Add text content if present
                        if (m.text) {
                            messageContent += `<div>${m.text}</div>`;
                        }
                        
                        // Add attachments if present
                        if (m.attachments && m.attachments.length > 0) {
                            messageContent += '<div class="message-attachments">';
                            m.attachments.forEach(att => {
                                const iconClass = getFileIcon(att.filename);
                                messageContent += `
                                    <div class="attachment-item">
                                        <i class="${iconClass}"></i>
                                        <div class="attachment-info">
                                            <span class="attachment-filename">${att.filename}</span>
                                            <span class="attachment-size">${formatFileSize(att.filesize)}</span>
                                        </div>
                                        <a href="${att.url}" target="_blank" class="attachment-download">
                                            <i class="fas fa-download"></i>
                                        </a>
                                    </div>
                                `;
                            });
                            messageContent += '</div>';
                        }
                        
                        // Generate status ticks based on message direction and read status
                        let statusTicks = '';
                        if (m.direction === 'sent') {
                            // WhatsApp-style status for sent messages
                            if (m.is_read) {
                                statusTicks = '<span class="message-status"><span class="tick double read">✓✓</span></span>';
                            } else {
                                statusTicks = '<span class="message-status"><span class="tick double delivered">✓✓</span></span>';
                            }
                        }
                        
                        return `
                            <div class="message ${m.direction === 'sent' ? 'sent' : 'received'}" data-message-id="${m.id || ''}">
                                ${messageContent}
                                <div class="message-time">
                                    ${m.time}
                                    ${statusTicks}
                                </div>
                            </div>
                        `;
                    }).join('');

                    chatMessagesEl.scrollTop = chatMessagesEl.scrollHeight;
                }

                function loadMessages() {
                    if (!currentTicketId) {
                        chatMessagesEl.innerHTML = '<div class="empty-state"><p>Select a ticket to view messages.</p></div>';
                        return;
                    }
                    chatMessagesEl.innerHTML = '<div class="empty-state"><p>Loading messages...</p></div>';
                    fetch(`/api/chat/messages/?contact_id=${contactId}&ticket_id=${encodeURIComponent(currentTicketId)}`, { credentials: 'same-origin' })
                        .then(async (res) => {
                            if (res.ok) return res.json();
                            let detail = '';
                            try {
                                const data = await res.json();
                                detail = data.detail || JSON.stringify(data);
                            } catch (_) {
                                try {
                                    detail = (await res.text()).slice(0, 200);
                                } catch (_) {
                                    detail = '';
                                }
                            }
                            throw new Error(`HTTP ${res.status}${detail ? `: ${detail}` : ''}`);
                        })
                        .then(data => {
                            renderMessages(data.results || []);
                        })
                        .catch((err) => {
                            console.error('Failed to load messages', err);
                            chatMessagesEl.innerHTML = `<div class="empty-state"><p>Failed to load messages.</p><small class="text-muted">${(err && err.message) ? err.message : ''}</small></div>`;
                        });
                }

                function getTextFromContentEditable(el) {
                    const text = (el.innerText || '').trim();
                    return text;
                }

                function clearContentEditable(el) {
                    el.textContent = '';
                    const ev = new Event('input', { bubbles: true });
                    el.dispatchEvent(ev);
                }

                sendBtn.addEventListener('click', () => {
                    const text = getTextFromContentEditable(inputEl);
                    if (!text && !hasAttachedFiles()) return;
                    if (!currentTicketId) return;

                    const csrftoken = getCookie('csrftoken') || '';
                    
                    // Show message immediately with "sending" status
                    const tempMessageId = 'temp-' + Date.now();
                    const tempMessageHtml = `
                        <div class="message sent" data-message-id="${tempMessageId}">
                            ${text ? `<div>${text}</div>` : ''}
                            ${hasAttachedFiles() ? '<div class="message-attachments">Uploading files...</div>' : ''}
                            <div class="message-time">
                                ${new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                                <span class="message-status"><span class="tick sending">✓</span></span>
                            </div>
                        </div>
                    `;
                    
                    chatMessagesEl.insertAdjacentHTML('beforeend', tempMessageHtml);
                    chatMessagesEl.scrollTop = chatMessagesEl.scrollHeight;
                    
                    // Create FormData for file upload
                    const formData = new FormData();
                    formData.append('contact_id', contactId);
                    formData.append('ticket_id', currentTicketId);
                    if (text) {
                        formData.append('text', text);
                    }
                    
                    // Add attached files - FIXED VERSION
                    const filePreviews = document.querySelectorAll('.file-preview');
                    console.log('Found file previews:', filePreviews.length);
                    filePreviews.forEach((preview, index) => {
                        const file = preview.storedFile; // Get stored file object
                        console.log(`File ${index}:`, file ? file.name : 'null', file ? file.size : 'null');
                        if (file) {
                            formData.append('files', file);
                        }
                    });
                    
                    // Update status to "sending" with double tick
                    setTimeout(() => {
                        const tempMsg = document.querySelector(`[data-message-id="${tempMessageId}"] .message-status`);
                        if (tempMsg) {
                            tempMsg.innerHTML = '<span class="tick double sending">✓✓</span>';
                        }
                    }, 500);
                    
                    fetch('/api/chat/messages/', {
                        method: 'POST',
                        credentials: 'same-origin',
                        headers: {
                            'X-CSRFToken': csrftoken,
                            // Don't set Content-Type header when using FormData
                        },
                        body: formData,
                    })
                        .then(res => {
                            console.log('Response status:', res.status);
                            if (!res.ok) {
                                return res.text().then(text => {
                                    console.error('Error response:', text);
                                    throw new Error(`HTTP ${res.status}: ${text}`);
                                });
                            }
                            return res.json();
                        })
                        .then(data => {
                            console.log('Success:', data);
                            
                            // Update the temporary message with real server data
                            const tempMsgElement = document.querySelector(`[data-message-id="${tempMessageId}"]`);
                            if (tempMsgElement) {
                                // Update message ID
                                tempMsgElement.setAttribute('data-message-id', data.id);
                                
                                // Update message content with attachments from server response
                                const contentDiv = tempMsgElement.querySelector('.message-content') || tempMsgElement;
                                
                                // Clear existing content except time
                                const timeDiv = tempMsgElement.querySelector('.message-time');
                                contentDiv.innerHTML = '';
                                
                                // Add text if present
                                if (data.text) {
                                    const textParagraph = document.createElement('div');
                                    textParagraph.textContent = data.text;
                                    contentDiv.appendChild(textParagraph);
                                }
                                
                                // Add attachments if present
                                if (data.attachments && data.attachments.length > 0) {
                                    const attachmentsDiv = document.createElement('div');
                                    attachmentsDiv.className = 'message-attachments';
                                    
                                    data.attachments.forEach(att => {
                                        const fileIcon = getFileIcon(att.filename);
                                        const isImage = /\.(jpg|jpeg|png|gif|webp|svg)$/i.test(att.filename);
                                        const isPdf = /\.pdf$/i.test(att.filename);
                                        
                                        const attachmentItem = document.createElement('div');
                                        attachmentItem.className = 'attachment-item';
                                        
                                        if (isImage) {
                                            attachmentItem.className = 'attachment-item image-attachment';
                                            attachmentItem.innerHTML = `
                                                <div class="attachment-image-preview">
                                                    <img src="${att.url}" alt="${att.filename}" onclick="window.open('${att.url}', '_blank')" style="max-width: 200px; max-height: 150px; cursor: pointer; border-radius: 4px;">
                                                </div>
                                                <div class="attachment-info" style="display: flex; justify-content: space-between; align-items: center; width: 100%;">
                                                    <div>
                                                        <span class="attachment-filename">${att.filename}</span>
                                                        <span class="attachment-size">${formatFileSize(att.filesize)}</span>
                                                    </div>
                                                    <div class="attachment-actions">
                                                        <a href="${att.url}" target="_blank" class="attachment-download">
                                                            <i class="fas fa-download"></i>
                                                        </a>
                                                    </div>
                                                </div>
                                            `;
                                        } else {
                                            attachmentItem.innerHTML = `
                                                <i class="${fileIcon}"></i>
                                                <div class="attachment-info">
                                                    <span class="attachment-filename">${att.filename}</span>
                                                    <span class="attachment-size">${formatFileSize(att.filesize)}</span>
                                                </div>
                                                <div class="attachment-actions">
                                                    <a href="${att.url}" ${isPdf ? 'target="_blank"' : 'download'} class="attachment-download">
                                                        <i class="fas fa-download"></i>
                                                    </a>
                                                </div>
                                            `;
                                        }
                                        attachmentsDiv.appendChild(attachmentItem);
                                    });
                                    
                                    contentDiv.appendChild(attachmentsDiv);
                                }
                                
                                // Re-add time element
                                if (timeDiv) {
                                    contentDiv.appendChild(timeDiv);
                                }
                            }
                            
                            clearContentEditable(inputEl);
                            clearFilePreviews();
                            
                            // Still reload messages after a short delay to catch any updates
                            setTimeout(() => {
                                loadMessages();
                            }, 2000);
                        })
                        .catch((err) => {
                            console.error('Failed to send message:', err);
                            // Show error status
                            const tempMsg = document.querySelector(`[data-message-id="${tempMessageId}"] .message-status`);
                            if (tempMsg) {
                                tempMsg.innerHTML = '<span class="tick" style="color: #ef4444;">✗</span>';
                            }
                            alert('Failed to send message. Please try again.');
                        });
                });

                // Helper function to update message status when read
                function updateMessageStatus(messageId, status) {
                    const messageElement = document.querySelector(`[data-message-id="${messageId}"]`);
                    if (!messageElement) return;
                    
                    const statusElement = messageElement.querySelector('.message-status');
                    if (!statusElement) return;
                    
                    switch(status) {
                        case 'sending':
                            statusElement.innerHTML = '<span class="tick sending">✓</span>';
                            break;
                        case 'sent':
                            statusElement.innerHTML = '<span class="tick double sending">✓✓</span>';
                            break;
                        case 'delivered':
                            statusElement.innerHTML = '<span class="tick double delivered">✓✓</span>';
                            break;
                        case 'read':
                            statusElement.innerHTML = '<span class="tick double read">✓✓</span>';
                            break;
                        case 'error':
                            statusElement.innerHTML = '<span class="tick" style="color: #ef4444;">✗</span>';
                            break;
                    }
                }

                // Helper function to check if there are attached files
                function hasAttachedFiles() {
                    return document.querySelectorAll('.file-preview').length > 0;
                }

                // Helper function to clear file previews
                function clearFilePreviews() {
                    const filePreviews = document.getElementById('filePreviews');
                    const fileUpload = document.getElementById('fileUpload');
                    if (filePreviews) {
                        filePreviews.innerHTML = '';
                        filePreviews.style.display = 'none';
                    }
                    if (fileUpload) {
                        fileUpload.value = '';
                    }
                }

                inputEl.addEventListener('keydown', (e) => {
                    if (e.key === 'Enter' && !e.shiftKey) {
                        e.preventDefault();
                        sendBtn.click();
                    }
                });

                renderTicketConversations();
                loadMessages();

                // Periodically check for message read status updates
                setInterval(() => {
                    if (currentTicketId && contactId) {
                        // Check if any sent messages have been read
                        const sentMessages = document.querySelectorAll('.message.sent[data-message-id]');
                        sentMessages.forEach(msgElement => {
                            const messageId = msgElement.getAttribute('data-message-id');
                            if (messageId && !messageId.startsWith('temp-')) {
                                // Check if message has been read by looking for is_read status
                                // This would ideally come from a WebSocket or API call
                                // For now, we'll simulate read status after 5 seconds
                                const statusElement = msgElement.querySelector('.message-status .tick');
                                if (statusElement && statusElement.classList.contains('delivered')) {
                                    // Simulate message being read after 5 seconds
                                    setTimeout(() => {
                                        updateMessageStatus(messageId, 'read');
                                    }, 5000);
                                }
                            }
                        });
                    }
                }, 3000); // Check every 3 seconds

                // File upload handler function
                function setupFileUploadHandlers() {
                    const fileUpload = document.getElementById('fileUpload');
                    const filePreviews = document.getElementById('filePreviews');
                    const attachFileBtn = document.getElementById('attachFileBtn');
                    
                    if (!fileUpload || !filePreviews || !attachFileBtn) {
                        console.error('File upload elements not found');
                        return;
                    }
                    
                    // Handle file selection
                    attachFileBtn.addEventListener('click', () => {
                        fileUpload.click();
                    });
                    
                    // Handle file selection change
                    fileUpload.addEventListener('change', handleFileSelect);
                    
                    // Handle file selection
                    function handleFileSelect(e) {
                        const files = e.target.files;
                        console.log('Files selected:', files.length);
                        if (files.length > 0) {
                            filePreviews.style.display = 'flex';
                            
                            Array.from(files).forEach(file => {
                                console.log('Processing file:', file.name, file.size);
                                if (file.size > 10 * 1024 * 1024) {
                                    alert('File size should be less than 10MB');
                                    return;
                                }
                                
                                const preview = document.createElement('div');
                                preview.className = 'file-preview';
                                preview.dataset.fileName = file.name;
                                preview.storedFile = file; // Store the actual file object
                                console.log('Stored file in preview:', file.name);
                                
                                if (file.type.startsWith('image/')) {
                                    const reader = new FileReader();
                                    reader.onload = (e) => {
                                        preview.innerHTML = `
                                            <img src="${e.target.result}" alt="${file.name}">
                                            <div class="file-info">
                                                <span class="file-name">${file.name}</span>
                                                <span class="file-size">${formatFileSize(file.size)}</span>
                                            </div>
                                            <button class="remove-file" title="Remove file">&times;</button>
                                        `;
                                        
                                        // Add remove file handler
                                        const removeBtn = preview.querySelector('.remove-file');
                                        removeBtn.addEventListener('click', () => {
                                            preview.remove();
                                            if (filePreviews.children.length === 0) {
                                                filePreviews.style.display = 'none';
                                            }
                                        });
                                        
                                        filePreviews.appendChild(preview);
                                    };
                                    reader.readAsDataURL(file);
                                } else {
                                    const iconClass = getFileIcon(file.name);
                                    
                                    preview.innerHTML = `
                                        <i class="${iconClass} fa-2x" style="color: var(--accent)"></i>
                                        <div class="file-info">
                                            <span class="file-name">${file.name}</span>
                                            <span class="file-size">${formatFileSize(file.size)}</span>
                                        </div>
                                        <button class="remove-file" title="Remove file">&times;</button>
                                    `;
                                    
                                    // Add remove file handler
                                    const removeBtn = preview.querySelector('.remove-file');
                                    removeBtn.addEventListener('click', () => {
                                        preview.remove();
                                        if (filePreviews.children.length === 0) {
                                            filePreviews.style.display = 'none';
                                        }
                                    });
                                    
                                    filePreviews.appendChild(preview);
                                }
                            });
                            
                            // Reset file input to allow selecting the same file again
                            fileUpload.value = '';
                        }
                    }
                }

                setupFileUploadHandlers();

                // New Chat button behavior (API-based flow)
                function startNewChat() {
                    if (!ticketIds.length) {
                        window.location.href = '/dashboard/user-dashboard/ticket/';
                        return;
                    }

                    const nextTicketId = ticketIds[0] || '';
                    if (!nextTicketId) {
                        return;
                    }

                    if (nextTicketId !== currentTicketId) {
                        currentTicketId = nextTicketId;
                        window.USER_CHAT_TICKET_ID = nextTicketId;
                        renderTicketConversations();
                    }
                    loadMessages();
                    inputEl.focus();
                }

                const newChatBtn = document.getElementById('newChatBtn');
                if (newChatBtn) newChatBtn.addEventListener('click', startNewChat);
                const startNewChatBtn = document.getElementById('startNewChatBtn');
                if (startNewChatBtn) startNewChatBtn.addEventListener('click', startNewChat);

                return;
            }

            // Sample data for demonstration
            const conversations = [
                {
                    id: 1,
                    name: 'Support Team',
                    lastMessage: 'Hello! How can I help you today?',
                    time: '2m ago',
                    unread: 2,
                    online: true
                },
                {
                    id: 2,
                    name: 'Billing Department',
                    lastMessage: 'Your invoice has been generated',
                    time: '1h ago',
                    unread: 0,
                    online: true
                },
                {
                    id: 3,
                    name: 'Technical Support',
                    lastMessage: 'Have you tried restarting the application?',
                    time: '5h ago',
                    unread: 0,
                    online: false
                }
            ];

            const messages = {
                1: [
                    { text: 'Hello! How can I help you today?', sent: false, time: '2:30 PM' },
                    { text: 'I\'m having trouble with my account login', sent: true, time: '2:32 PM' },
                    { text: 'I see. Have you tried resetting your password?', sent: false, time: '2:33 PM' }
                ]
            };

            // Render conversations
            const renderConversations = () => {
                const container = document.getElementById('conversationList');
                if (conversations.length === 0) {
                    container.innerHTML = `
                        <div class="empty-state">
                            <i class="far fa-comment-dots"></i>
                            <p>No active conversations</p>
                            <button class="btn btn-primary mt-2" id="emptyStateNewChatBtn">Start New Chat</button>
                        </div>`;
                    return;
                }

                container.innerHTML = conversations.map(conv => `
                    <div class="conversation" data-conversation-id="${conv.id}">
                        <div class="conversation-header">
                            <span class="conversation-name">${conv.name}</span>
                            <span class="conversation-time">${conv.time}</span>
                        </div>
                        <div class="conversation-preview">
                            ${conv.lastMessage}
                        </div>
                        ${conv.unread > 0 ? `<span class="unread-badge">${conv.unread}</span>` : ''}
                    </div>
                `).join('');

                // Add click handlers
                document.querySelectorAll('.conversation').forEach(conv => {
                    conv.addEventListener('click', () => {
                        const convId = parseInt(conv.getAttribute('data-conversation-id'));
                        loadConversation(convId);
                        
                        // Mark as read
                        const conversation = conversations.find(c => c.id === convId);
                        if (conversation) {
                            conversation.unread = 0;
                            renderConversations();
                        }
                    });
                });
            };

            // Render messages for a conversation
            const renderMessages = (conversationId) => {
                const container = document.getElementById('chatMessages');
                const conversation = conversations.find(c => c.id === conversationId);
                
                if (!messages[conversationId]) {
                    container.innerHTML = `
                        <div class="empty-state">
                            <i class="far fa-comments"></i>
                            <h3>Start a conversation with ${conversation?.name || 'Support'}</h3>
                            <p>Ask us anything or share your concerns.</p>
                        </div>`;
                    return;
                }

                container.innerHTML = messages[conversationId].map(msg => `
                    <div class="message ${msg.sent ? 'sent' : 'received'}">
                        <div>${msg.text}</div>
                        <div class="message-time">
                            ${msg.time}
                            ${msg.sent ? `<span class="message-status">✓✓</span>` : ''}
                        </div>
                    </div>
                `).join('');

                // Scroll to bottom
                container.scrollTop = container.scrollHeight;
            };

            // Load a conversation
            const loadConversation = (conversationId) => {
                document.querySelectorAll('.conversation').forEach(c => {
                    c.classList.toggle('active', parseInt(c.getAttribute('data-conversation-id')) === conversationId);
                });
                renderMessages(conversationId);
                
                // Update agent status
                const conversation = conversations.find(c => c.id === conversationId);
                const statusDot = document.querySelector('.status-dot');
                const statusText = document.querySelector('.status-text');
                
                if (conversation) {
                    statusDot.classList.toggle('offline', !conversation.online);
                    statusText.textContent = conversation.online 
                        ? `${conversation.name} is online` 
                        : `${conversation.name} is offline`;
                }
            };

            // Function to get text from contenteditable div
            const getTextFromContentEditable = (element) => {
                // Create a range and get the text content
                if (window.getSelection) {
                    const selection = window.getSelection();
                    const range = document.createRange();
                    range.selectNodeContents(element);
                    selection.removeAllRanges();
                    selection.addRange(range);
                    const text = selection.toString().trim();
                    selection.removeAllRanges();
                    return text;
                }
                return element.innerText.trim();
            };

            // Function to clear contenteditable div
            const clearContentEditable = (element) => {
                element.textContent = '';
                // Dispatch input event to update any listeners
                const event = new Event('input', { bubbles: true });
                element.dispatchEvent(event);
            };

            // Send message - Real API implementation only
            // The real API implementation is already set up above in the contactId block

            // New chat functionality
            function startNewChat() {
                // In a real app, this would create a new conversation on the server
                const newChatId = conversations.length > 0 ? Math.max(...conversations.map(c => c.id)) + 1 : 1;
                
                // Add new conversation
                const newConversation = {
                    id: newChatId,
                    name: 'New Chat',
                    lastMessage: '',
                    time: 'Just now',
                    unread: 0,
                    online: false
                };
                
                conversations.push(newConversation);
                messages[newChatId] = [];
                
                // Render the updated conversations list
                renderConversations();
                
                // Select the new conversation
                loadConversation(newChatId);
                
                // Focus the message input
                document.querySelector('.chat-input').focus();
            }
            
            // File upload handling - Real API implementation only
            // The real file upload handlers are already set up above in the contactId block
            
            // Add event listeners for new chat buttons
            document.getElementById('newChatBtn')?.addEventListener('click', startNewChat);
            document.getElementById('startNewChatBtn')?.addEventListener('click', startNewChat);
            document.getElementById('emptyStateNewChatBtn')?.addEventListener('click', startNewChat);
            
            });
