// static/app.js - UPDATED
document.addEventListener('DOMContentLoaded', () => {
    // --- Element Selectors ---
    const loginSection = document.getElementById('login-section');
    const userProfileControls = document.getElementById('user-profile-controls');
    const chatSection = document.getElementById('chat-section');
    const postChatActions = document.getElementById('post-chat-actions');
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
    const openAdminPanelButton = document.getElementById('openAdminPanelButton');
    const adminModal = document.getElementById('admin-modal');
    const adminModalCloseBtn = document.getElementById('admin-modal-close-btn');
    const adminNavButtons = document.querySelectorAll('.admin-nav-button');
    const adminPanels = document.querySelectorAll('.admin-panel');
    const ticketsLoadingMessage = document.getElementById('tickets-loading-message');
    const ticketsTableContainer = document.getElementById('tickets-table-container');
    const ticketsTableBody = document.getElementById('tickets-table-body');

    // --- State Variables ---
    let currentUserProfile = null;
    let currentUserEmail = null;
    let currentQuestion = null;
    let currentAnswer = null;
    let chatHistory = [];
    let contextualRolesObject = {};
    const ADMIN_LEVEL = 3;

    // --- Helper for fetch options ---
    const getFetchOptions = (method = 'GET', body = null) => {
        const options = {
            method: method,
            headers: { 'Content-Type': 'application/json' },
            credentials: 'include'
        };
        if (body) {
            options.body = JSON.stringify(body);
        }
        return options;
    };

    // --- Visibility & UI Functions ---
    function showLogin() {
        [userProfileControls, chatSection, postChatActions, ticketModal, adminControlsArea, userPermissionsDisplayDiv].forEach(el => el.classList.add('hidden'));
        loginSection.classList.remove('hidden');
    }

    function showChat() {
        loginSection.classList.add('hidden');
        [userProfileControls, chatSection].forEach(el => el.classList.remove('hidden'));
        postChatActions.classList.add('hidden'); // Keep actions hidden until a chat response is given
    }

    // NEW REFACTORED FUNCTION
    function updateUIForUserProfile(profile) {
        currentUserProfile = profile;
        currentUserEmail = profile.user_email;
        localStorage.setItem('knowledgeAssistantProfile', JSON.stringify(profile));

        profileEmail.textContent = currentUserEmail;
        showChat();
        
        if (profile.user_hierarchy_level === ADMIN_LEVEL) {
            adminControlsArea.classList.remove('hidden');
        } else {
            adminControlsArea.classList.add('hidden');
        }
    }

    async function loadAdminPanelData() {
        try {
            const response = await fetch('/admin/config_tags', getFetchOptions());
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
        } catch (error) { console.error("Could not load admin config tags:", error); }
    }
    
    function hideTicketModal() {
        ticketModal.close();
        ticketQuestionTextarea.value = ''; ticketSubmissionMessage.textContent = '';
        teamSuggestionP.textContent = ''; ticketTeamSelect.innerHTML = '';
    }
    
    // --- Append Message & Textarea Resize ---
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
        messageDiv.appendChild(contentDiv); messageDiv.appendChild(sourcesDiv);
        chatHistoryDiv.appendChild(messageDiv);
        chatHistoryDiv.scrollTop = chatHistoryDiv.scrollHeight;
        return { contentDiv, sourcesDiv };
    }

    chatInput.addEventListener('input', () => {
        chatInput.style.height = 'auto';
        chatInput.style.height = `${Math.min(chatInput.scrollHeight, 150)}px`;
    });

    // --- Event Listeners ---
    loginButton.addEventListener('click', async () => {
        const email = emailInput.value.trim();
        if (!email) { loginError.textContent = 'Please enter your email.'; return; }
        loginError.textContent = '';
        loginButton.disabled = true; loginButton.textContent = 'Logging in...';
        try {
            const response = await fetch('/auth/login', getFetchOptions('POST', { email }));
            const data = await response.json();
            if (!response.ok) throw new Error(data.detail || 'Login failed');
            
            // UPDATED to use refactored function
            if (data.user_profile) {
                updateUIForUserProfile(data.user_profile);
                emailInput.value = '';
            } else {
                throw new Error('Login response was missing user profile details.');
            }
        } catch (error) {
            console.error('Login error:', error);
            loginError.textContent = error.message;
            currentUserEmail = null; currentUserProfile = null;
            localStorage.removeItem('knowledgeAssistantProfile');
        } finally {
            loginButton.disabled = false; loginButton.textContent = 'Login';
        }
    });

    logoutButton.addEventListener('click', async () => {
        try {
            await fetch('/auth/logout', getFetchOptions('POST'));
        } catch (error) {
            console.error("Logout failed, but clearing client-side state anyway:", error);
        } finally {
            localStorage.removeItem('knowledgeAssistantProfile');
            currentUserEmail = null; currentUserProfile = null;
            currentQuestion = null; currentAnswer = null; chatHistory = [];
            contextualRolesObject = {};
            chatHistoryDiv.innerHTML = ''; profileEmail.textContent = '';
            adminPermissionsForm.reset(); contextualRolesPreview.textContent = '{}';
            showLogin();
        }
    });

    const handleSend = async () => {
        const prompt = chatInput.value.trim();
        if (!prompt || !currentUserEmail) return;
        appendMessage('user', prompt);
        chatHistory.push({ role: 'user', content: prompt });
        currentQuestion = prompt;
        chatInput.value = ''; chatInput.style.height = 'auto';
        postChatActions.classList.add('hidden'); // Hide actions while waiting for new response
        chatInput.disabled = true; sendChatButton.disabled = true; sendChatButton.textContent = '...';
        try {
            const response = await fetch('/rag/chat', getFetchOptions('POST', { prompt: prompt, chat_history: chatHistory.slice(-8) }));
            if (!response.ok || !response.body) { const errData = await response.json(); throw new Error(errData.detail || 'Failed to get a valid response from the server.'); }
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
                            if (jsonData.error) { contentDiv.innerHTML = `<p class="error-message">Error: ${jsonData.error}</p>`; }
                        } catch (e) { console.warn("Could not parse JSON from stream event:", event, e); }
                    }
                }
                chatHistoryDiv.scrollTop = chatHistoryDiv.scrollHeight;
            }
            contentDiv.innerHTML = marked.parse(currentAnswer);
            if (contentDiv.textContent === '...') { contentDiv.textContent = "I'm sorry, but I couldn't find a relevant answer in the documents available to me."; }
            chatHistory.push({ role: 'assistant', content: currentAnswer });
            postChatActions.classList.remove('hidden'); // Show actions now
            feedbackButtonsDiv.classList.remove('hidden');
            feedbackMessage.textContent = '';
        } catch (error) {
            console.error('Chat error:', error);
            const { contentDiv } = appendMessage('assistant', `An error occurred: ${error.message}`);
            if (contentDiv) contentDiv.classList.add('error-message');
            currentAnswer = null;
        } finally {
            chatInput.disabled = false; sendChatButton.disabled = false; sendChatButton.textContent = 'Send';
        }
    };

    sendChatButton.addEventListener('click', handleSend);
    chatInput.addEventListener('keydown', (event) => { if (event.key === 'Enter' && !event.shiftKey) { event.preventDefault(); handleSend(); } });

    async function handleFeedback(feedbackType) {
        if (!currentQuestion || !currentAnswer || !currentUserEmail) return;
        feedbackMessage.textContent = ''; feedbackMessage.className = 'success-message';
        try {
            const response = await fetch('/feedback/record', getFetchOptions('POST', { question: currentQuestion, answer: currentAnswer, feedback_type: feedbackType }));
            if (!response.ok) throw new Error('Could not submit feedback.');
            feedbackMessage.textContent = 'Thank you!';
            feedbackButtonsDiv.classList.add('hidden');
        } catch (error) { feedbackMessage.textContent = `Error: ${error.message}`; feedbackMessage.className = 'error-message'; }
    }
    helpfulButton.addEventListener('click', () => handleFeedback('👍'));
    notHelpfulButton.addEventListener('click', () => handleFeedback('👎'));

    // --- Admin Panel Logic ---
    async function fetchAndDisplayTickets() {
        ticketsTableBody.innerHTML = ''; ticketsTableContainer.classList.add('hidden');
        ticketsLoadingMessage.textContent = 'Loading tickets...'; ticketsLoadingMessage.className = '';
        ticketsLoadingMessage.classList.remove('hidden');
        try {
            const response = await fetch('/admin/recent_tickets', getFetchOptions());
            const tickets = await response.json();
            if (!response.ok) { throw new Error(tickets.detail || 'Failed to fetch tickets.'); }
            if (tickets.length === 0) { ticketsLoadingMessage.textContent = 'No recent tickets found.'; return; }
            tickets.forEach(ticket => {
                const row = document.createElement('tr');
                const timestamp = new Date(ticket.timestamp).toLocaleString();
                row.innerHTML = `<td>${timestamp}</td><td>${ticket.user_email}</td><td class="ticket-question">${ticket.question}</td><td>${ticket.selected_team}</td><td>${ticket.status}</td>`;
                ticketsTableBody.appendChild(row);
            });
            ticketsLoadingMessage.classList.add('hidden'); ticketsTableContainer.classList.remove('hidden');
        } catch (error) { ticketsLoadingMessage.textContent = `Error: ${error.message}`; ticketsLoadingMessage.className = 'error-message'; }
    }

    function clearAdminMessages() {
        if(adminViewPermissionsMessage) {
            adminViewPermissionsMessage.textContent = '';
            adminViewPermissionsMessage.className = '';
        }
        if(adminPermissionsMessage) {
            adminPermissionsMessage.textContent = '';
            adminPermissionsMessage.className = 'error-message';
        }
        if(adminRemoveUserMessage) {
            adminRemoveUserMessage.textContent = '';
            adminRemoveUserMessage.className = 'error-message';
        }
        if(userPermissionsDisplayDiv) {
            userPermissionsDisplayDiv.classList.add('hidden');
        }
    }

    function openAdminModal() { adminModal.showModal(); loadAdminPanelData(); fetchAndDisplayTickets(); }
    function closeAdminModal() { 
        adminModal.close(); 
        clearAdminMessages(); // Clear messages on close
    }
    openAdminPanelButton.addEventListener('click', openAdminModal);
    adminModalCloseBtn.addEventListener('click', closeAdminModal);
    adminModal.addEventListener('close', clearAdminMessages);


    adminNavButtons.forEach(button => {
        button.addEventListener('click', () => {
            const targetPanelId = button.dataset.panel;
            adminNavButtons.forEach(btn => btn.classList.remove('active')); button.classList.add('active');
            adminPanels.forEach(panel => { panel.classList.toggle('active', panel.id === targetPanelId); });
            if (targetPanelId === 'view-tickets-panel') { fetchAndDisplayTickets(); }
        });
    });

    addRoleButton.addEventListener('click', () => {
        const context = roleContextTagInput.value.trim().toUpperCase(); const role = roleNameTagInput.value.trim().toUpperCase();
        if (!context || !role) { alert('Both Context and Role Name must be filled.'); return; }
        if (!contextualRolesObject[context]) { contextualRolesObject[context] = []; }
        if (!contextualRolesObject[context].includes(role)) { contextualRolesObject[context].push(role); }
        contextualRolesPreview.textContent = JSON.stringify(contextualRolesObject, null, 2);
        roleContextTagInput.value = ''; roleNameTagInput.value = ''; roleContextTagInput.focus();
    });

    adminPermissionsForm.addEventListener('submit', async (event) => {
        // UPDATED to clear stale messages
        clearAdminMessages();
        event.preventDefault();
        adminPermissionsMessage.textContent = ''; adminPermissionsMessage.className = 'error-message';
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
            const response = await fetch('/admin/user_permissions', getFetchOptions('POST', { target_email: targetEmail, permissions }));
            const data = await response.json();
            if (!response.ok) throw new Error(data.detail || 'Failed to update permissions.');
            adminPermissionsMessage.textContent = data.message || 'Permissions updated successfully!';
            adminPermissionsMessage.className = 'success-message';
            adminPermissionsForm.reset(); contextualRolesObject = {}; contextualRolesPreview.textContent = '{}';
            if (data.updated_profile) { adminPermissionsMessage.innerHTML += `<br>Updated Profile: <pre>${JSON.stringify(data.updated_profile, null, 2)}</pre>`; }
        } catch (error) { adminPermissionsMessage.textContent = `Error: ${error.message}`; }
    });

    viewPermissionsButton.addEventListener('click', async () => {
        // UPDATED to clear stale messages
        clearAdminMessages();
        adminViewPermissionsMessage.textContent = ''; adminViewPermissionsMessage.className = 'error-message';
        userPermissionsDisplayDiv.classList.add('hidden');
        const targetEmailToView = viewTargetUserEmailInput.value.trim();
        if (!targetEmailToView) { adminViewPermissionsMessage.textContent = 'User Email to view is required.'; return; }
        try {
            const response = await fetch(`/admin/view_user_permissions/${encodeURIComponent(targetEmailToView)}`, getFetchOptions());
            const data = await response.json();
            if (!response.ok) throw new Error(data.detail || 'Failed to fetch permissions.');
            adminViewPermissionsMessage.textContent = 'Permissions fetched successfully.'; adminViewPermissionsMessage.className = 'success-message';
            displayUserEmailSpan.textContent = data.user_email || targetEmailToView;
            displayUserPermissionsJsonPre.textContent = JSON.stringify(data, null, 2);
            userPermissionsDisplayDiv.classList.remove('hidden');
        } catch (error) { adminViewPermissionsMessage.textContent = `Error: ${error.message}`; }
    });

    removeUserButton.addEventListener('click', async () => {
        // UPDATED to clear stale messages
        clearAdminMessages();
        adminRemoveUserMessage.textContent = ''; adminRemoveUserMessage.className = 'error-message';
        const targetEmailToRemove = removeTargetUserEmailInput.value.trim();
        if (!targetEmailToRemove) { adminRemoveUserMessage.textContent = 'User Email to remove is required.'; return; }
        if (!confirm(`Are you sure you want to remove the user '${targetEmailToRemove}'? This action cannot be undone.`)) { return; }
        try {
            const response = await fetch('/admin/remove_user', getFetchOptions('POST', { target_email: targetEmailToRemove }));
            const data = await response.json();
            if (!response.ok) throw new Error(data.detail || 'Failed to remove user.');
            adminRemoveUserMessage.textContent = data.message || 'User removed successfully!';
            adminRemoveUserMessage.className = 'success-message';
            removeTargetUserEmailInput.value = '';
        } catch (error) { adminRemoveUserMessage.textContent = `Error: ${error.message}`; }
    });

    // --- Ticket Modal Logic ---
    openTicketModalButton.addEventListener('click', () => {
        ticketModal.showModal();
        ticketQuestionTextarea.value = currentQuestion || '';
        ticketSubmissionMessage.textContent = ''; teamSuggestionP.textContent = '';
        if (ticketQuestionTextarea.value) { ticketQuestionTextarea.dispatchEvent(new Event('input', { bubbles: true })); }
        else { ticketTeamSelect.innerHTML = '<option value="">Enter question for suggestions</option>'; }
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
                const response = await fetch('/tickets/suggest_team', getFetchOptions('POST', { question_text: questionText }));
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
                } else { ticketTeamSelect.innerHTML = '<option value="">No teams available</option>'; }
            } catch (error) { teamSuggestionP.textContent = `Error: ${error.message}`; }
        }, 500);
    });
    
    submitTicketButton.addEventListener('click', async () => {
        const question_text = ticketQuestionTextarea.value.trim(); const selected_team = ticketTeamSelect.value;
        ticketSubmissionMessage.textContent = ''; ticketSubmissionMessage.className = 'error-message';
        if (!question_text || !selected_team) { ticketSubmissionMessage.textContent = 'Question and team selection are required.'; return; }
        try {
            const body = { question_text: question_text, chat_history_json: JSON.stringify(chatHistory.slice(-5)), selected_team: selected_team };
            const response = await fetch('/tickets/create', getFetchOptions('POST', body));
            const data = await response.json();
            if (!response.ok) throw new Error(data.detail || 'Could not create ticket.');
            ticketSubmissionMessage.textContent = 'Ticket created successfully!';
            ticketSubmissionMessage.className = 'success-message';
            setTimeout(hideTicketModal, 2000);
        } catch (error) { ticketSubmissionMessage.textContent = `Error: ${error.message}`; }
    });
    
    // --- Application Initialization ---
    async function initApp() {
        try {
            const response = await fetch('/auth/me', getFetchOptions('POST'));
            if (!response.ok) { throw new Error("No valid session."); }
            const data = await response.json();
            
            // UPDATED to use refactored function
            if (data.user_profile) {
                console.log("Session validated. Resuming for:", data.user_profile.user_email);
                updateUIForUserProfile(data.user_profile);
_            } else {
                throw new Error("Profile not found in session response.");
            }
        } catch (error) {
            console.log("Initialization check failed:", error.message);
            localStorage.removeItem('knowledgeAssistantProfile');
            currentUserEmail = null; currentUserProfile = null;
            showLogin();
        }
    }
    
    initApp();
});