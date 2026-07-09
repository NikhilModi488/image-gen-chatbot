document.addEventListener('DOMContentLoaded', () => {
  // DOM Elements
  const promptInput = document.getElementById('promptInput');
  const inputForm = document.getElementById('inputForm');
  const messagesContainer = document.getElementById('messagesContainer');
  const refineToggle = document.getElementById('refineToggle');
  const ollamaStatusDot = document.getElementById('ollamaStatusDot');
  const ollamaStatusText = document.getElementById('ollamaStatusText');
  const activeEngineText = document.getElementById('activeEngineText');
  const historyList = document.getElementById('historyList');
  const clearHistoryBtn = document.getElementById('clearHistoryBtn');
  const newChatBtn = document.getElementById('newChatBtn');
  const modelSelect = document.getElementById('modelSelect');
  const geminiKeyCard = document.getElementById('geminiKeyCard');
  const geminiApiKeyInput = document.getElementById('geminiApiKeyInput');
  
  // Modal Elements
  const imageModal = document.getElementById('imageModal');
  const modalImg = document.getElementById('modalImg');
  const modalPrompt = document.getElementById('modalPrompt');
  const modalDownload = document.getElementById('modalDownload');
  const closeModalBtn = document.getElementById('closeModalBtn');

  // Application State
  let conversations = []; // Array of { id, title, timestamp, messages: [] }
  let activeConversationId = null;
  let isGenerating = false;

  // Initialize Welcome Message template
  const welcomeHtml = messagesContainer.innerHTML;

  // Load state
  loadConversationsFromStorage();
  checkBackendStatus();
  setupEventListeners();

  // 1. Setup Event Listeners
  function setupEventListeners() {
    inputForm.addEventListener('submit', handleFormSubmit);

    promptInput.addEventListener('input', autoResizeTextarea);
    promptInput.addEventListener('keydown', (e) => {
      if (e.key === 'Enter' && !e.shiftKey) {
        e.preventDefault();
        inputForm.requestSubmit();
      }
    });

    // Delegate suggestion chip clicks (handles dynamic chips)
    document.addEventListener('click', (e) => {
      if (e.target.classList.contains('suggestion-chip')) {
        promptInput.value = e.target.textContent;
        autoResizeTextarea();
        promptInput.focus();
      }
    });

    clearHistoryBtn.addEventListener('click', clearAllConversations);
    newChatBtn.addEventListener('click', startNewChat);

    closeModalBtn.addEventListener('click', closeModal);
    imageModal.addEventListener('click', (e) => {
      if (e.target === imageModal) closeModal();
    });

    // Gemini API key state sync
    const savedGeminiKey = localStorage.getItem('aetherimage_gemini_key') || '';
    geminiApiKeyInput.value = savedGeminiKey;
    
    geminiApiKeyInput.addEventListener('input', () => {
      localStorage.setItem('aetherimage_gemini_key', geminiApiKeyInput.value);
    });

    function updateGeminiKeyVisibility() {
      if (modelSelect.value === 'gemini-3.1-flash-image') {
        geminiKeyCard.style.display = 'block';
      } else {
        geminiKeyCard.style.display = 'none';
      }
    }
    modelSelect.addEventListener('change', updateGeminiKeyVisibility);
    updateGeminiKeyVisibility(); // Initial trigger

    document.addEventListener('keydown', (e) => {
      if (e.key === 'Escape') closeModal();
    });
  }

  function autoResizeTextarea() {
    promptInput.style.height = 'auto';
    promptInput.style.height = (promptInput.scrollHeight) + 'px';
  }

  // 2. Fetch Backend Status
  async function checkBackendStatus() {
    try {
      const response = await fetch('/api/status');
      if (!response.ok) throw new Error('Status endpoint failed');
      const data = await response.json();

      if (data.success) {
        if (data.ollama.available) {
          ollamaStatusDot.className = 'status-dot online';
          ollamaStatusText.textContent = `Ollama Online (${data.ollama.refinementModel})`;
          refineToggle.disabled = false;
          refineToggle.checked = true; // Enable prompt refinement by default when Ollama is available
        } else {
          ollamaStatusDot.className = 'status-dot offline';
          ollamaStatusText.textContent = 'Ollama Offline';
          refineToggle.checked = false;
          refineToggle.disabled = true;
        }

        let engineName = 'Local SVG';
        if (data.generator.provider === 'ollama') engineName = 'Ollama Local';
        else if (data.generator.provider === 'pollinations') engineName = 'Pollinations AI';
        
        activeEngineText.textContent = engineName;
      }
    } catch (error) {
      console.error('Failed to query backend status:', error);
      ollamaStatusDot.className = 'status-dot offline';
      ollamaStatusText.textContent = 'Server Unreachable';
      activeEngineText.textContent = 'Offline';
      refineToggle.disabled = true;
    }
  }

  // 3. Start New Chat Session
  function startNewChat() {
    activeConversationId = null;
    messagesContainer.innerHTML = welcomeHtml;
    // Remove active highlight from sidebar items
    document.querySelectorAll('.history-item').forEach(item => {
      item.classList.remove('active-chat');
    });
    promptInput.value = '';
    promptInput.focus();
    autoResizeTextarea();
  }

  // 4. Handle Generation Requests
  async function handleFormSubmit(e) {
    e.preventDefault();
    const prompt = promptInput.value.trim();
    if (!prompt || isGenerating) return;

    isGenerating = true;
    promptInput.value = '';
    promptInput.disabled = true;
    promptInput.style.height = 'auto';
    
    const sendBtn = document.getElementById('sendBtn');
    sendBtn.disabled = true;

    // Check if this is the first message of a new conversation
    let currentConv = null;
    if (activeConversationId === null) {
      // Clear the welcome card
      messagesContainer.innerHTML = '';
      
      // Create new conversation
      activeConversationId = 'chat-' + Date.now();
      currentConv = {
        id: activeConversationId,
        title: prompt, // Title is the first user prompt
        timestamp: Date.now(),
        messages: []
      };
      conversations.unshift(currentConv);
    } else {
      currentConv = conversations.find(c => c.id === activeConversationId);
    }

    // Append User Message to UI and History state
    appendUserMessage(prompt);
    currentConv.messages.push({ role: 'user', content: prompt });
    saveConversationsToStorage();
    renderConversationsSidebar();
    scrollToBottom();

    // Get seed from the last assistant message in history (if it exists) to lock seed consistency
    const lastAssistantMsg = currentConv.messages.slice().reverse().find(m => m.role === 'assistant');
    const activeSeed = lastAssistantMsg ? lastAssistantMsg.seed : null;

    // Prepare history payload for context-aware refinement
    // We only pass messages preceding the current one
    const historyPayload = currentConv.messages.slice(0, -1).map(msg => ({
      role: msg.role,
      content: msg.content,
      refinedPrompt: msg.refinedPrompt || null
    }));

    // Add Bot Loading indicator
    const loaderId = appendBotLoader();
    scrollToBottom();

    try {
      const selectedModel = modelSelect.value;
      const response = await fetch('/api/generate', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          prompt: prompt,
          refine: refineToggle.checked,
          history: historyPayload,
          model: selectedModel,
          geminiApiKey: geminiApiKeyInput.value,
          seed: activeSeed
        })
      });

      const result = await response.json();
      removeLoader(loaderId);

      if (result.success) {
        const generationData = result.data;
        
        // Background pre-load for smooth fade-in
        if (generationData.image) {
          await preloadImage(generationData.image);
        }

        // Append Bot Response
        appendBotMessage(generationData);
        
        // Add to history
        currentConv.messages.push({
          role: 'assistant',
          content: generationData.isGreeting ? generationData.message : `Here is your generated image for: "${generationData.originalPrompt}"`,
          image: generationData.image || null,
          isGreeting: generationData.isGreeting || false,
          source: generationData.source,
          duration: generationData.duration,
          refinedPrompt: generationData.refinedPrompt,
          originalPrompt: generationData.originalPrompt,
          model: selectedModel,
          seed: generationData.seed
        });

        saveConversationsToStorage();
        renderConversationsSidebar();
      } else {
        appendErrorMessage(result.error || 'An error occurred during generation.');
      }
    } catch (error) {
      console.error('Error during generation:', error);
      removeLoader(loaderId);
      appendErrorMessage('Failed to connect to the backend server.');
    } finally {
      isGenerating = false;
      promptInput.disabled = false;
      sendBtn.disabled = false;
      promptInput.focus();
      scrollToBottom();
      checkBackendStatus();
    }
  }

  function preloadImage(src) {
    return new Promise((resolve) => {
      const img = new Image();
      img.src = src;
      img.onload = () => resolve(src);
      img.onerror = () => resolve(src);
    });
  }

  // 5. Message Render Helpers
  function appendUserMessage(text) {
    const timestamp = getFormattedTime();
    const messageHtml = `
      <div class="message user-message slide-in">
        <div class="message-avatar">
          <i data-lucide="user"></i>
        </div>
        <div class="message-content">
          <div class="message-bubble">
            <p>${escapeHTML(text)}</p>
          </div>
          <span class="message-time">${timestamp}</span>
        </div>
      </div>
    `;
    messagesContainer.insertAdjacentHTML('beforeend', messageHtml);
    lucide.createIcons();
  }

  function appendBotLoader() {
    const loaderId = 'loader-' + Date.now();
    const loaderHtml = `
      <div class="message bot-message slide-in" id="${loaderId}">
        <div class="message-avatar">
          <i data-lucide="wand-2"></i>
        </div>
        <div class="message-content">
          <div class="message-bubble">
            <div class="typing-indicator">
              <span></span>
              <span></span>
              <span></span>
            </div>
            <p style="font-size: 12px; margin-top: 4px; color: var(--text-muted)">Generating your image...</p>
            <div class="loader-card">
              <i data-lucide="compass"></i>
              <span style="font-size: 11px; font-weight: 500;">Synthesizing pixels...</span>
            </div>
          </div>
        </div>
      </div>
    `;
    messagesContainer.insertAdjacentHTML('beforeend', loaderHtml);
    lucide.createIcons();
    return loaderId;
  }

  function removeLoader(loaderId) {
    const loader = document.getElementById(loaderId);
    if (loader) loader.remove();
  }

  function appendBotMessage(data) {
    const timestamp = getFormattedTime();

    // If this is a conversational greeting/question reply, render text-only
    if (data.isGreeting) {
      const messageHtml = `
        <div class="message bot-message slide-in">
          <div class="message-avatar">
            <i data-lucide="wand-2"></i>
          </div>
          <div class="message-content">
            <div class="message-bubble">
              <p>${escapeHTML(data.message)}</p>
            </div>
            <span class="message-time">${timestamp}</span>
          </div>
        </div>
      `;
      messagesContainer.insertAdjacentHTML('beforeend', messageHtml);
      lucide.createIcons();
      return;
    }

    const metadataHtml = `
      <div class="image-metadata-card">
        <div class="metadata-item">
          <span class="metadata-label">Engine:</span>
          <span class="metadata-val">${escapeHTML(data.source)}</span>
        </div>
        <div class="metadata-item">
          <span class="metadata-label">Latency:</span>
          <span class="metadata-val">${(data.duration / 1000).toFixed(2)}s</span>
        </div>
        ${data.refinedPrompt ? `
        <div class="metadata-item">
          <span class="metadata-label">Ollama Refined:</span>
          <span class="metadata-val refined-text">"${escapeHTML(data.refinedPrompt)}"</span>
        </div>
        ` : ''}
      </div>
    `;

    const messageHtml = `
      <div class="message bot-message slide-in">
        <div class="message-avatar">
          <i data-lucide="wand-2"></i>
        </div>
        <div class="message-content">
          <div class="message-bubble">
            <p>Here is your generated image for: <strong>"${escapeHTML(data.originalPrompt || data.prompt)}"</strong></p>
            
            <div class="generated-image-container">
              <img src="${data.image}" class="generated-image" alt="Generated visual">
              <div class="image-overlay-actions">
                <button class="overlay-btn zoom-btn" title="View Fullscreen"><i data-lucide="maximize-2"></i></button>
                <a href="${data.image}" download="${slugify(data.originalPrompt || 'image')}.png" class="overlay-btn" title="Download"><i data-lucide="download"></i></a>
              </div>
            </div>
            
            ${metadataHtml}
          </div>
          <span class="message-time">${timestamp}</span>
        </div>
      </div>
    `;

    messagesContainer.insertAdjacentHTML('beforeend', messageHtml);
    lucide.createIcons();

    // Attach click events to the image and zoom button
    const container = messagesContainer.lastElementChild;
    const img = container.querySelector('.generated-image');
    const zoomBtn = container.querySelector('.zoom-btn');
    
    const triggerModal = () => openModal(data.image, data.refinedPrompt || data.originalPrompt || data.prompt);
    img.addEventListener('click', triggerModal);
    zoomBtn.addEventListener('click', triggerModal);
  }

  function appendErrorMessage(errorMsg) {
    const timestamp = getFormattedTime();
    const messageHtml = `
      <div class="message bot-message slide-in">
        <div class="message-avatar" style="background: rgba(239, 68, 68, 0.1); border-color: rgba(239, 68, 68, 0.2);">
          <i data-lucide="alert-circle" style="color: #ef4444;"></i>
        </div>
        <div class="message-content">
          <div class="message-bubble" style="border-color: rgba(239, 68, 68, 0.2);">
            <p style="color: #fca5a5; font-weight: 500;">Generation Failed</p>
            <p style="font-size: 13px; color: #fecaca;">${escapeHTML(errorMsg)}</p>
          </div>
          <span class="message-time">${timestamp}</span>
        </div>
      </div>
    `;
    messagesContainer.insertAdjacentHTML('beforeend', messageHtml);
    lucide.createIcons();
  }

  // 6. Conversations Storage & Rendering
  function loadConversationsFromStorage() {
    try {
      const stored = localStorage.getItem('aetherimage_conversations');
      if (stored) {
        conversations = JSON.parse(stored);
        renderConversationsSidebar();
      }
    } catch (e) {
      console.error('Failed to load conversations from LocalStorage:', e);
    }
  }

  function saveConversationsToStorage() {
    try {
      localStorage.setItem('aetherimage_conversations', JSON.stringify(conversations));
    } catch (e) {
      console.error('Failed to save conversations to LocalStorage:', e);
    }
  }

  function renderConversationsSidebar() {
    if (conversations.length === 0) {
      historyList.innerHTML = `
        <div class="empty-history">
          <i data-lucide="message-square"></i>
          <p>No chat history yet</p>
        </div>
      `;
      lucide.createIcons();
      return;
    }

    historyList.innerHTML = '';
    conversations.forEach((conv) => {
      const timeStr = formatRelativeTime(conv.timestamp);
      const isActive = conv.id === activeConversationId ? 'active-chat' : '';
      const itemHtml = `
        <div class="history-item ${isActive}" data-id="${conv.id}">
          <i data-lucide="message-square" class="chat-icon"></i>
          <div class="history-item-details">
            <span class="history-item-prompt">${escapeHTML(conv.title)}</span>
            <span class="history-item-time">${timeStr}</span>
          </div>
          <button class="delete-chat-btn" data-id="${conv.id}" title="Delete conversation">
            <i data-lucide="x"></i>
          </button>
        </div>
      `;
      historyList.insertAdjacentHTML('beforeend', itemHtml);
    });

    lucide.createIcons();

    // Attach click events to conversation items
    historyList.querySelectorAll('.history-item').forEach(itemNode => {
      itemNode.addEventListener('click', (e) => {
        // If clicking delete button, don't load the chat
        if (e.target.closest('.delete-chat-btn')) return;
        
        const id = itemNode.getAttribute('data-id');
        loadConversation(id);
      });
    });

    // Attach click events to delete buttons
    historyList.querySelectorAll('.delete-chat-btn').forEach(btn => {
      btn.addEventListener('click', (e) => {
        e.stopPropagation();
        const id = btn.getAttribute('data-id');
        deleteConversation(id);
      });
    });
  }

  function loadConversation(id) {
    const conv = conversations.find(c => c.id === id);
    if (!conv) return;

    activeConversationId = id;
    renderConversationsSidebar(); // Refresh active highlights

    // Revert the model select dropdown to the model used in this conversation
    const lastAssistantMsg = conv.messages.slice().reverse().find(m => m.role === 'assistant');
    if (lastAssistantMsg && lastAssistantMsg.model) {
      modelSelect.value = lastAssistantMsg.model;
    }

    // Update key field visibility based on loaded model
    if (modelSelect.value === 'gemini-3.1-flash-image') {
      geminiKeyCard.style.display = 'block';
    } else {
      geminiKeyCard.style.display = 'none';
    }

    // Clear and rebuild chat
    messagesContainer.innerHTML = '';
    
    // Clear and rebuild chat by rendering user and assistant messages chronologically
    conv.messages.forEach(msg => {
      if (msg.role === 'user') {
        appendUserMessage(msg.content);
      } else if (msg.role === 'assistant') {
        appendBotMessage(msg);
      }
    });

    scrollToBottom();
  }

  function deleteConversation(id) {
    if (confirm('Are you sure you want to delete this conversation?')) {
      conversations = conversations.filter(c => c.id !== id);
      saveConversationsToStorage();
      
      if (activeConversationId === id) {
        startNewChat();
      } else {
        renderConversationsSidebar();
      }
    }
  }

  function clearAllConversations() {
    if (conversations.length === 0) return;
    if (confirm('Are you sure you want to clear all conversation history?')) {
      conversations = [];
      localStorage.removeItem('aetherimage_conversations');
      startNewChat();
      renderConversationsSidebar();
    }
  }

  // 7. Modal Handlers
  function openModal(imageSrc, promptText) {
    modalImg.src = imageSrc;
    modalPrompt.textContent = promptText;
    modalDownload.href = imageSrc;
    modalDownload.download = `${slugify(promptText)}.png`;
    imageModal.classList.add('active');
  }

  function closeModal() {
    imageModal.classList.remove('active');
  }

  // 8. Utility Functions
  function getFormattedTime() {
    const now = new Date();
    return now.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
  }

  function formatRelativeTime(timestamp) {
    const diffMs = Date.now() - timestamp;
    const diffSec = Math.floor(diffMs / 1000);
    const diffMin = Math.floor(diffSec / 60);
    const diffHr = Math.floor(diffMin / 60);

    if (diffSec < 60) return 'just now';
    if (diffMin < 60) return `${diffMin}m ago`;
    if (diffHr < 24) return `${diffHr}h ago`;
    return new Date(timestamp).toLocaleDateString();
  }

  // Simple HTML escaping helper
  function escapeHTML(str) {
    return str
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;')
      .replace(/'/g, '&#039;');
  }

  function slugify(text) {
    return text
      .toLowerCase()
      .replace(/[^a-z0-9]+/g, '-')
      .replace(/(^-|-$)+/g, '')
      .slice(0, 30);
  }

  function scrollToBottom() {
    messagesContainer.scrollTo({
      top: messagesContainer.scrollHeight,
      behavior: 'smooth'
    });
  }
});
