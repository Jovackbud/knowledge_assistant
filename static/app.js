// static/app.js

document.addEventListener('DOMContentLoaded', () => {
    // --- Element Selectors (No changes needed here) ---
    const loginSection = document.getElementById('login-section');
    const userProfileSection = document.getElementById('user-profile-section');
    const chatSection = document.getElementById('chat-section');
    const feedbackSection = document.getElementById('feedback-section');
    const ticketCreationTrigger = document.getElementById('ticket-creation-trigger');
    const ticketModal = document.getElementById('ticket-modal');
    const emailInput = document.getElementById('email');
    const loginButton = document.getElementById('loginButton');
    const loginError = document.getElementById('login-error');
    const profileEmail = document.getElementById('profile-email');
    const logoutButton = document.getElementById('logoutButton');
    const chatHistoryDiv = document.getElementById('chat-history');
    const chatInput = document.getElementById('chat-input');
    const sendChatButton = document.getElementById('sendChatButton');
    const feedbackButtonsDiv = document.getElementById('feedback-buttons');
    const helpfulButton = document.getElementById('helpfulButton');
    const notHelpfulButton = document.getElementById('notHelpfulButton');
    const feedbackMessage = document.getElementById('feedback-message');
    const openTicketModalButton = document.getElementById('openTicketModalButton');
    const ticketQuestionTextarea = document.getElementById('ticket-question');
    const ticketTeamSelect = document.getElementById('ticket-team');
    const teamSuggestionP = document.getElementById('team-suggestion');
    const submitTicketButton = document.getElementById('submitTicketButton');
    const cancelTicketButton = document.getElementById('cancelTicketButton');
    const ticketSubmissionMessage = document.getElementById('ticket-submission-message');
    const adminControlsArea = document.getElementById('admin-controls-area');
    const toggleAdminPanelButton = document.getElementById('toggleAdminPanelButton');
    const adminPermissionsSection = document.getElementById('admin-permissions-section');
    const viewTargetUserEmailInput = document.getElementById('view-target-user-email');
    const viewPermissionsButton = document.getElementById('viewPermissionsButton');
    const adminViewPermissionsMessage = document.getElementById('admin-view-permissions-message');
    const userPermissionsDisplayDiv = document.getElementById('user-permissions-display');
    const displayUserEmailSpan = document.getElementById('display-user-email');
    const displayUserPermissionsJsonPre = document.getElementById('display-user-permissions-json');
    const adminPermissionsForm = document.getElementById('admin-permissions-form');
    const targetUserEmailInput = document.getElementById('target-user-email');
    const targetHierarchyLevelInput = document.getElementById('target-hierarchy-level');
    const targetDepartmentsInput = document.getElementById('target-departments');
    const knownDepartmentsDatalist = document.getElementById('known-departments-list');
    const targetProjectsInput = document.getElementById('target-projects');
    const roleContextTagInput = document.getElementById('role-context-tag');
    const roleNameTagInput = document.getElementById('role-name-tag');
    const addRoleButton = document.getElementById('addRoleButton');
    const contextualRolesPreview = document.getElementById('contextual-roles-preview');
    const adminPermissionsMessage = document.getElementById('admin-permissions-message');
    const removeTargetUserEmailInput = document.getElementById('remove-target-user-email');
    const removeUserButton = document.getElementById('removeUserButton');
    const adminRemoveUserMessage = document.getElementById('admin-remove-user-message');


    // --- State Variables ---
    // --- UPDATED FOR JWT PERSISTENCE ---
    // Try to load user profile and token from localStorage on startup.
    let currentUserProfile = JSON.parse(localStorage.getItem('knowledgeAssistantProfile')) || null;
    let jwtToken = localStorage.getItem('knowledgeAssistantToken') || null;
    let currentUserEmail = currentUserProfile ? currentUserProfile.user_email : null;
    
    // Other state variables remain the same
    let currentQuestion = null;
    let currentAnswer = null;
    let chatHistory = [];
    let contextualRolesObject = {};

    // --- Helper function for API calls ---
    function getAuthHeaders() {
        if (!jwtToken) return { 'Content-Type': 'application/json' };
        return {
            'Content-Type': 'application/json',
            'Authorization': `Bearer ${jwtToken}`
        };
    }

    // --- Visibility & UI Functions ---
    function showLogin() {
        [userProfileSection, chatSection, feedbackSection, ticketCreationTrigger, ticketModal, adminControlsArea, adminPermissionsSection, userPermissionsDisplayDiv].forEach(el => el.classList.add('hidden'));
        loginSection.classList.remove('hidden');
    }

    function showChat() {
        [loginSection, adminPermissionsSection].forEach(el => el.classList.add('hidden'));
        [userProfileSection, chatSection, ticketCreationTrigger].forEach(el => el.classList.remove('hidden'));
    }
    
    async function loadAdminPanelData() {
        try {
            const response = await fetch('/admin/config_tags', { headers: getAuthHeaders() });
            if (!response.ok) return;
            const data = await response.json();
            knownDepartmentsDatalist.innerHTML = '';
            if (data.known_department_tags) {
                data.known_department_tags.forEach(tag => {
                    const option = document.createElement('option');
                    option.value = tag;
                    knownDepartmentsDatalist.appendChild(option);
                });
            }
        } catch (error) {
            console.error("Could not load admin config tags:", error);
        }
    }
    
    function hideTicketModal() {
        ticketModal.classList.add('hidden');
        ticketQuestionTextarea.value = '';
        ticketSubmissionMessage.textContent = '';
        teamSuggestionP.textContent = '';
        ticketTeamSelect.innerHTML = '';
    }
    
    function appendMessage(role, text) {
        const messageDiv = document.createElement('div');
        messageDiv.classList.add('chat-message', `${role}-message`);
        
        if (role === 'user') {
            messageDiv.textContent = text;
            chatHistoryDiv.appendChild(messageDiv);
            chatHistoryDiv.scrollTop = chatHistoryDiv.scrollHeight;
            return {};
        }
    
        const contentDiv = document.createElement('div');
        contentDiv.classList.add('assistant-message-content');
        contentDiv.innerHTML = text;
        
        const sourcesDiv = document.createElement('div');
        sourcesDiv.classList.add('sources-container', 'hidden');
    
        messageDiv.appendChild(contentDiv);
        messageDiv.appendChild(sourcesDiv);
    
        chatHistoryDiv.appendChild(messageDiv);
        chatHistoryDiv.scrollTop = chatHistoryDiv.scrollHeight;
    
        return { contentDiv, sourcesDiv };
    }

    chatInput.addEventListener('input', () => {
        chatInput.style.height = 'auto';
        const scrollHeight = chatInput.scrollHeight;
        chatInput.style.height = `${Math.min(scrollHeight, 150)}px`;
    });


    // --- Event Listeners ---
    loginButton.addEventListener('click', async () => {
        const email = emailInput.value.trim();
        if (!email) { loginError.textContent = 'Please enter your email.'; return; }
        loginError.textContent = '';
        loginButton.disabled = true;
        loginButton.textContent = 'Logging in...';
        try {
            const response = await fetch('/auth/login', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ email })
            });
            const data = await response.json();
            if (!response.ok) throw new Error(data.detail || 'Login failed');
            
            jwtToken = data.access_token;
            currentUserProfile = data.user_profile;
            currentUserEmail = data.user_profile.user_email;

            // --- UPDATED FOR JWT PERSISTENCE ---
            // Save the token and profile to localStorage
            localStorage.setItem('knowledgeAssistantToken', jwtToken);
            localStorage.setItem('knowledgeAssistantProfile', JSON.stringify(currentUserProfile));

            if (currentUserProfile) {
                profileEmail.textContent = currentUserEmail;
                showChat();
                emailInput.value = '';

                const ADMIN_LEVEL = 3; 
                if (currentUserProfile.user_hierarchy_level === ADMIN_LEVEL) {
                    adminControlsArea.classList.remove('hidden');
                    toggleAdminPanelButton.textContent = 'Show Admin Panel';
                } else {
                    adminControlsArea.classList.add('hidden');
                    adminPermissionsSection.classList.add('hidden');
                }
            } else {
                throw new Error('Login response was missing user profile details.');
            }
        } catch (error) {
            console.error('Login error:', error);
            loginError.textContent = error.message;
            currentUserEmail = null; 
            currentUserProfile = null;
            jwtToken = null;
        } finally {
            loginButton.disabled = false;
            loginButton.textContent = 'Login';
        }
    });

    logoutButton.addEventListener('click', () => {
        // --- UPDATED FOR JWT PERSISTENCE ---
        // Clear the token and profile from localStorage
        localStorage.removeItem('knowledgeAssistantToken');
        localStorage.removeItem('knowledgeAssistantProfile');

        // Reset all state variables
        currentUserEmail = null;
        currentUserProfile = null;
        jwtToken = null;
        currentQuestion = null;
        currentAnswer = null;
        chatHistory = [];
        contextualRolesObject = {};
        
        // Reset UI
        chatHistoryDiv.innerHTML = '';
        profileEmail.textContent = '';
        adminPermissionsForm.reset();
        contextualRolesPreview.textContent = '{}';
        
        showLogin();
    });

    toggleAdminPanelButton.addEventListener('click', () => {
        const isAdminPanelVisible = !adminPermissionsSection.classList.contains('hidden');
        if (isAdminPanelVisible) {
            adminPermissionsSection.classList.add('hidden');
            toggleAdminPanelButton.textContent = 'Show Admin Panel';
        } else {
            adminPermissionsSection.classList.remove('hidden');
            toggleAdminPanelButton.textContent = 'Hide Admin Panel';
            loadAdminPanelData();
        }
    });

    const handleSend = async () => {
        const prompt = chatInput.value.trim();
        if (!prompt || !currentUserEmail) {
            console.error("Exiting: Prompt is empty or user is not logged in properly.");
            return;
        }

        appendMessage('user', prompt);
        chatHistory.push({ role: 'user', content: prompt });
        currentQuestion = prompt;
        chatInput.value = '';
        chatInput.style.height = 'auto'; // Reset textarea height
        feedbackSection.classList.add('hidden');

        chatInput.disabled = true;
        sendChatButton.disabled = true;
        sendChatButton.textContent = '...';

        try {
            const response = await fetch('/rag/chat', {
                method: 'POST',
                headers: getAuthHeaders(),
                body: JSON.stringify({
                    prompt: prompt,
                    chat_history: chatHistory.slice(-9, -1)
                })
            });
        
            if (!response.ok || !response.body) {
                const errData = await response.json();
                throw new Error(errData.detail || 'Failed to get a valid response from the server.');
            }
        
            const { contentDiv, sourcesDiv } = appendMessage('assistant', '...');
            currentAnswer = '';
        
            const reader = response.body.getReader();
            const decoder = new TextDecoder();
            let buffer = '';
        
            while (true) {
                const { value, done } = await reader.read();
                if (done) break;
        
                buffer += decoder.decode(value, { stream: true });
                const events = buffer.split('\n\n');
                buffer = events.pop(); 
        
                for (const event of events) {
                    if (event.startsWith('data: ')) {
                        try {
                            const jsonData = JSON.parse(event.substring(6));
                            
                            if (jsonData.answer_chunk) {
                                if (contentDiv.textContent === '...') contentDiv.textContent = '';
                                currentAnswer += jsonData.answer_chunk;
                                contentDiv.innerHTML = marked.parse(currentAnswer + ' ▌');
                            }
                            if (jsonData.sources) {
                                sourcesDiv.classList.remove('hidden');
                                const sourceList = jsonData.sources.map(source => `<li class="source-item">${source}</li>`).join('');
                                sourcesDiv.innerHTML = `<strong>Sources:</strong><ul>${sourceList}</ul>`;
                            }
                            if (jsonData.error) {
                                contentDiv.innerHTML = `<p class="error-message">Error: ${jsonData.error}</p>`;
                            }
                        } catch (e) {
                            console.warn("Could not parse JSON from stream event:", event, e);
                        }
                    }
                }
                chatHistoryDiv.scrollTop = chatHistoryDiv.scrollHeight;
            }
            
            contentDiv.innerHTML = marked.parse(currentAnswer);
            
            if (contentDiv.textContent === '...') {
                contentDiv.textContent = "I'm sorry, but I couldn't find a relevant answer in the documents available to me.";
            }
        
            chatHistory.push({ role: 'assistant', content: currentAnswer });
            feedbackSection.classList.remove('hidden');
            feedbackButtonsDiv.classList.remove('hidden');
            feedbackMessage.textContent = '';
        
        } catch (error) {
            console.error('Chat error:', error);
            const { contentDiv } = appendMessage('assistant', `An error occurred: ${error.message}`);
            contentDiv.classList.add('error-message');
            currentAnswer = null;
            
        } finally {
            chatInput.disabled = false;
            sendChatButton.disabled = false;
            sendChatButton.textContent = 'Send';
        }
    };

    sendChatButton.addEventListener('click', handleSend);
    chatInput.addEventListener('keydown', (event) => {
        if (event.key === 'Enter' && !event.shiftKey) {
            event.preventDefault();
            handleSend();
        }
    });

    async function handleFeedback(feedbackType) {
        if (!currentQuestion || !currentAnswer || !currentUserEmail) return;
        feedbackMessage.textContent = '';
        feedbackMessage.className = 'success-message';
        try {
            const response = await fetch('/feedback/record', {
                method: 'POST',
                headers: getAuthHeaders(),
                body: JSON.stringify({ question: currentQuestion, answer: currentAnswer, feedback_type: feedbackType })
            });
            if (!response.ok) throw new Error('Could not submit feedback.');
            feedbackMessage.textContent = 'Feedback received. Thank you!';
            feedbackButtonsDiv.classList.add('hidden');
        } catch (error) {
            feedbackMessage.textContent = `Error: ${error.message}`;
            feedbackMessage.className = 'error-message';
        }
    }
    helpfulButton.addEventListener('click', () => handleFeedback('👍'));
    notHelpfulButton.addEventListener('click', () => handleFeedback('👎'));

    // --- Admin Panel Listeners (No changes needed here) ---
    addRoleButton.addEventListener('click', () => {
        const context = roleContextTagInput.value.trim().toUpperCase();
        const role = roleNameTagInput.value.trim().toUpperCase();
        if (!context || !role) { alert('Both Context and Role Name must be filled.'); return; }
        if (!contextualRolesObject[context]) { contextualRolesObject[context] = []; }
        if (!contextualRolesObject[context].includes(role)) { contextualRolesObject[context].push(role); }
        contextualRolesPreview.textContent = JSON.stringify(contextualRolesObject, null, 2);
        roleContextTagInput.value = '';
        roleNameTagInput.value = '';
        roleContextTagInput.focus();
    });

    adminPermissionsForm.addEventListener('submit', async (event) => {
        event.preventDefault();
        adminPermissionsMessage.textContent = ''; 
        adminPermissionsMessage.className = 'error-message';
        const targetEmail = targetUserEmailInput.value.trim();
        if (!targetEmail) { adminPermissionsMessage.textContent = 'Target User Email is required.'; return; }

        const permissions = {};
        const hierarchyLevel = targetHierarchyLevelInput.value.trim();
        if (hierarchyLevel !== '') permissions.user_hierarchy_level = parseInt(hierarchyLevel, 10);
        
        const departmentsStr = targetDepartmentsInput.value.trim();
        if (departmentsStr !== '') permissions.departments = departmentsStr.split(',').map(d => d.trim().toUpperCase()).filter(Boolean);

        const projectsStr = targetProjectsInput.value.trim();
        if (projectsStr !== '') permissions.projects_membership = projectsStr.split(',').map(p => p.trim().toUpperCase()).filter(Boolean);
        
        if (Object.keys(contextualRolesObject).length > 0) { permissions.contextual_roles = contextualRolesObject; }
        if (Object.keys(permissions).length === 0) { adminPermissionsMessage.textContent = 'No changes detected. Please fill in at least one field to update.'; return; }
        
        try {
            const response = await fetch('/admin/user_permissions', {
                method: 'POST',
                headers: getAuthHeaders(),
                body: JSON.stringify({ target_email: targetEmail, permissions })
            });
            const data = await response.json();
            if (!response.ok) throw new Error(data.detail || 'Failed to update permissions.');
            
            adminPermissionsMessage.textContent = data.message || 'Permissions updated successfully!';
            adminPermissionsMessage.className = 'success-message';
            adminPermissionsForm.reset();
            contextualRolesObject = {};
            contextualRolesPreview.textContent = '{}';

            if (data.updated_profile) {
                 adminPermissionsMessage.innerHTML += `<br>Updated Profile: <pre>${JSON.stringify(data.updated_profile, null, 2)}</pre>`;
            }
        } catch (error) {
            adminPermissionsMessage.textContent = `Error: ${error.message}`;
        }
    });

    viewPermissionsButton.addEventListener('click', async () => {
        adminViewPermissionsMessage.textContent = ''; 
        adminViewPermissionsMessage.className = 'error-message';
        userPermissionsDisplayDiv.classList.add('hidden');
        const targetEmailToView = viewTargetUserEmailInput.value.trim();
        if (!targetEmailToView) { adminViewPermissionsMessage.textContent = 'User Email to view is required.'; return; }
        try {
            const response = await fetch(`/admin/view_user_permissions/${encodeURIComponent(targetEmailToView)}`, {
                method: 'GET', headers: getAuthHeaders()
            });
            const data = await response.json();
            if (!response.ok) throw new Error(data.detail || 'Failed to fetch permissions.');
            
            adminViewPermissionsMessage.textContent = 'Permissions fetched successfully.';
            adminViewPermissionsMessage.className = 'success-message';
            displayUserEmailSpan.textContent = data.user_email || targetEmailToView;
            displayUserPermissionsJsonPre.textContent = JSON.stringify(data, null, 2); 
            userPermissionsDisplayDiv.classList.remove('hidden');
        } catch (error) {
            adminViewPermissionsMessage.textContent = `Error: ${error.message}`;
        }
    });

    removeUserButton.addEventListener('click', async () => {
        adminRemoveUserMessage.textContent = ''; 
        adminRemoveUserMessage.className = 'error-message';
        const targetEmailToRemove = removeTargetUserEmailInput.value.trim();
        if (!targetEmailToRemove) { adminRemoveUserMessage.textContent = 'User Email to remove is required.'; return; }
        if (!confirm(`Are you sure you want to remove the user '${targetEmailToRemove}'? This action cannot be undone.`)) { return; }
        try {
            const response = await fetch('/admin/remove_user', {
                method: 'POST',
                headers: getAuthHeaders(),
                body: JSON.stringify({ target_email: targetEmailToRemove })
            });
            const data = await response.json();
            if (!response.ok) throw new Error(data.detail || 'Failed to remove user.');
            adminRemoveUserMessage.textContent = data.message || 'User removed successfully!';
            adminRemoveUserMessage.className = 'success-message';
            removeTargetUserEmailInput.value = ''; 
        } catch (error) {
            adminRemoveUserMessage.textContent = `Error: ${error.message}`;
        }
    });

    // --- Ticket System Listeners (No changes needed here) ---
    openTicketModalButton.addEventListener('click', () => {
        ticketModal.classList.remove('hidden');
        ticketQuestionTextarea.value = currentQuestion || ''; 
        ticketSubmissionMessage.textContent = ''; 
        teamSuggestionP.textContent = '';
        if (ticketQuestionTextarea.value) {
            ticketQuestionTextarea.dispatchEvent(new Event('input', { bubbles: true }));
        } else {
             ticketTeamSelect.innerHTML = '<option value="">Enter question for suggestions</option>';
        }
    });

    cancelTicketButton.addEventListener('click', () => { hideTicketModal(); });

    let suggestTeamTimeout;
    ticketQuestionTextarea.addEventListener('input', () => {
        clearTimeout(suggestTeamTimeout);
        const questionText = ticketQuestionTextarea.value.trim();
        teamSuggestionP.textContent = '';
        if (!questionText) { ticketTeamSelect.innerHTML = '<option value="">Enter question to see suggestions</option>'; return; }
        ticketTeamSelect.innerHTML = '<option value="">Loading teams...</option>';
        suggestTeamTimeout = setTimeout(async () => {
            try {
                const response = await fetch('/tickets/suggest_team', {
                    method: 'POST',
                    headers: getAuthHeaders(),
                    body: JSON.stringify({ question_text: questionText })
                });
                const data = await response.json();
                ticketTeamSelect.innerHTML = ''; 
                if (!response.ok) throw new Error(data.detail || 'Unknown error');
                if (data.available_teams && data.available_teams.length > 0) {
                    data.available_teams.forEach(team => {
                        const option = document.createElement('option');
                        option.value = team; option.textContent = team;
                        if (team === data.suggested_team) { option.selected = true; }
                        ticketTeamSelect.appendChild(option);
                    });
                    teamSuggestionP.textContent = data.suggested_team ? `Suggested Team: ${data.suggested_team}` : 'Please select a team.';
                } else {
                    ticketTeamSelect.innerHTML = '<option value="">No teams available</option>';
                }
            } catch (error) {
                teamSuggestionP.textContent = `Error: ${error.message}`;
            }
        }, 500); 
    });
    
    submitTicketButton.addEventListener('click', async () => {
        const question_text = ticketQuestionTextarea.value.trim();
        const selected_team = ticketTeamSelect.value;
        ticketSubmissionMessage.textContent = ''; 
        ticketSubmissionMessage.className = 'error-message';
        if (!question_text || !selected_team) { ticketSubmissionMessage.textContent = 'Question and team selection are required.'; return; }
        
        try {
            const response = await fetch('/tickets/create', {
                method: 'POST',
                headers: getAuthHeaders(),
                body: JSON.stringify({ 
                    question_text: question_text, 
                    chat_history_json: JSON.stringify(chatHistory.slice(-5)), 
                    selected_team: selected_team 
                })
            });
            const data = await response.json();
            if (!response.ok) throw new Error(data.detail || 'Could not create ticket.');
            
            ticketSubmissionMessage.textContent = 'Ticket created successfully!';
            ticketSubmissionMessage.className = 'success-message';
            setTimeout(hideTicketModal, 2000);
        } catch (error) {
            ticketSubmissionMessage.textContent = `Error: ${error.message}`;
        }
    });
    
    // --- UPDATED FOR JWT PERSISTENCE ---
    // Create an initialization function to check for an existing session
    function initApp() {
        if (jwtToken && currentUserProfile) {
            console.log("Resuming session for:", currentUserProfile.user_email);
            // Populate UI elements with data from the resumed session
            profileEmail.textContent = currentUserProfile.user_email;
            
            // Show the correct view
            showChat();

            // Check for admin privileges and show admin panel if necessary
            const ADMIN_LEVEL = 3; 
            if (currentUserProfile.user_hierarchy_level === ADMIN_LEVEL) {
                adminControlsArea.classList.remove('hidden');
                toggleAdminPanelButton.textContent = 'Show Admin Panel';
            } else {
                adminControlsArea.classList.add('hidden');
                adminPermissionsSection.classList.add('hidden');
            }
        } else {
            // If there's no token or profile, show the login screen
            showLogin();
        }
    }

    // Run the initialization function when the app loads
    initApp();
});