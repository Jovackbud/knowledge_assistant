document.addEventListener('DOMContentLoaded', () => {
    // --- Element Selectors ---
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
    let currentUserEmail = null;
    let currentUserProfile = null;
    let jwtToken = null;
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
        messageDiv.classList.add('chat-message');
        
        if (role === 'user') {
            messageDiv.classList.add('user-message');
            messageDiv.textContent = text;
            chatHistoryDiv.appendChild(messageDiv);
            chatHistoryDiv.scrollTop = chatHistoryDiv.scrollHeight;
            return {};
        }

        messageDiv.classList.add('assistant-message');
        const contentDiv = document.createElement('div');
        contentDiv.classList.add('assistant-message-content');
        contentDiv.textContent = text;
        
        const sourcesDiv = document.createElement('div');
        sourcesDiv.classList.add('sources-container', 'hidden');

        messageDiv.appendChild(contentDiv);
        messageDiv.appendChild(sourcesDiv);

        chatHistoryDiv.appendChild(messageDiv);
        chatHistoryDiv.scrollTop = chatHistoryDiv.scrollHeight;
        return { contentDiv, sourcesDiv };
    }

    // --- Event Listeners ---

    loginButton.addEventListener('click', async () => {
        const email = emailInput.value.trim();
        if (!email) { loginError.textContent = 'Please enter your email.'; return; }
        loginError.textContent = '';
        try {
            const response = await fetch('/auth/login', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ email })
            });
            const data = await response.json();
            if (!response.ok) throw new Error(data.detail || 'Login failed');
            
            jwtToken = data.access_token;

            if (data.user_profile && data.user_profile.user_email) {
                currentUserProfile = data.user_profile;
                currentUserEmail = data.user_profile.user_email;

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
        }
    });

    logoutButton.addEventListener('click', () => {
        currentUserEmail = null;
        currentUserProfile = null;
        jwtToken = null;
        currentQuestion = null;
        currentAnswer = null;
        chatHistory = [];
        contextualRolesObject = {};
        
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

    sendChatButton.addEventListener('click', async () => {
        const prompt = chatInput.value.trim();
        if (!prompt || !currentUserEmail) {
            console.error("Exiting: Prompt is empty or user is not logged in properly.");
            return;
        }

        appendMessage('user', prompt);
        chatHistory.push({ role: 'user', content: prompt });
        currentQuestion = prompt;
        chatInput.value = '';
        feedbackSection.classList.add('hidden');

        // --- SUGGESTION 5: Disable inputs during generation ---
        chatInput.disabled = true;
        sendChatButton.disabled = true;
        sendChatButton.textContent = 'Thinking...';

        try {
            const response = await fetch('/rag/chat', {
                method: 'POST',
                headers: getAuthHeaders(),
                body: JSON.stringify({
                    prompt: prompt,
                    // --- SUGGESTION 6: Limit chat history to last 8 messages (4 turns) ---
                    chat_history: chatHistory.slice(-9, -1)
                })
            });

            if (!response.ok || !response.body) {
                const errData = await response.json();
                throw new Error(errData.detail || 'Failed to get response.');
            }

            const { contentDiv, sourcesDiv } = appendMessage('assistant', '...');
            currentAnswer = '';

            const reader = response.body.getReader();
            const decoder = new TextDecoder();
            
            while (true) {
                const { value, done } = await reader.read();
                if (done) break;
                
                const lines = decoder.decode(value, { stream: true }).split('\n').filter(line => line.startsWith('data: '));
                for (const line of lines) {
                    try {
                        const jsonData = JSON.parse(line.substring(5));
                        if (jsonData.answer_chunk) {
                            if (currentAnswer === '' && contentDiv.textContent === '...') currentAnswer = '';
                            currentAnswer += jsonData.answer_chunk;
                            contentDiv.textContent = currentAnswer;
                        }
                        if (jsonData.sources) {
                            sourcesDiv.classList.remove('hidden');
                            sourcesDiv.innerHTML = '<strong>Sources:</strong>';
                            const sourceList = document.createElement('ul');
                            jsonData.sources.forEach(source => {
                                const li = document.createElement('li');
                                li.classList.add('source-item');
                                li.textContent = source;
                                sourceList.appendChild(li);
                            });
                            sourcesDiv.appendChild(sourceList);
                        }
                        if (jsonData.error) {
                            contentDiv.textContent = jsonData.error;
                            contentDiv.style.color = 'red';
                        }
                    } catch (e) {
                        console.warn("Could not parse JSON chunk from stream:", line);
                    }
                }
                chatHistoryDiv.scrollTop = chatHistoryDiv.scrollHeight;
            }

            // --- SUGGESTION 5: Re-enable inputs on success ---
            chatInput.disabled = false;
            sendChatButton.disabled = false;
            sendChatButton.textContent = 'Send';

            if (contentDiv.textContent === '...') contentDiv.textContent = "Sorry, I couldn't find an answer.";
            
            chatHistory.push({ role: 'assistant', content: currentAnswer });
            feedbackSection.classList.remove('hidden');
            feedbackButtonsDiv.classList.remove('hidden');
            feedbackMessage.textContent = '';

        } catch (error) {
            console.error('Chat error:', error);
            const { contentDiv } = appendMessage('assistant', `An error occurred: ${error.message}`);
            if(contentDiv) contentDiv.style.color = 'red';
            currentAnswer = null;
            
            // --- SUGGESTION 5: Re-enable inputs on error ---
            chatInput.disabled = false;
            sendChatButton.disabled = false;
            sendChatButton.textContent = 'Send';
        }
    });
    
    chatInput.addEventListener('keypress', (event) => { if (event.key === 'Enter') { sendChatButton.click(); } });

    async function handleFeedback(feedbackType) {
        if (!currentQuestion || !currentAnswer || !currentUserEmail) return;
        feedbackMessage.textContent = '';
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
        }
    }
    helpfulButton.addEventListener('click', () => handleFeedback('👍'));
    notHelpfulButton.addEventListener('click', () => handleFeedback('👎'));

    // --- Admin Panel Listeners ---
    addRoleButton.addEventListener('click', () => {
        const context = roleContextTagInput.value.trim().toUpperCase();
        const role = roleNameTagInput.value.trim().toUpperCase();
        if (!context || !role) {
            alert('Both Context and Role Name must be filled.');
            return;
        }
        if (!contextualRolesObject[context]) {
            contextualRolesObject[context] = [];
        }
        if (!contextualRolesObject[context].includes(role)) {
            contextualRolesObject[context].push(role);
        }
        contextualRolesPreview.textContent = JSON.stringify(contextualRolesObject, null, 2);
        roleContextTagInput.value = '';
        roleNameTagInput.value = '';
        roleContextTagInput.focus();
    });

    adminPermissionsForm.addEventListener('submit', async (event) => {
        event.preventDefault();
        adminPermissionsMessage.textContent = ''; 
        adminPermissionsMessage.style.color = 'red';
        const targetEmail = targetUserEmailInput.value.trim();
        if (!targetEmail) { adminPermissionsMessage.textContent = 'Target User Email is required.'; return; }

        const permissions = {};
        const hierarchyLevel = targetHierarchyLevelInput.value.trim();
        if (hierarchyLevel !== '') permissions.user_hierarchy_level = parseInt(hierarchyLevel, 10);
        
        const departmentsStr = targetDepartmentsInput.value.trim();
        if (departmentsStr !== '') permissions.departments = departmentsStr.split(',').map(d => d.trim()).filter(Boolean);

        const projectsStr = targetProjectsInput.value.trim();
        if (projectsStr !== '') permissions.projects_membership = projectsStr.split(',').map(p => p.trim()).filter(Boolean);
        
        if (Object.keys(contextualRolesObject).length > 0) {
            permissions.contextual_roles = contextualRolesObject;
        }

        if (Object.keys(permissions).length === 0) {
            adminPermissionsMessage.textContent = 'No changes detected. Please fill in at least one field to update.'; return;
        }
        
        try {
            const response = await fetch('/admin/user_permissions', {
                method: 'POST',
                headers: getAuthHeaders(),
                body: JSON.stringify({ target_email: targetEmail, permissions })
            });
            const data = await response.json();
            if (!response.ok) throw new Error(data.detail || 'Failed to update permissions.');
            
            adminPermissionsMessage.textContent = data.message || 'Permissions updated successfully!';
            adminPermissionsMessage.style.color = 'green';
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
        adminViewPermissionsMessage.style.color = 'red';
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
            adminViewPermissionsMessage.style.color = 'green';
            displayUserEmailSpan.textContent = data.user_email || targetEmailToView;
            displayUserPermissionsJsonPre.textContent = JSON.stringify(data, null, 2); 
            userPermissionsDisplayDiv.classList.remove('hidden');
        } catch (error) {
            adminViewPermissionsMessage.textContent = `Error: ${error.message}`;
        }
    });

    removeUserButton.addEventListener('click', async () => {
        adminRemoveUserMessage.textContent = ''; 
        adminRemoveUserMessage.style.color = 'red';
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
            adminRemoveUserMessage.style.color = 'green';
            removeTargetUserEmailInput.value = ''; 
        } catch (error) {
            adminRemoveUserMessage.textContent = `Error: ${error.message}`;
        }
    });

    // --- Ticket System Listeners ---
    openTicketModalButton.addEventListener('click', () => {
        ticketModal.classList.remove('hidden');
        ticketQuestionTextarea.value = currentQuestion || ''; 
        ticketSubmissionMessage.textContent = ''; teamSuggestionP.textContent = '';
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
        ticketSubmissionMessage.textContent = ''; ticketSubmissionMessage.style.color = 'red';
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
            ticketSubmissionMessage.style.color = 'green';
            setTimeout(hideTicketModal, 2000);
        } catch (error) {
            ticketSubmissionMessage.textContent = `Error: ${error.message}`;
        }
    });
    
    // Initial UI State
    showLogin();
});