// static/app.js
document.addEventListener('DOMContentLoaded', () => {

    // ═══════════════════════════════════════════════
    //  Element References
    // ═══════════════════════════════════════════════
    const loginView            = document.getElementById('login-view');
    const chatView             = document.getElementById('chat-view');
    const adminView            = document.getElementById('admin-view');

    // Login
    const emailInput           = document.getElementById('email');
    const loginButton          = document.getElementById('loginButton');
    const loginError           = document.getElementById('login-error');

    // Top bar (populated dynamically)
    const topbarActions        = document.getElementById('topbar-actions');

    // Chat
    const chatMessages         = document.getElementById('chat-messages');
    const welcomeSplash        = document.getElementById('welcome-splash');
    const chatInput            = document.getElementById('chat-input');
    const sendChatButton       = document.getElementById('sendChatButton');
    const postChatBar          = document.getElementById('post-chat-bar');
    const helpfulButton        = document.getElementById('helpfulButton');
    const notHelpfulButton     = document.getElementById('notHelpfulButton');
    const feedbackMessage      = document.getElementById('feedback-message');
    const newChatButton        = document.getElementById('newChatButton');

    // Admin nav
    const closeAdminBtn        = document.getElementById('closeAdminBtn');
    const adminNavBtns         = document.querySelectorAll('.admin-nav-btn');
    const adminPanels          = document.querySelectorAll('.admin-panel');

    // Docs panel
    const docsTableBody        = document.getElementById('docs-tbody');
    const refreshDocsBtn       = document.getElementById('refreshDocsBtn');
    const dropzone             = document.getElementById('dropzone');
    const docFileInput         = document.getElementById('doc-file-input');
    const uploadStatus         = document.getElementById('upload-status');
    const uploadDept           = document.getElementById('upload-dept');
    const uploadLevel          = document.getElementById('upload-level');

    // Tickets panel
    const ticketsStatus        = document.getElementById('tickets-status');
    const ticketsContainer     = document.getElementById('tickets-container');
    const ticketsTbody         = document.getElementById('tickets-tbody');

    // View perms
    const viewEmailInput       = document.getElementById('view-email');
    const viewPermsBtn         = document.getElementById('viewPermsBtn');
    const viewPermsMsg         = document.getElementById('view-perms-msg');
    const permsDisplay         = document.getElementById('perms-display');
    const permsEmailLabel      = document.getElementById('perms-email-label');
    const permsJson            = document.getElementById('perms-json');

    // Manage perms
    const permsForm            = document.getElementById('perms-form');
    const targetEmailInput     = document.getElementById('target-email');
    const targetLevelInput     = document.getElementById('target-level');
    const targetIsAdminInput   = document.getElementById('target-is-admin');
    const deptCheckboxes       = document.getElementById('dept-checkboxes');
    const targetProjectsInput  = document.getElementById('target-projects');
    const roleCtxInput         = document.getElementById('role-ctx');
    const roleNameInput        = document.getElementById('role-name');
    const addRoleBtn           = document.getElementById('addRoleBtn');
    const rolesPreview         = document.getElementById('roles-preview');
    const permsFormMsg         = document.getElementById('perms-form-msg');

    // Remove user
    const removeEmailInput     = document.getElementById('remove-email');
    const removeUserBtn        = document.getElementById('removeUserBtn');
    const removeMsg            = document.getElementById('remove-msg');

    // Ticket modal
    const ticketModal          = document.getElementById('ticket-modal');
    const ticketQuestion       = document.getElementById('ticket-question');
    const ticketTeam           = document.getElementById('ticket-team');
    const teamSuggestion       = document.getElementById('team-suggestion');
    const cancelTicketBtn      = document.getElementById('cancelTicketBtn');
    const submitTicketBtn      = document.getElementById('submitTicketBtn');
    const ticketSubmitMsg      = document.getElementById('ticket-submit-msg');

    // Confirm modal
    const confirmModal         = document.getElementById('confirm-modal');
    const confirmTitle         = document.getElementById('confirm-title');
    const confirmBody          = document.getElementById('confirm-body');
    const confirmOkBtn         = document.getElementById('confirmOkBtn');
    const confirmCancelBtn     = document.getElementById('confirmCancelBtn');

    // ═══════════════════════════════════════════════
    //  State
    // ═══════════════════════════════════════════════
    let currentUser       = null;   // full profile object
    let currentQuestion   = null;
    let currentAnswer     = null;
    let chatHistory       = [];     // { role, content }[]
    let contextualRoles   = {};
    let chatActive        = false;

    // ═══════════════════════════════════════════════
    //  Utilities
    // ═══════════════════════════════════════════════

    /** Centralised fetch helper — always sends the session cookie */
    const api = (method = 'GET', body = null) => ({
        method,
        headers: body instanceof FormData ? undefined : { 'Content-Type': 'application/json' },
        credentials: 'include',
        body: body instanceof FormData ? body : (body ? JSON.stringify(body) : undefined)
    });

    /** Show a toast notification */
    function toast(msg, type = 'info') {
        const container = document.getElementById('toast-container');
        const el = document.createElement('div');
        el.className = `toast ${type}`;
        el.textContent = msg;
        container.appendChild(el);
        setTimeout(() => el.remove(), 4200);
    }

    /** Custom confirm dialog — returns a Promise<boolean> */
    function confirm(title, body) {
        return new Promise(resolve => {
            confirmTitle.textContent = title;
            confirmBody.textContent  = body;
            confirmModal.showModal();
            const cleanup = (result) => {
                confirmModal.close();
                confirmOkBtn.removeEventListener('click', ok);
                confirmCancelBtn.removeEventListener('click', cancel);
                resolve(result);
            };
            const ok     = () => cleanup(true);
            const cancel = () => cleanup(false);
            confirmOkBtn.addEventListener('click', ok);
            confirmCancelBtn.addEventListener('click', cancel);
        });
    }

    /** Status badge helper for tickets */
    function badgeFor(status) {
        const map = {
            'Open':        'badge-open',
            'In Progress': 'badge-progress',
            'Resolved':    'badge-resolved',
            'Closed':      'badge-closed'
        };
        return `<span class="badge ${map[status] || 'badge-closed'}">${status}</span>`;
    }

    /** Convert textarea height to content height */
    function autoResize(el) {
        el.style.height = 'auto';
        el.style.height = `${Math.min(el.scrollHeight, 200)}px`;
    }

    // ═══════════════════════════════════════════════
    //  View Management
    // ═══════════════════════════════════════════════

    function showLogin() {
        loginView.classList.remove('hidden');
        chatView.classList.add('hidden');
        adminView.classList.add('hidden');
        topbarActions.innerHTML = '';
        loginError.textContent = '';
    }

    function showChat() {
        loginView.classList.add('hidden');
        chatView.classList.remove('hidden');
        adminView.classList.add('hidden');
        buildTopBar();
    }

    function showAdmin() {
        loginView.classList.add('hidden');
        chatView.classList.add('hidden');
        adminView.classList.remove('hidden');
        switchAdminPanel('docs-panel');
        loadAdminConfig();
        fetchDocs();
    }

    function buildTopBar() {
        if (!currentUser) return;
        const isAdmin = currentUser.is_admin;
        topbarActions.innerHTML = `
            <div class="user-chip">
                <span class="user-dot"></span>
                <span>${currentUser.user_email}</span>
            </div>
            <button class="btn btn-ghost btn-sm" id="ticketBtn">🎫 Ticket</button>
            ${isAdmin ? `<button class="btn btn-ghost btn-sm" id="adminBtn" style="color:var(--danger);">⚙️ Admin</button>` : ''}
            <button class="btn btn-ghost btn-sm" id="logoutBtn">Sign out</button>
        `;
        document.getElementById('ticketBtn').addEventListener('click', openTicketModal);
        document.getElementById('logoutBtn').addEventListener('click', handleLogout);
        if (isAdmin) document.getElementById('adminBtn').addEventListener('click', showAdmin);
    }

    // ═══════════════════════════════════════════════
    //  Auth
    // ═══════════════════════════════════════════════

    async function initApp() {
        try {
            const res  = await fetch('/auth/me', api('POST'));
            if (!res.ok) throw new Error('No session');
            const data = await res.json();
            if (data.user_profile) {
                currentUser = data.user_profile;
                showChat();
            } else {
                throw new Error('Missing profile');
            }
        } catch {
            showLogin();
        }
    }

    loginButton.addEventListener('click', async () => {
        const email = emailInput.value.trim();
        if (!email) { loginError.textContent = 'Please enter your work email.'; return; }
        loginError.textContent = '';
        loginButton.disabled = true;
        loginButton.textContent = 'Signing in…';
        try {
            const res  = await fetch('/auth/login', api('POST', { email }));
            const data = await res.json();
            if (!res.ok) throw new Error(data.detail || 'Login failed');
            if (!data.user_profile) throw new Error('Incomplete login response');
            currentUser = data.user_profile;
            emailInput.value = '';
            showChat();
        } catch (e) {
            loginError.textContent = e.message;
        } finally {
            loginButton.disabled = false;
            loginButton.textContent = 'Sign In';
        }
    });

    emailInput.addEventListener('keydown', e => { if (e.key === 'Enter') loginButton.click(); });

    async function handleLogout() {
        try { await fetch('/auth/logout', api('POST')); } catch { /* always clear client */ }
        currentUser = null; currentQuestion = null; currentAnswer = null;
        chatHistory = []; chatActive = false;
        chatMessages.innerHTML = '';
        chatMessages.appendChild(welcomeSplash);
        welcomeSplash.classList.remove('hidden');
        postChatBar.classList.add('hidden');
        showLogin();
    }

    // ═══════════════════════════════════════════════
    //  Chat
    // ═══════════════════════════════════════════════

    function createUserMessage(text) {
        const initials = (currentUser?.user_email?.[0] || 'U').toUpperCase();
        const div = document.createElement('div');
        div.className = 'msg msg-user';
        div.innerHTML = `
            <div class="msg-avatar">${initials}</div>
            <div class="msg-body">
                <div class="msg-bubble">${escapeHtml(text)}</div>
            </div>`;
        return div;
    }

    function createAIMessage() {
        const div = document.createElement('div');
        div.className = 'msg msg-ai';
        div.innerHTML = `
            <div class="msg-avatar">AI</div>
            <div class="msg-body">
                <div class="msg-bubble" id="ai-bubble-active">
                    <div class="typing-indicator"><span></span><span></span><span></span></div>
                </div>
                <div class="msg-meta hidden" id="ai-meta-active"></div>
            </div>`;
        return div;
    }

    function escapeHtml(text) {
        return text.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
    }

    function renderMarkdown(raw) {
        try { return marked.parse(raw); } catch { return escapeHtml(raw); }
    }

    const handleSend = async () => {
        const prompt = chatInput.value.trim();
        if (!prompt || !currentUser) return;

        // Activate chat view
        if (!chatActive) {
            chatActive = true;
            welcomeSplash.classList.add('hidden');
        }
        postChatBar.classList.add('hidden');
        feedbackMessage.textContent = '';

        // User message
        const userEl = createUserMessage(prompt);
        chatMessages.appendChild(userEl);
        chatHistory.push({ role: 'user', content: prompt });
        if (chatHistory.length > 40) chatHistory = chatHistory.slice(-40); // cap at 20 exchanges
        currentQuestion = prompt;
        chatInput.value = '';
        chatInput.style.height = 'auto';

        // AI placeholder
        const aiEl = createAIMessage();
        chatMessages.appendChild(aiEl);
        chatMessages.scrollTop = chatMessages.scrollHeight;

        const bubble = document.getElementById('ai-bubble-active');
        const meta   = document.getElementById('ai-meta-active');
        bubble.id    = '';
        meta.id      = '';

        // Disable input
        chatInput.disabled = true;
        sendChatButton.disabled = true;

        let accum = '';
        try {
            const res = await fetch('/rag/chat', api('POST', {
                prompt,
                chat_history: chatHistory.slice(-16)
            }));

            if (!res.ok || !res.body) {
                const err = await res.json().catch(() => ({}));
                throw Object.assign(new Error(err.detail || 'Server error'), { type: 'server' });
            }

            const reader  = res.body.getReader();
            const decoder = new TextDecoder();
            let   buf     = '';

            while (true) {
                const { value, done } = await reader.read();
                if (done) break;
                buf += decoder.decode(value, { stream: true });
                const parts = buf.split('\n\n');
                buf = parts.pop();
                for (const part of parts) {
                    if (!part.startsWith('data: ')) continue;
                    try {
                        const json = JSON.parse(part.slice(6));
                        if (json.answer_chunk) {
                            accum += json.answer_chunk;
                            bubble.innerHTML = renderMarkdown(accum) + '<span class="cursor-blink">▌</span>';
                            chatMessages.scrollTop = chatMessages.scrollHeight;
                        }
                        if (json.sources && json.sources.length > 0) {
                            const pills = json.sources.map(s => `<span class="source-pill">${escapeHtml(s)}</span>`).join('');
                            meta.classList.remove('hidden');
                            meta.innerHTML = `
                                <button class="copy-btn" title="Copy answer" data-answer="">📋 Copy</button>
                                <div class="sources"><span class="sources-label">Sources:</span>${pills}</div>`;
                            meta.querySelector('.copy-btn').dataset.answer = accum;
                            meta.querySelector('.copy-btn').addEventListener('click', handleCopyClick);
                        }
                        if (json.error) {
                            bubble.innerHTML = `<span class="text-danger">⚠ ${escapeHtml(json.error)}</span>`;
                        }
                    } catch { /* malformed event, skip */ }
                }
            }

            // Finalise
            if (accum) {
                bubble.innerHTML = renderMarkdown(accum);
                // Ensure copy button references final answer
                const copyBtn = meta.querySelector('.copy-btn');
                if (copyBtn) copyBtn.dataset.answer = accum;
            } else if (bubble.querySelector('.typing-indicator')) {
                // No content arrived — LLM found no relevant docs
                bubble.innerHTML = `<span class="text-muted">ℹ I couldn't find a relevant answer in the documents available to you.</span>`;
            }

            currentAnswer = accum;
            chatHistory.push({ role: 'assistant', content: accum });
            postChatBar.classList.remove('hidden');

        } catch (err) {
            const isNoDoc = err.message?.toLowerCase().includes('no relevant');
            bubble.innerHTML = isNoDoc
                ? `<span class="text-muted">ℹ I couldn't find a relevant answer in the documents available to you.</span>`
                : `<span class="text-danger">⚠ ${escapeHtml(err.message || 'An unexpected error occurred.')}</span>`;
            currentAnswer = null;
        } finally {
            chatInput.disabled = false;
            sendChatButton.disabled = false;
            chatInput.focus();
        }
    };

    sendChatButton.addEventListener('click', handleSend);
    chatInput.addEventListener('keydown', e => {
        if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); handleSend(); }
    });
    chatInput.addEventListener('input', () => autoResize(chatInput));

    newChatButton.addEventListener('click', () => {
        chatHistory = [];
        chatActive  = false;
        currentQuestion = null;
        currentAnswer   = null;
        chatMessages.innerHTML = '';
        chatMessages.appendChild(welcomeSplash);
        welcomeSplash.classList.remove('hidden');
        postChatBar.classList.add('hidden');
        feedbackMessage.textContent = '';
    });

    function handleCopyClick(e) {
        const btn = e.currentTarget;
        const text = btn.dataset.answer;
        navigator.clipboard.writeText(text).then(() => {
            btn.textContent = '✓ Copied';
            btn.classList.add('copied');
            setTimeout(() => { btn.textContent = '📋 Copy'; btn.classList.remove('copied'); }, 2000);
        });
    }

    // ═══════════════════════════════════════════════
    //  Feedback
    // ═══════════════════════════════════════════════

    async function submitFeedback(type) {
        if (!currentQuestion || !currentAnswer) return;
        try {
            const res = await fetch('/feedback/record', api('POST', {
                question: currentQuestion,
                answer: currentAnswer,
                feedback_type: type
            }));
            if (!res.ok) throw new Error('Failed');
            feedbackMessage.textContent = 'Thanks for your feedback!';
            feedbackMessage.className   = 'text-success';
            helpfulButton.disabled    = true;
            notHelpfulButton.disabled = true;
        } catch {
            feedbackMessage.textContent = 'Could not record feedback.';
            feedbackMessage.className   = 'text-danger';
        }
    }

    helpfulButton.addEventListener('click',    () => submitFeedback('👍'));
    notHelpfulButton.addEventListener('click', () => submitFeedback('👎'));

    // ═══════════════════════════════════════════════
    //  Ticket Modal
    // ═══════════════════════════════════════════════

    function openTicketModal() {
        ticketQuestion.value        = currentQuestion || '';
        ticketSubmitMsg.textContent = '';
        teamSuggestion.textContent  = '';
        ticketTeam.innerHTML        = '<option value="">Type your issue for a suggestion</option>';
        ticketModal.showModal();
        if (ticketQuestion.value) ticketQuestion.dispatchEvent(new Event('input', { bubbles: true }));
    }

    cancelTicketBtn.addEventListener('click', () => { ticketModal.close(); });

    let teamSuggestTimeout;
    ticketQuestion.addEventListener('input', () => {
        clearTimeout(teamSuggestTimeout);
        const text = ticketQuestion.value.trim();
        if (!text) { ticketTeam.innerHTML = '<option value="">Type your issue for a suggestion</option>'; return; }
        ticketTeam.innerHTML = '<option value="">Loading…</option>';
        teamSuggestTimeout = setTimeout(async () => {
            try {
                const res  = await fetch('/tickets/suggest_team', api('POST', { question_text: text }));
                const data = await res.json();
                if (!res.ok) throw new Error(data.detail || 'Failed');
                ticketTeam.innerHTML = '';
                (data.available_teams || []).forEach(team => {
                    const opt = document.createElement('option');
                    opt.value = team; opt.textContent = team;
                    if (team === data.suggested_team) opt.selected = true;
                    ticketTeam.appendChild(opt);
                });
                teamSuggestion.textContent = data.suggested_team ? `Suggested: ${data.suggested_team}` : '';
            } catch (e) {
                teamSuggestion.textContent = `Error: ${e.message}`;
            }
        }, 500);
    });

    submitTicketBtn.addEventListener('click', async () => {
        const question_text  = ticketQuestion.value.trim();
        const selected_team  = ticketTeam.value;
        ticketSubmitMsg.textContent = '';
        if (!question_text || !selected_team) {
            ticketSubmitMsg.textContent = 'Please fill in the question and select a team.';
            ticketSubmitMsg.className   = 'text-danger';
            return;
        }
        try {
            const res  = await fetch('/tickets/create', api('POST', {
                question_text,
                selected_team,
                chat_history: chatHistory.slice(-5)
            }));
            const data = await res.json();
            if (!res.ok) throw new Error(data.detail || 'Failed');
            ticketSubmitMsg.textContent = '✓ Ticket created successfully!';
            ticketSubmitMsg.className   = 'text-success';
            setTimeout(() => ticketModal.close(), 1800);
        } catch (e) {
            ticketSubmitMsg.textContent = e.message;
            ticketSubmitMsg.className   = 'text-danger';
        }
    });

    // ═══════════════════════════════════════════════
    //  Admin: Navigation
    // ═══════════════════════════════════════════════

    closeAdminBtn.addEventListener('click', showChat);

    function switchAdminPanel(panelId) {
        adminNavBtns.forEach(b => b.classList.toggle('active', b.dataset.panel === panelId));
        adminPanels.forEach(p => {
            const show = p.id === panelId;
            p.classList.toggle('active', show);
            p.style.display = show ? '' : 'none';
        });
        if (panelId === 'tickets-panel') fetchTickets();
    }

    adminNavBtns.forEach(btn => {
        btn.addEventListener('click', () => switchAdminPanel(btn.dataset.panel));
    });

    // ═══════════════════════════════════════════════
    //  Admin: Config Tags (departments)
    // ═══════════════════════════════════════════════

    async function loadAdminConfig() {
        try {
            const res  = await fetch('/admin/config_tags', api());
            if (!res.ok) return;
            const data = await res.json();
            const tags = data.known_department_tags || [];

            // Populate upload select
            uploadDept.innerHTML = tags.map(t => `<option value="${t}">${t}</option>`).join('');

            // Populate manage-perms checkboxes
            deptCheckboxes.innerHTML = tags.map(t => `
                <label class="check-item">
                    <input type="checkbox" name="departments" value="${t}">
                    <span>${t}</span>
                </label>`).join('');
        } catch { /* non-fatal */ }
    }

    // ═══════════════════════════════════════════════
    //  Admin: Documents
    // ═══════════════════════════════════════════════

    refreshDocsBtn.addEventListener('click', fetchDocs);

    async function fetchDocs() {
        docsTableBody.innerHTML = '<tr><td colspan="4" style="text-align:center;padding:1.5rem;color:var(--text-muted)">Loading…</td></tr>';
        try {
            const res  = await fetch('/admin/documents', api());
            if (!res.ok) throw new Error('Failed to fetch documents');
            const data = await res.json();
            const docs = data.documents || [];
            if (docs.length === 0) {
                docsTableBody.innerHTML = '<tr><td colspan="4" style="text-align:center;padding:1.5rem;color:var(--text-muted)">No documents indexed yet.</td></tr>';
                return;
            }
            docsTableBody.innerHTML = docs.map(doc => {
                const kb   = (doc.size / 1024).toFixed(1);
                const date = new Date(doc.last_modified).toLocaleDateString();
                return `<tr>
                    <td>${escapeHtml(doc.filename)}</td>
                    <td>${kb} KB</td>
                    <td>${date}</td>
                    <td style="text-align:right">
                        <button class="btn btn-danger btn-sm" data-filename="${escapeHtml(doc.filename)}">Delete</button>
                    </td>
                </tr>`;
            }).join('');

            docsTableBody.querySelectorAll('[data-filename]').forEach(btn => {
                btn.addEventListener('click', async () => {
                    const filename = btn.dataset.filename;
                    const ok = await confirm('Delete Document', `Permanently delete "${filename}"? This will also remove its vectors from Pinecone.`);
                    if (!ok) return;
                    try {
                        const res = await fetch(`/admin/documents/${encodeURIComponent(filename)}`, api('DELETE'));
                        if (!res.ok) throw new Error('Delete failed');
                        toast(`"${filename}" deleted`, 'success');
                        fetchDocs();
                    } catch (e) {
                        toast(e.message, 'error');
                    }
                });
            });
        } catch (e) {
            docsTableBody.innerHTML = `<tr><td colspan="4" style="text-align:center;color:var(--danger);padding:1.5rem;">${escapeHtml(e.message)}</td></tr>`;
        }
    }

    async function uploadDocument(file) {
        if (!file) return;
        uploadStatus.textContent = '⬆ Uploading…';
        uploadStatus.className   = 'text-muted';
        const formData = new FormData();
        formData.append('file', file);
        formData.append('department', uploadDept.value || 'GENERAL');
        formData.append('hierarchy_level', uploadLevel.value || '0');
        try {
            const res = await fetch('/admin/documents', { method: 'POST', body: formData, credentials: 'include' });
            if (!res.ok) throw new Error('Upload failed');
            uploadStatus.textContent = '✓ Uploaded — sync started in background';
            uploadStatus.className   = 'text-success';
            toast('Document uploaded and sync started', 'success');
            setTimeout(() => { uploadStatus.textContent = ''; }, 4000);
            fetchDocs();
        } catch (e) {
            uploadStatus.textContent = `✗ ${e.message}`;
            uploadStatus.className   = 'text-danger';
        }
    }

    // Dropzone events
    dropzone.addEventListener('click', () => docFileInput.click());
    dropzone.addEventListener('keydown', e => { if (e.key === 'Enter' || e.key === ' ') docFileInput.click(); });
    docFileInput.addEventListener('change', e => {
        if (e.target.files.length) uploadDocument(e.target.files[0]);
        e.target.value = '';
    });
    dropzone.addEventListener('dragover',  e => { e.preventDefault(); dropzone.classList.add('drag-over'); });
    dropzone.addEventListener('dragleave', e => { e.preventDefault(); dropzone.classList.remove('drag-over'); });
    dropzone.addEventListener('drop', e => {
        e.preventDefault();
        dropzone.classList.remove('drag-over');
        if (e.dataTransfer.files.length) uploadDocument(e.dataTransfer.files[0]);
    });

    // ═══════════════════════════════════════════════
    //  Admin: Tickets
    // ═══════════════════════════════════════════════

    async function fetchTickets() {
        ticketsStatus.textContent = 'Loading tickets…';
        ticketsStatus.className   = 'text-muted';
        ticketsContainer.classList.add('hidden');

        try {
            const res     = await fetch('/admin/recent_tickets', api());
            const tickets = await res.json();
            if (!res.ok) throw new Error(tickets.detail || 'Failed to fetch tickets');

            if (tickets.length === 0) {
                ticketsStatus.textContent = 'No tickets found.';
                return;
            }

            ticketsStatus.classList.add('hidden');
            ticketsContainer.classList.remove('hidden');

            ticketsTbody.innerHTML = tickets.map(t => {
                const ts = new Date(t.timestamp).toLocaleString();
                return `
                <tr class="ticket-row" data-ticket-id="${t.id}" data-user-email="${escapeHtml(t.user_email)}" data-question="${escapeHtml(t.question)}">
                    <td>#${t.id}</td>
                    <td style="white-space:nowrap">${ts}</td>
                    <td>${escapeHtml(t.user_email)}</td>
                    <td class="td-wrap">${escapeHtml(t.question)}</td>
                    <td>${escapeHtml(t.selected_team)}</td>
                    <td class="badge-cell">${badgeFor(t.status)}</td>
                    <td>
                        <select class="ticket-status-select" style="width:120px;padding:.3rem .5rem;font-size:.8rem;" data-ticket-id="${t.id}">
                            <option value="Open"        ${t.status==='Open'        ? 'selected' : ''}>Open</option>
                            <option value="In Progress" ${t.status==='In Progress' ? 'selected' : ''}>In Progress</option>
                            <option value="Resolved"    ${t.status==='Resolved'    ? 'selected' : ''}>Resolved</option>
                            <option value="Closed"      ${t.status==='Closed'      ? 'selected' : ''}>Closed</option>
                        </select>
                    </td>
                    <td>
                        <button class="btn btn-ghost btn-sm reply-toggle-btn" data-ticket-id="${t.id}">✉ Reply</button>
                    </td>
                </tr>
                <tr class="reply-panel-row hidden" id="reply-panel-${t.id}">
                    <td colspan="9" style="background:var(--surface-2);padding:1rem 1.5rem;border-bottom:2px solid var(--border);">
                        <div style="max-width:680px;">
                            <div class="reply-history" id="reply-history-${t.id}" style="margin-bottom:.75rem;display:flex;flex-direction:column;gap:.5rem;"></div>
                            <label style="font-size:.8rem;color:var(--text-muted);margin-bottom:.35rem;display:block;">
                                Reply to <strong>${escapeHtml(t.user_email)}</strong>
                                <span style="font-weight:400;color:var(--text-dim);"> — will be sent as email and continue the ticket thread</span>
                            </label>
                            <textarea id="reply-text-${t.id}" rows="3"
                                style="width:100%;resize:vertical;background:var(--surface);border:1px solid var(--border);border-radius:var(--radius);padding:.6rem .85rem;color:var(--text);font-family:var(--font);font-size:.875rem;margin-bottom:.5rem;"
                                placeholder="Type your reply…"></textarea>
                            <div style="display:flex;gap:.5rem;align-items:center;">
                                <button class="btn btn-primary btn-sm send-reply-btn" data-ticket-id="${t.id}" data-user-email="${escapeHtml(t.user_email)}">Send Reply</button>
                                <button class="btn btn-ghost btn-sm close-reply-btn" data-ticket-id="${t.id}">Cancel</button>
                                <span class="reply-status-${t.id}" style="font-size:.8rem;margin-left:.25rem;"></span>
                            </div>
                        </div>
                    </td>
                </tr>`;
            }).join('');

            // ── Status update ──
            ticketsTbody.querySelectorAll('.ticket-status-select').forEach(sel => {
                sel.addEventListener('change', async () => {
                    const id     = sel.dataset.ticketId;
                    const status = sel.value;
                    try {
                        const res = await fetch(`/admin/tickets/${id}`, api('PATCH', { status }));
                        if (!res.ok) throw new Error('Update failed');
                        sel.closest('tr').querySelector('.badge-cell').innerHTML = badgeFor(status);
                        toast(`Ticket #${id} → ${status}`, 'success');
                    } catch (e) {
                        toast(e.message, 'error');
                        fetchTickets();
                    }
                });
            });

            // ── Toggle reply panel ──
            ticketsTbody.querySelectorAll('.reply-toggle-btn').forEach(btn => {
                btn.addEventListener('click', async () => {
                    const id    = btn.dataset.ticketId;
                    const panel = document.getElementById(`reply-panel-${id}`);
                    const open  = !panel.classList.contains('hidden');
                    if (open) {
                        panel.classList.add('hidden');
                        btn.textContent = '✉ Reply';
                    } else {
                        panel.classList.remove('hidden');
                        btn.textContent = '▲ Hide';
                        loadReplyHistory(id);
                        document.getElementById(`reply-text-${id}`)?.focus();
                    }
                });
            });

            // ── Close reply panel ──
            ticketsTbody.querySelectorAll('.close-reply-btn').forEach(btn => {
                btn.addEventListener('click', () => {
                    const panel = document.getElementById(`reply-panel-${btn.dataset.ticketId}`);
                    panel?.classList.add('hidden');
                    ticketsTbody.querySelector(`.reply-toggle-btn[data-ticket-id="${btn.dataset.ticketId}"]`).textContent = '✉ Reply';
                });
            });

            // ── Send reply ──
            ticketsTbody.querySelectorAll('.send-reply-btn').forEach(btn => {
                btn.addEventListener('click', async () => {
                    const id         = btn.dataset.ticketId;
                    const userEmail  = btn.dataset.userEmail;
                    const textarea   = document.getElementById(`reply-text-${id}`);
                    const statusSpan = document.querySelector(`.reply-status-${id}`);
                    const text = textarea?.value.trim();
                    if (!text) { statusSpan.textContent = 'Reply cannot be empty.'; statusSpan.className = `reply-status-${id} text-danger`; return; }

                    btn.disabled = true;
                    statusSpan.textContent = 'Sending…';
                    statusSpan.className   = `reply-status-${id} text-muted`;

                    try {
                        const res  = await fetch(`/admin/tickets/${id}/reply`, api('POST', { reply_text: text }));
                        const data = await res.json();
                        if (!res.ok) throw new Error(data.detail || 'Failed');

                        textarea.value = '';
                        if (data.email_sent) {
                            statusSpan.textContent = `✓ Sent to ${userEmail}`;
                            statusSpan.className   = `reply-status-${id} text-success`;
                            toast(`Reply sent to ${userEmail}`, 'success');
                        } else {
                            statusSpan.textContent = '⚠ Saved but email not sent — check SMTP config';
                            statusSpan.className   = `reply-status-${id} text-danger`;
                            toast('Reply saved but email failed — check SMTP settings', 'error');
                        }
                        loadReplyHistory(id);
                    } catch (e) {
                        statusSpan.textContent = e.message;
                        statusSpan.className   = `reply-status-${id} text-danger`;
                    } finally {
                        btn.disabled = false;
                    }
                });
            });

        } catch (e) {
            ticketsStatus.textContent = `Error: ${e.message}`;
            ticketsStatus.className   = 'text-danger';
        }
    }

    async function loadReplyHistory(ticketId) {
        const container = document.getElementById(`reply-history-${ticketId}`);
        if (!container) return;
        try {
            const res  = await fetch(`/admin/tickets/${ticketId}/replies`, api());
            const data = await res.json();
            if (!res.ok || !data.replies?.length) { container.innerHTML = ''; return; }
            container.innerHTML = data.replies.map(r => {
                const ts      = new Date(r.timestamp).toLocaleString();
                const sentTag = r.email_sent
                    ? `<span class="badge badge-resolved" style="font-size:.7rem;">✓ emailed</span>`
                    : `<span class="badge badge-closed"   style="font-size:.7rem;">not sent</span>`;
                return `<div style="background:var(--surface);border:1px solid var(--border);border-left:3px solid var(--primary);border-radius:var(--radius);padding:.65rem .9rem;">
                    <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:.35rem;font-size:.78rem;color:var(--text-muted);">
                        <span><strong style="color:var(--text);">${escapeHtml(r.admin_email)}</strong> · ${ts}</span>
                        ${sentTag}
                    </div>
                    <p style="margin:0;font-size:.875rem;white-space:pre-wrap;">${escapeHtml(r.reply_text)}</p>
                </div>`;
            }).join('');
        } catch { container.innerHTML = ''; }
    }

    // ═══════════════════════════════════════════════
    //  Admin: View Permissions
    // ═══════════════════════════════════════════════

    viewPermsBtn.addEventListener('click', async () => {
        const email = viewEmailInput.value.trim();
        if (!email) { viewPermsMsg.textContent = 'Please enter an email.'; viewPermsMsg.className = 'text-danger'; return; }
        viewPermsMsg.textContent = 'Loading…'; viewPermsMsg.className = 'text-muted';
        permsDisplay.classList.add('hidden');
        try {
            const res  = await fetch(`/admin/view_user_permissions/${encodeURIComponent(email)}`, api());
            const data = await res.json();
            if (!res.ok) throw new Error(data.detail || 'Not found');
            viewPermsMsg.textContent = '✓ Found';
            viewPermsMsg.className   = 'text-success';
            permsEmailLabel.textContent = data.user_email || email;
            permsJson.textContent = JSON.stringify(data, null, 2);
            permsDisplay.classList.remove('hidden');
        } catch (e) {
            viewPermsMsg.textContent = e.message;
            viewPermsMsg.className   = 'text-danger';
        }
    });

    viewEmailInput.addEventListener('keydown', e => { if (e.key === 'Enter') viewPermsBtn.click(); });

    // ═══════════════════════════════════════════════
    //  Admin: Manage Permissions
    // ═══════════════════════════════════════════════

    addRoleBtn.addEventListener('click', () => {
        const ctx  = roleCtxInput.value.trim().toUpperCase();
        const role = roleNameInput.value.trim().toUpperCase();
        if (!ctx || !role) { toast('Both context and role are required', 'error'); return; }
        if (!contextualRoles[ctx]) contextualRoles[ctx] = [];
        if (!contextualRoles[ctx].includes(role)) contextualRoles[ctx].push(role);
        rolesPreview.textContent = JSON.stringify(contextualRoles, null, 2);
        roleCtxInput.value = ''; roleNameInput.value = ''; roleCtxInput.focus();
    });

    permsForm.addEventListener('submit', async e => {
        e.preventDefault();
        permsFormMsg.textContent = '';
        const targetEmail = targetEmailInput.value.trim();
        if (!targetEmail) { permsFormMsg.textContent = 'Target email is required.'; permsFormMsg.className = 'text-danger'; return; }

        const permissions = {};
        const level = targetLevelInput.value;
        if (level !== '') permissions.user_hierarchy_level = parseInt(level, 10);
        permissions.is_admin = targetIsAdminInput.checked;
        permissions.departments = Array.from(deptCheckboxes.querySelectorAll('input:checked')).map(i => i.value);
        const projStr = targetProjectsInput.value.trim();
        permissions.projects_membership = projStr ? projStr.split(',').map(p => p.trim().toUpperCase()).filter(Boolean) : [];
        if (Object.keys(contextualRoles).length > 0) permissions.contextual_roles = contextualRoles;

        try {
            const res  = await fetch('/admin/user_permissions', api('POST', { target_email: targetEmail, permissions }));
            const data = await res.json();
            if (!res.ok) throw new Error(data.detail || 'Update failed');
            permsFormMsg.textContent = data.message || 'Permissions updated!';
            permsFormMsg.className   = 'text-success';
            toast('Permissions updated', 'success');
            permsForm.reset();
            contextualRoles = {};
            rolesPreview.textContent = '{}';
        } catch (e) {
            permsFormMsg.textContent = e.message;
            permsFormMsg.className   = 'text-danger';
        }
    });

    // ═══════════════════════════════════════════════
    //  Admin: Remove User
    // ═══════════════════════════════════════════════

    removeUserBtn.addEventListener('click', async () => {
        const email = removeEmailInput.value.trim();
        if (!email) { removeMsg.textContent = 'Email is required.'; removeMsg.className = 'text-danger'; return; }
        const ok = await confirm('Remove User', `Permanently remove "${email}"? This cannot be undone.`);
        if (!ok) return;
        try {
            const res  = await fetch('/admin/remove_user', api('POST', { target_email: email }));
            const data = await res.json();
            if (!res.ok) throw new Error(data.detail || 'Failed');
            removeMsg.textContent = data.message || 'User removed.';
            removeMsg.className   = 'text-success';
            removeEmailInput.value = '';
            toast(`User "${email}" removed`, 'success');
        } catch (e) {
            removeMsg.textContent = e.message;
            removeMsg.className   = 'text-danger';
        }
    });

    // ═══════════════════════════════════════════════
    //  Boot
    // ═══════════════════════════════════════════════
    initApp();
});