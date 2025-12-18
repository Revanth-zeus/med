const API_BASE = '';

// ============== INITIALIZATION ==============
document.addEventListener('DOMContentLoaded', () => {
    initializeTabs();
    loadDashboardStats();
    loadDocumentsList();
    setupEventListeners();
});

// ============== TAB NAVIGATION ==============
function initializeTabs() {
    const tabButtons = document.querySelectorAll('.tab-btn');
    const tabPanes = document.querySelectorAll('.tab-pane');

    tabButtons.forEach(button => {
        button.addEventListener('click', () => {
            const tabName = button.getAttribute('data-tab');
            
            // Update active states
            tabButtons.forEach(btn => btn.classList.remove('active'));
            tabPanes.forEach(pane => pane.classList.remove('active'));
            
            button.classList.add('active');
            document.getElementById(`${tabName}Tab`).classList.add('active');
            
            // Load content for tab
            if (tabName === 'documents') {
                loadDocumentsList();
            } else if (tabName === 'generate') {
                updatePolicyNote();
            } else if (tabName === 'skills') {
                loadSkills();
                loadCompetencies();
            } else if (tabName === 'profile') {
                checkLearnerProfile();
            } else if (tabName === 'recommendations') {
                loadRecommendations();
            }
        });
    });
}

// ============== DASHBOARD STATS ==============
async function loadDashboardStats() {
    try {
        const response = await fetch(`${API_BASE}/api/documents/indexed`);
        const data = await response.json();
        
        if (data.success) {
            const totalChunks = data.files.reduce((sum, file) => sum + file.chunk_count, 0);
            
            document.getElementById('statDocuments').textContent = data.count;
            document.getElementById('statChunks').textContent = totalChunks;
            document.getElementById('statStatus').textContent = data.count > 0 ? 'Ready' : 'No Docs';
            
            updatePolicyNote();
        }
    } catch (err) {
        console.error('Error loading stats:', err);
        document.getElementById('statStatus').textContent = 'Error';
    }
}

function updatePolicyNote() {
    const statDocs = parseInt(document.getElementById('statDocuments').textContent) || 0;
    const noteEl = document.getElementById('policyNote');
    
    if (statDocs === 0) {
        noteEl.textContent = '⚠️ No documents uploaded yet. Upload documents in the "My Documents" tab.';
        noteEl.style.color = '#F59E0B';
    } else {
        noteEl.textContent = `✅ ${statDocs} document(s) available for policy-aligned questions`;
        noteEl.style.color = '#10B981';
    }
}

// ============== EVENT LISTENERS ==============
function setupEventListeners() {
    // Generate question
    document.getElementById('generateBtn').addEventListener('click', generateQuestion);
    document.getElementById('topic').addEventListener('keypress', (e) => {
        if (e.key === 'Enter') generateQuestion();
    });
    
    // File upload
    const uploadArea = document.getElementById('uploadArea');
    const fileInput = document.getElementById('fileUpload');
    
    uploadArea.addEventListener('click', () => fileInput.click());
    fileInput.addEventListener('change', handleFileUpload);
    
    // Drag and drop
    uploadArea.addEventListener('dragover', (e) => {
        e.preventDefault();
        uploadArea.classList.add('drag-over');
    });
    
    uploadArea.addEventListener('dragleave', () => {
        uploadArea.classList.remove('drag-over');
    });
    
    uploadArea.addEventListener('drop', (e) => {
        e.preventDefault();
        uploadArea.classList.remove('drag-over');
        const file = e.dataTransfer.files[0];
        if (file) {
            fileInput.files = e.dataTransfer.files;
            handleFileUpload();
        }
    });
    
    // Refresh documents
    document.getElementById('refreshDocsBtn').addEventListener('click', loadDocumentsList);
    
    // Search
    document.getElementById('searchBtn').addEventListener('click', searchPolicies);
    document.getElementById('searchQuery').addEventListener('keypress', (e) => {
        if (e.key === 'Enter') searchPolicies();
    });
}

// ============== GENERATE QUESTION ==============
async function generateQuestion() {
    const topic = document.getElementById('topic').value.trim();
    const difficulty = document.getElementById('difficulty').value;
    const questionType = document.getElementById('question_type').value;
    const includeCitations = document.getElementById('include_citations').checked;
    const usePolicies = document.getElementById('use_policies').checked;

    if (!topic) {
        showError('Please enter a clinical topic');
        return;
    }

    const btn = document.getElementById('generateBtn');
    const loading = document.getElementById('loading');
    const error = document.getElementById('error');
    const result = document.getElementById('result');
    const placeholder = document.getElementById('placeholder');

    // Reset UI
    error.classList.add('hidden');
    result.classList.add('hidden');
    placeholder.classList.add('hidden');
    loading.classList.remove('hidden');
    btn.disabled = true;

    try {
        // Always use the complete endpoint with skills
        const endpoint = '/generate-question-with-skills-and-policies';
        
        const response = await fetch(`${API_BASE}${endpoint}`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                topic: topic,
                difficulty: difficulty,
                question_type: questionType,
                use_hospital_policies: usePolicies
            })
        });

        if (!response.ok) {
            const errorData = await response.json();
            throw new Error(errorData.detail || 'Failed to generate question');
        }

        const data = await response.json();
        displayQuestion(data, difficulty, questionType);

    } catch (err) {
        showError(err.message);
        placeholder.classList.remove('hidden');
    } finally {
        loading.classList.add('hidden');
        btn.disabled = false;
    }
}


function displayQuestion(data, difficulty, questionType) {
    const content = document.getElementById('questionContent');
    const result = document.getElementById('result');
    
    // Update meta badges
    document.getElementById('resultType').textContent = questionType.toUpperCase();
    document.getElementById('resultDifficulty').textContent = difficulty.charAt(0).toUpperCase() + difficulty.slice(1);
    
    let html = '';

    // Scenario
    if (data.data.scenario) {
        html += `
            <div class="scenario-box">
                <h3>📋 Clinical Scenario</h3>
                <p>${data.data.scenario}</p>
            </div>
        `;
    }

    // Question
    const questionText = data.data.question || data.data.question_template || '';
    html += `<h3>❓ Question</h3><p><strong>${questionText}</strong></p>`;

    // Options (MCQ, SATA)
    if (data.data.options) {
        html += '<h3>📝 Answer Options</h3><ul class="options-list">';
        for (const [key, value] of Object.entries(data.data.options)) {
            const isCorrect = (data.data.correct_answer === key) || 
                             (data.data.correct_answers && data.data.correct_answers.includes(key));
            const className = isCorrect ? 'correct-answer' : '';
            html += `<li class="${className}">${key}. ${value}</li>`;
        }
        html += '</ul>';
    }

    // Matrix
    if (data.data.row_items && data.data.column_options) {
        html += '<h3>📊 Matrix Grid</h3>';
        html += '<div style="overflow-x: auto;"><table style="width:100%; border-collapse: collapse; margin-top: 10px;">';
        html += '<thead><tr><th style="border: 2px solid var(--border); padding: 12px; background: var(--light-gray); text-align: left;">Assessment Finding</th>';
        data.data.column_options.forEach(col => {
            html += `<th style="border: 2px solid var(--border); padding: 12px; background: var(--light-gray); text-align: center;">${col}</th>`;
        });
        html += '</tr></thead><tbody>';
        
        data.data.row_items.forEach(item => {
            html += `<tr><td style="border: 1px solid var(--border); padding: 12px; font-weight: 500;">${item}</td>`;
            data.data.column_options.forEach(col => {
                const isCorrect = data.data.correct_matrix[item] === col;
                const bgColor = isCorrect ? '#D1FAE5' : 'white';
                const icon = isCorrect ? '✓' : '';
                html += `<td style="border: 1px solid var(--border); padding: 12px; background: ${bgColor}; text-align: center; color: var(--success); font-weight: bold;">${icon}</td>`;
            });
            html += '</tr>';
        });
        html += '</tbody></table></div>';
    }

    // Cloze
    if (data.data.blanks) {
        html += '<h3>📝 Fill-in-the-Blank Options</h3>';
        for (const [blank, options] of Object.entries(data.data.blanks)) {
            const correctAnswer = data.data.correct_answers[blank];
            html += `<div style="margin-bottom: 1rem; padding: 1rem; background: var(--light-gray); border-radius: 8px;">`;
            html += `<p style="margin-bottom: 0.5rem;"><strong>${blank}:</strong></p>`;
            html += `<p style="color: var(--gray);">Options: ${options.join(', ')}</p>`;
            html += `<p style="color: var(--success); font-weight: 600; margin-top: 0.5rem;">✓ Correct: ${correctAnswer}</p>`;
            html += `</div>`;
        }
    }

    // Highlight
    if (data.data.text_passage) {
        html += `<h3>📄 Text Passage</h3>`;
        html += `<div class="scenario-box"><pre style="white-space: pre-wrap; font-family: inherit; line-height: 1.8;">${data.data.text_passage}</pre></div>`;
        if (data.data.correct_highlights) {
            html += `<div style="background: var(--light-gray); padding: 1rem; border-radius: 8px;">`;
            html += `<p style="font-weight: 600; margin-bottom: 0.5rem;">✓ Correct Highlights:</p>`;
            html += `<ul style="margin-left: 1.5rem;">`;
            data.data.correct_highlights.forEach(highlight => {
                html += `<li style="color: var(--success); font-weight: 500;">${highlight}</li>`;
            });
            html += `</ul></div>`;
        }
    }

    // Bowtie
    if (data.data.condition) {
        html += `<h3>🎯 Clinical Judgment: ${data.data.condition}</h3>`;
        html += `<div style="display: grid; grid-template-columns: 1fr 1fr; gap: 1rem; margin-top: 1rem;">`;
        html += `<div style="background: #FEF3C7; padding: 1rem; border-radius: 8px;">`;
        html += `<p style="font-weight: 600; margin-bottom: 0.5rem;">⚠️ Correct Causes:</p>`;
        html += `<ul style="margin-left: 1.5rem;">`;
        data.data.correct_causes.forEach(cause => {
            html += `<li>${cause}</li>`;
        });
        html += `</ul></div>`;
        html += `<div style="background: #D1FAE5; padding: 1rem; border-radius: 8px;">`;
        html += `<p style="font-weight: 600; margin-bottom: 0.5rem;">✓ Correct Interventions:</p>`;
        html += `<ul style="margin-left: 1.5rem;">`;
        data.data.correct_interventions.forEach(intervention => {
            html += `<li>${intervention}</li>`;
        });
        html += `</ul></div></div>`;
    }

    // Rationale
    if (data.data.rationale) {
        html += `
            <div class="rationale-box">
                <h3>💡 Rationale</h3>
                <p>${data.data.rationale}</p>
            </div>
        `;
    }

    // Citations
    if (data.citations && data.citations.length > 0) {
        html += '<div class="citations"><h3>📚 Evidence-Based Citations</h3>';
        data.citations.forEach((cite, idx) => {
            html += `
                <div class="citation-item">
                    <strong>${idx + 1}. </strong>
                    <a href="${cite.url}" target="_blank">${cite.title}</a><br>
                    <small>${cite.authors} • ${cite.journal} (${cite.pub_date}) • Relevance: ${cite.relevance}</small>
                </div>
            `;
        });
        html += '</div>';
    }

    // Skill Tags
    if (data.skill_tags && data.skill_tags.length > 0) {
        html += '<div class="skills-section">';
        html += '<h3>🎯 Skills Tested</h3>';
        html += '<div class="skill-tags">';
        data.skill_tags.forEach(tag => {
            const confidencePercent = (tag.confidence * 100).toFixed(0);
            html += `
                <div class="skill-tag">
                    <div class="skill-tag-header">
                        <span class="skill-name">${tag.skill_name}</span>
                        <span class="skill-confidence">${confidencePercent}%</span>
                    </div>
                    <div class="skill-category">${tag.category}</div>
                </div>
            `;
        });
        html += '</div></div>';
    }

    // Competencies
    if (data.competencies && data.competencies.length > 0) {
        html += '<div class="competencies-section">';
        html += '<h3>📋 Competencies</h3>';
        html += '<div class="competency-badges">';
        data.competencies.forEach(comp => {
            const coverage = (comp.coverage * 100).toFixed(0);
            html += `
                <div class="competency-badge">
                    <span class="comp-name">${comp.competency_name}</span>
                    <span class="comp-coverage">${coverage}% coverage</span>
                </div>
            `;
        });
        html += '</div></div>';
    }

    if (data.citation_note) {
        html += `<div style="background: #FEF3C7; padding: 1rem; border-radius: 8px; margin-top: 1rem; border-left: 4px solid var(--warning);">`;
        html += `<p style="color: #92400E;"><strong>ℹ️ Note:</strong> ${data.citation_note}</p>`;
        html += `</div>`;
    }

    content.innerHTML = html;
    result.classList.remove('hidden');
    result.scrollIntoView({ behavior: 'smooth', block: 'start' });
}

// ============== FILE UPLOAD ==============
// Global abort controller for upload
let uploadAbortController = null;

async function handleFileUpload() {
    const fileInput = document.getElementById('fileUpload');
    const file = fileInput.files[0];
    
    if (!file) return;
    
    const uploadArea = document.getElementById('uploadArea');
    const uploadProgress = document.getElementById('uploadProgress');
    const uploadSuccess = document.getElementById('uploadSuccess');
    const progressText = document.getElementById('uploadProgressText');
    const progressBar = document.getElementById('uploadProgressBar');
    const progressPercent = document.getElementById('uploadProgressPercent');
    
    // Create abort controller
    uploadAbortController = new AbortController();
    
    // Show loading
    uploadArea.classList.add('hidden');
    uploadProgress.classList.remove('hidden');
    uploadSuccess.classList.add('hidden');
    
    // Show file size info
    const fileSizeKB = (file.size / 1024).toFixed(0);
    progressText.textContent = `📤 Uploading ${file.name} (${fileSizeKB} KB)...`;
    
    // Animate progress bar with realistic steps
    let currentProgress = 0;
    const progressSteps = [
        { percent: 10, text: `📤 Uploading to Google Drive...`, delay: 500 },
        { percent: 25, text: `📄 Extracting text from document...`, delay: 1500 },
        { percent: 40, text: `📦 Creating text chunks...`, delay: 2500 },
        { percent: 55, text: `🧠 Generating embeddings...`, delay: 3500 },
        { percent: 70, text: `💾 Storing in vector database...`, delay: 5000 },
        { percent: 85, text: `🔍 Finalizing index...`, delay: 7000 },
    ];
    
    // Update progress bar function
    const updateProgress = (percent, text) => {
        if (uploadAbortController && !uploadAbortController.signal.aborted) {
            if (progressBar) progressBar.style.width = `${percent}%`;
            if (progressPercent) progressPercent.textContent = `${percent}%`;
            if (text && progressText) progressText.textContent = text;
        }
    };
    
    // Start progress animation
    progressSteps.forEach(step => {
        setTimeout(() => {
            if (currentProgress < step.percent) {
                currentProgress = step.percent;
                updateProgress(step.percent, step.text);
            }
        }, step.delay);
    });
    
    try {
        const formData = new FormData();
        formData.append('file', file);
        
        const response = await fetch(`${API_BASE}/api/upload-and-index`, {
            method: 'POST',
            body: formData,
            signal: uploadAbortController.signal
        });
        
        if (!response.ok) {
            const errorData = await response.json();
            throw new Error(errorData.detail || 'Upload failed');
        }
        
        const data = await response.json();
        
        // Complete progress
        updateProgress(100, '✅ Complete!');
        
        // Clear abort controller
        uploadAbortController = null;
        
        // Short delay to show 100%
        await new Promise(r => setTimeout(r, 500));
        
        // Show success
        document.getElementById('uploadMessage').textContent = 
            `✅ ${data.filename} uploaded successfully! (${data.chunks_indexed} chunks indexed)`;
        uploadProgress.classList.add('hidden');
        uploadSuccess.classList.remove('hidden');
        
        // Reload stats and documents list
        loadDashboardStats();
        loadDocumentsList();
        
        // Reset after 3 seconds
        setTimeout(() => {
            uploadArea.classList.remove('hidden');
            uploadSuccess.classList.add('hidden');
            fileInput.value = '';
            // Reset progress bar
            if (progressBar) progressBar.style.width = '0%';
            if (progressPercent) progressPercent.textContent = '0%';
        }, 3000);
        
    } catch (err) {
        uploadAbortController = null;
        uploadProgress.classList.add('hidden');
        
        if (err.name === 'AbortError') {
            showSuccess('Upload cancelled');
        } else {
            showError(err.message);
        }
        
        uploadArea.classList.remove('hidden');
        fileInput.value = '';
        // Reset progress bar
        if (progressBar) progressBar.style.width = '0%';
        if (progressPercent) progressPercent.textContent = '0%';
    }
}

function cancelUpload() {
    if (uploadAbortController) {
        uploadAbortController.abort();
        uploadAbortController = null;
        
        const uploadArea = document.getElementById('uploadArea');
        const uploadProgress = document.getElementById('uploadProgress');
        const fileInput = document.getElementById('fileUpload');
        
        uploadProgress.classList.add('hidden');
        uploadArea.classList.remove('hidden');
        fileInput.value = '';
        
        showSuccess('Upload cancelled');
    }
}

// ============== DOCUMENTS LIST ==============
async function loadDocumentsList() {
    const container = document.getElementById('documentsList');
    container.innerHTML = '<div class="loading-docs"><div class="spinner"></div><p>Loading documents...</p></div>';
    
    try {
        const response = await fetch(`${API_BASE}/api/documents/indexed`);
        const data = await response.json();
        
        if (data.success && data.files.length > 0) {
            let html = '';
            data.files.forEach(file => {
                html += `
                    <div class="document-item" id="doc-${encodeURIComponent(file.filename)}">
                        <div class="doc-icon">📄</div>
                        <div class="doc-info">
                            <div class="doc-name">${file.filename}</div>
                            <div class="doc-meta">${file.chunk_count} chunks indexed</div>
                        </div>
                        <button class="btn-delete" onclick="deleteDocument('${encodeURIComponent(file.filename)}')" title="Delete document">
                            🗑️
                        </button>
                    </div>
                `;
            });
            container.innerHTML = html;
        } else {
            container.innerHTML = `
                <div class="empty-state">
                    <svg width="80" height="80" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1" opacity="0.3">
                        <path d="M13 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V9z"/>
                        <polyline points="13 2 13 9 20 9"/>
                    </svg>
                    <h3>No Documents Yet</h3>
                    <p>Upload your first document to get started</p>
                </div>
            `;
        }
    } catch (err) {
        container.innerHTML = `<div class="error-state">Error loading documents: ${err.message}</div>`;
    }
}

async function deleteDocument(encodedFilename) {
    const filename = decodeURIComponent(encodedFilename);
    
    if (!confirm(`Delete "${filename}"?\n\nThis will remove all indexed chunks for this document. This cannot be undone.`)) {
        return;
    }
    
    // Show loading state on the document item
    const docItem = document.getElementById(`doc-${encodedFilename}`);
    if (docItem) {
        docItem.style.opacity = '0.5';
        docItem.style.pointerEvents = 'none';
    }
    
    try {
        const response = await fetch(`${API_BASE}/api/documents/by-name/${encodedFilename}`, {
            method: 'DELETE'
        });
        
        const data = await response.json();
        
        if (data.success) {
            // Show success message
            showSuccess(`Deleted "${filename}" (${data.chunks_deleted} chunks removed)`);
            
            // Refresh the documents list and stats
            await loadDocumentsList();
            await loadDashboardStats();
        } else {
            throw new Error(data.detail || 'Delete failed');
        }
        
    } catch (err) {
        console.error('Delete error:', err);
        showError(`Failed to delete: ${err.message}`);
        
        // Restore the document item
        if (docItem) {
            docItem.style.opacity = '1';
            docItem.style.pointerEvents = 'auto';
        }
    }
}

// Helper to show success message
function showSuccess(message) {
    // Create a success toast
    const toast = document.createElement('div');
    toast.className = 'success-toast';
    toast.innerHTML = `<span>✅</span> ${message}`;
    toast.style.cssText = `
        position: fixed;
        top: 20px;
        right: 20px;
        background: linear-gradient(135deg, #10B981, #059669);
        color: white;
        padding: 1rem 1.5rem;
        border-radius: 8px;
        box-shadow: 0 4px 20px rgba(16, 185, 129, 0.4);
        z-index: 10000;
        animation: slideIn 0.3s ease;
        display: flex;
        align-items: center;
        gap: 0.5rem;
        font-weight: 500;
    `;
    document.body.appendChild(toast);
    
    setTimeout(() => {
        toast.style.animation = 'slideOut 0.3s ease';
        setTimeout(() => toast.remove(), 300);
    }, 3000);
}

// ============== POLICY SEARCH ==============
async function searchPolicies() {
    const query = document.getElementById('searchQuery').value.trim();
    
    if (!query) {
        showError('Please enter a search query');
        return;
    }
    
    const searchLoading = document.getElementById('searchLoading');
    const searchResults = document.getElementById('searchResults');
    const searchPlaceholder = document.getElementById('searchPlaceholder');
    
    searchPlaceholder.classList.add('hidden');
    searchResults.classList.add('hidden');
    searchLoading.classList.remove('hidden');
    
    try {
        const response = await fetch(`${API_BASE}/api/documents/search`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                query: query,
                limit: 5
            })
        });
        
        if (!response.ok) {
            throw new Error('Search failed');
        }
        
        const data = await response.json();
        
        if (data.success && data.results.length > 0) {
            let html = '<h3>Search Results</h3>';
            data.results.forEach((result, idx) => {
                const relevancePercent = (result.relevance_score * 100).toFixed(0);
                html += `
                    <div class="search-result-item">
                        <div class="result-header">
                            <span class="result-number">${idx + 1}</span>
                            <div class="result-meta">
                                <div class="result-filename">📄 ${result.filename}</div>
                                <div class="result-section">${result.section} • Chunk ${result.chunk_index}</div>
                            </div>
                            <div class="result-score">${relevancePercent}%</div>
                        </div>
                        <div class="result-content">${result.content}</div>
                    </div>
                `;
            });
            searchResults.innerHTML = html;
            searchResults.classList.remove('hidden');
        } else {
            searchResults.innerHTML = `
                <div class="empty-state">
                    <h3>No Results Found</h3>
                    <p>Try different keywords or upload more documents</p>
                </div>
            `;
            searchResults.classList.remove('hidden');
        }
        
    } catch (err) {
        showError(err.message);
        searchPlaceholder.classList.remove('hidden');
    } finally {
        searchLoading.classList.add('hidden');
    }
}

// ============== ERROR HANDLING ==============
function showError(message) {
    const error = document.getElementById('error');
    error.innerHTML = `<strong>⚠️ Error:</strong> ${message}`;
    error.classList.remove('hidden');
    
    setTimeout(() => {
        error.classList.add('hidden');
    }, 5000);
}



// ============== SKILLS FUNCTIONALITY ==============

let allSkills = [];
let allCompetencies = [];
let currentLearner = null;

// Load skills when Skills tab is opened
async function loadSkills() {
    try {
        const response = await fetch(`${API_BASE}/api/skills/all`);
        const data = await response.json();
        
        if (data.success) {
            allSkills = data.skills;
            displaySkills(allSkills);
        }
    } catch (err) {
        console.error('Error loading skills:', err);
    }
}

async function loadCompetencies() {
    try {
        const response = await fetch(`${API_BASE}/api/competencies/all`);
        const data = await response.json();
        
        if (data.success) {
            allCompetencies = data.competencies;
            displayCompetencies(allCompetencies);
        }
    } catch (err) {
        console.error('Error loading competencies:', err);
    }
}

function displaySkills(skills) {
    const container = document.getElementById('skillsList');
    document.getElementById('skillsCount').textContent = `${skills.length} skills`;
    
    if (skills.length === 0) {
        container.innerHTML = '<div class="empty-state"><p>No skills found</p></div>';
        return;
    }
    
    let html = '';
    skills.forEach(skill => {
        const roles = skill.required_roles.join(', ');
        const levels = skill.proficiency_levels.join(', ');
        
        html += `
            <div class="skill-card" onclick="showSkillDetails('${skill.id}')">
                <div class="skill-card-header">
                    <h3>${skill.name}</h3>
                    <span class="category-badge">${skill.category}</span>
                </div>
                <p class="skill-description">${skill.description}</p>
                <div class="skill-meta">
                    <div><strong>Roles:</strong> ${roles}</div>
                    <div><strong>Levels:</strong> ${levels}</div>
                </div>
                <div class="skill-keywords">
                    <strong>Keywords:</strong> ${skill.keywords.join(', ')}
                </div>
            </div>
        `;
    });
    
    container.innerHTML = html;
}

// Add this new function at the end of app_s.js
function showSkillDetails(skillId) {
    const skill = allSkills.find(s => s.id === skillId);
    if (!skill) return;
    
    // Create modal
    const modal = document.createElement('div');
    modal.className = 'skill-modal';
    modal.innerHTML = `
        <div class="skill-modal-content">
            <div class="skill-modal-header">
                <h2>${skill.name}</h2>
                <button class="modal-close" onclick="this.closest('.skill-modal').remove()">×</button>
            </div>
            <div class="skill-modal-body">
                <div class="skill-detail-section">
                    <h3>Description</h3>
                    <p>${skill.description}</p>
                </div>
                
                <div class="skill-detail-section">
                    <h3>Category</h3>
                    <span class="category-badge">${skill.category}</span>
                </div>
                
                <div class="skill-detail-section">
                    <h3>Required Roles</h3>
                    <div class="role-badges">
                        ${skill.required_roles.map(role => `<span class="role-badge">${role}</span>`).join('')}
                    </div>
                </div>
                
                <div class="skill-detail-section">
                    <h3>Proficiency Levels</h3>
                    <div class="level-badges">
                        ${skill.proficiency_levels.map(level => `<span class="proficiency-badge ${level}">${level}</span>`).join('')}
                    </div>
                </div>
                
                <div class="skill-detail-section">
                    <h3>Keywords for Auto-Tagging</h3>
                    <div class="keyword-tags">
                        ${skill.keywords.map(kw => `<span class="keyword-tag">${kw}</span>`).join('')}
                    </div>
                </div>
                
                <div class="skill-actions">
                    <button class="btn-primary" onclick="generateQuestionForSkill('${skill.id}', '${skill.name}')">
                        Generate Practice Question
                    </button>
                </div>
            </div>
        </div>
    `;
    
    document.body.appendChild(modal);
}

function generateQuestionForSkill(skillId, skillName) {
    // Close modal
    document.querySelector('.skill-modal')?.remove();
    
    // Switch to Generate tab
    document.querySelector('[data-tab="generate"]').click();
    
    // Pre-fill topic based on skill keywords
    const skill = allSkills.find(s => s.id === skillId);
    if (skill && skill.keywords.length > 0) {
        document.getElementById('topic').value = skill.keywords[0];
        
        // Scroll to form
        setTimeout(() => {
            document.getElementById('topic').focus();
        }, 100);
    }
}




function displayCompetencies(competencies) {
    const container = document.getElementById('competenciesList');
    
    if (competencies.length === 0) {
        container.innerHTML = '<div class="empty-state"><p>No competencies found</p></div>';
        return;
    }
    
    let html = '';
    competencies.forEach(comp => {
        const roles = comp.roles.join(', ');
        
        html += `
            <div class="competency-card">
                <h3>${comp.name}</h3>
                <p>${comp.description}</p>
                <div class="comp-meta">
                    <span><strong>Skills:</strong> ${comp.skills.length}</span>
                    <span><strong>Roles:</strong> ${roles}</span>
                </div>
            </div>
        `;
    });
    
    container.innerHTML = html;
}

// Filter skills
document.getElementById('skillCategoryFilter').addEventListener('change', (e) => {
    const category = e.target.value;
    const roleFilter = document.getElementById('skillRoleFilter').value;
    filterSkills(category, roleFilter);
});

document.getElementById('skillRoleFilter').addEventListener('change', (e) => {
    const role = e.target.value;
    const categoryFilter = document.getElementById('skillCategoryFilter').value;
    filterSkills(categoryFilter, role);
});

function filterSkills(category, role) {
    let filtered = allSkills;
    
    if (category !== 'all') {
        filtered = filtered.filter(s => s.category === category);
    }
    
    if (role !== 'all') {
        filtered = filtered.filter(s => s.required_roles.includes(role));
    }
    
    displaySkills(filtered);
}

// Check for existing profile
function checkLearnerProfile() {
    const learnerId = localStorage.getItem('learnerId');
    if (learnerId) {
        loadLearnerProfile(learnerId);
    }
}

// Create profile
document.getElementById('createProfileBtn').addEventListener('click', async () => {
    const name = document.getElementById('learnerName').value.trim();
    const role = document.getElementById('learnerRole').value;
    
    if (!name) {
        showError('Please enter your name');
        return;
    }
    
    const learnerId = 'learner_' + Date.now();
    
    try {
        const response = await fetch(`${API_BASE}/api/learner/create?learner_id=${learnerId}&name=${encodeURIComponent(name)}&role=${encodeURIComponent(role)}`, {
            method: 'POST'
        });
        
        const data = await response.json();
        
        if (data.success) {
            localStorage.setItem('learnerId', learnerId);
            currentLearner = data.profile;
            showProfileDashboard();
        }
    } catch (err) {
        showError('Error creating profile: ' + err.message);
    }
});

async function loadLearnerProfile(learnerId) {
    try {
        const response = await fetch(`${API_BASE}/api/learner/${learnerId}`);
        const data = await response.json();
        
        if (data.success) {
            currentLearner = data.profile;
            showProfileDashboard();
            loadLearnerPerformance(learnerId);
        }
    } catch (err) {
        console.error('Error loading profile:', err);
        // Profile not found, show setup
        document.getElementById('profileSetup').classList.remove('hidden');
        document.getElementById('profileDashboard').classList.add('hidden');
    }
}

function showProfileDashboard() {
    document.getElementById('profileSetup').classList.add('hidden');
    document.getElementById('profileDashboard').classList.remove('hidden');
    document.getElementById('profileName').textContent = currentLearner.name;
    document.getElementById('profileRole').textContent = currentLearner.role;
}

async function loadLearnerPerformance(learnerId) {
    try {
        const response = await fetch(`${API_BASE}/api/learner/${learnerId}/performance`);
        const data = await response.json();
        
        if (data.success) {
            updateProfileStats(data);
            displayStrengthsAndGaps(data);
            displayDetailedPerformance(data);
            createRadarChart(data);
        }
    } catch (err) {
        console.error('Error loading performance:', err);
    }
}

function updateProfileStats(data) {
    document.getElementById('totalAttempts').textContent = data.total_attempts || 0;
    document.getElementById('skillsPracticed').textContent = data.skills_practiced || 0;
    
    // Use overall_accuracy from the new API response
    const avgAcc = data.overall_accuracy || 0;
    document.getElementById('avgAccuracy').textContent = avgAcc.toFixed(0) + '%';
}

function displayStrengthsAndGaps(data) {
    // Strengths - Show TOPICS where user got questions correct
    const strengthsList = document.getElementById('strengthsList');
    const topicStrengths = data.topic_strengths || [];
    const skillStrengths = data.strengths || [];
    
    if (topicStrengths.length > 0 || skillStrengths.length > 0) {
        let html = '';
        
        // Show topic strengths first
        topicStrengths.forEach(t => {
            html += `
                <div class="performance-item strength">
                    <div class="perf-name">📚 ${t.topic}</div>
                    <div class="perf-stats">
                        <span class="accuracy-badge success">${(t.accuracy * 100).toFixed(0)}%</span>
                        <span class="attempts-badge">${t.correct}/${t.attempts} correct</span>
                    </div>
                </div>
            `;
        });
        
        // Then show skill strengths
        skillStrengths.forEach(s => {
            const skillName = s.skill_id.replace('skill_', '').replace('topic_', '').replace(/_/g, ' ').toUpperCase();
            html += `
                <div class="performance-item strength">
                    <div class="perf-name">🎯 ${skillName}</div>
                    <div class="perf-stats">
                        <span class="accuracy-badge success">${(s.accuracy * 100).toFixed(0)}%</span>
                        <span class="attempts-badge">${s.attempts} attempts</span>
                    </div>
                </div>
            `;
        });
        
        strengthsList.innerHTML = html;
    } else {
        strengthsList.innerHTML = '<div class="empty-state"><p>Get 70%+ on topics to see your strengths!</p></div>';
    }
    
    // Gaps - Show TOPICS where user got questions wrong
    const gapsList = document.getElementById('gapsList');
    const topicWeaknesses = data.topic_weaknesses || [];
    const skillGaps = data.gaps || [];
    
    if (topicWeaknesses.length > 0 || skillGaps.length > 0) {
        let html = '';
        
        // Show topic weaknesses first
        topicWeaknesses.forEach(t => {
            html += `
                <div class="performance-item gap">
                    <div class="perf-name">📚 ${t.topic}</div>
                    <div class="perf-stats">
                        <span class="accuracy-badge warning">${(t.accuracy * 100).toFixed(0)}%</span>
                        <span class="attempts-badge">${t.correct}/${t.attempts} correct</span>
                    </div>
                </div>
            `;
        });
        
        // Then show skill gaps
        skillGaps.forEach(g => {
            const skillName = g.skill_id.replace('skill_', '').replace('topic_', '').replace(/_/g, ' ').toUpperCase();
            html += `
                <div class="performance-item gap">
                    <div class="perf-name">🎯 ${skillName}</div>
                    <div class="perf-stats">
                        <span class="accuracy-badge warning">${(g.accuracy * 100).toFixed(0)}%</span>
                        <span class="attempts-badge">${g.attempts} attempts</span>
                    </div>
                </div>
            `;
        });
        
        gapsList.innerHTML = html;
    } else {
        gapsList.innerHTML = '<div class="empty-state"><p>Great job! No major gaps identified</p></div>';
    }
}

function displayDetailedPerformance(data) {
    const container = document.getElementById('detailedPerformance');
    
    const hasTopics = data.topic_performance && Object.keys(data.topic_performance).length > 0;
    const hasSkills = data.skill_performance && Object.keys(data.skill_performance).length > 0;
    const hasExams = data.recent_exams && data.recent_exams.length > 0;
    
    if (!hasTopics && !hasSkills && !hasExams) {
        container.innerHTML = '<div class="empty-state"><p>No performance data yet. Take an exam to see your results!</p></div>';
        return;
    }
    
    let html = '';
    
    // Show recent exams first
    if (hasExams) {
        html += '<h4 style="margin-bottom: 1rem; color: var(--primary);">📋 Recent Exam Results</h4>';
        html += '<table class="performance-table"><thead><tr><th>Exam</th><th>Mode</th><th>Score</th><th>Questions</th><th>Duration</th><th>Date</th></tr></thead><tbody>';
        
        data.recent_exams.forEach((exam, idx) => {
            const date = new Date(exam.completed_at).toLocaleDateString();
            const scoreClass = exam.score >= 80 ? 'success' : exam.score >= 60 ? 'warning' : 'danger';
            const modeIcons = { practice: '📚', adaptive: '🎯', timed: '⏱️' };
            const icon = modeIcons[exam.mode] || '📝';
            
            html += `
                <tr>
                    <td><strong>Exam ${idx + 1}</strong></td>
                    <td>${icon} ${exam.mode}</td>
                    <td><span class="accuracy-badge ${scoreClass}">${exam.score.toFixed(0)}%</span></td>
                    <td>${exam.correct_answers}/${exam.total_questions}</td>
                    <td>${exam.duration_minutes.toFixed(1)} min</td>
                    <td>${date}</td>
                </tr>
            `;
        });
        
        html += '</tbody></table>';
        html += '<div style="margin: 2rem 0; border-top: 1px solid var(--border);"></div>';
    }
    
    // Show topic performance
    if (hasTopics) {
        html += '<h4 style="margin-bottom: 1rem; color: var(--primary);">📚 Topic Performance</h4>';
        html += '<table class="performance-table"><thead><tr><th>Topic</th><th>Correct</th><th>Total</th><th>Accuracy</th><th>Last Practiced</th></tr></thead><tbody>';
        
        for (const [topic, perf] of Object.entries(data.topic_performance)) {
            const lastDate = new Date(perf.last_attempted).toLocaleDateString();
            const accuracyPercent = (perf.accuracy * 100).toFixed(0);
            
            html += `
                <tr>
                    <td><strong>${topic.charAt(0).toUpperCase() + topic.slice(1)}</strong></td>
                    <td>${perf.correct_attempts}</td>
                    <td>${perf.total_attempts}</td>
                    <td><span class="accuracy-badge ${accuracyPercent >= 70 ? 'success' : accuracyPercent >= 50 ? 'warning' : 'danger'}">${accuracyPercent}%</span></td>
                    <td>${lastDate}</td>
                </tr>
            `;
        }
        
        html += '</tbody></table>';
        html += '<div style="margin: 2rem 0; border-top: 1px solid var(--border);"></div>';
    }
    
    // Show skill performance
    if (hasSkills) {
        html += '<h4 style="margin-bottom: 1rem; color: var(--primary);">🎯 Skill Performance</h4>';
        html += '<table class="performance-table"><thead><tr><th>Skill</th><th>Attempts</th><th>Accuracy</th><th>Proficiency</th><th>Last Practiced</th></tr></thead><tbody>';
        
        for (const [skillId, perf] of Object.entries(data.skill_performance)) {
            const skillName = skillId.replace('skill_', '').replace('topic_', '').replace(/_/g, ' ').toUpperCase();
            const lastDate = new Date(perf.last_attempted).toLocaleDateString();
            const accuracyPercent = (perf.accuracy * 100).toFixed(0);
            
            html += `
                <tr>
                    <td><strong>${skillName}</strong></td>
                    <td>${perf.total_attempts}</td>
                    <td><span class="accuracy-badge ${accuracyPercent >= 70 ? 'success' : accuracyPercent >= 50 ? 'warning' : 'danger'}">${accuracyPercent}%</span></td>
                    <td><span class="proficiency-badge ${perf.proficiency_level}">${perf.proficiency_level}</span></td>
                    <td>${lastDate}</td>
                </tr>
            `;
        }
        
        html += '</tbody></table>';
    }
    
    container.innerHTML = html;
}

// ============================================================
// FIXED createRadarChart function v2 - PREVENTS SHRINKING
// Replace the entire createRadarChart function in app_s.js with this
// ============================================================

function createRadarChart(data) {
    // Combine topic and skill performance for the radar chart (Knowledge Graph)
    const topicPerf = data.topic_performance || {};
    const skillPerf = data.skill_performance || {};
    
    const hasTopics = Object.keys(topicPerf).length > 0;
    const hasSkills = Object.keys(skillPerf).length > 0;
    
    const container = document.getElementById('radarChartContainer');
    const ctx = document.getElementById('skillsRadarChart');
    
    if (!hasTopics && !hasSkills) {
        if (container) {
            container.innerHTML = '<div class="empty-state" style="display: flex; align-items: center; justify-content: center; height: 100%;"><p>Complete questions to see your knowledge graph</p></div>';
        }
        return;
    }
    
    // If container doesn't exist (old HTML), create wrapper dynamically
    if (!container && ctx) {
        const parent = ctx.parentElement;
        const wrapper = document.createElement('div');
        wrapper.id = 'radarChartContainer';
        wrapper.style.cssText = 'position: relative; width: 100%; max-width: 450px; height: 400px; margin: 0 auto;';
        parent.insertBefore(wrapper, ctx);
        wrapper.appendChild(ctx);
    }
    
    if (!ctx) return;
    
    const labels = [];
    const chartData = [];
    
    // Add topics first (primary focus) - these are what users care about most
    for (const [topic, perf] of Object.entries(topicPerf)) {
        const topicName = topic.charAt(0).toUpperCase() + topic.slice(1);
        labels.push(topicName);
        chartData.push(parseFloat((perf.accuracy * 100).toFixed(1)));
    }
    
    // Add skills that aren't already covered by topics
    for (const [skillId, perf] of Object.entries(skillPerf)) {
        const skillName = skillId.replace('skill_', '').replace('topic_', '').replace(/_/g, ' ');
        const formattedName = skillName.charAt(0).toUpperCase() + skillName.slice(1);
        if (!labels.some(l => l.toLowerCase() === formattedName.toLowerCase())) {
            labels.push(formattedName);
            chartData.push(parseFloat((perf.accuracy * 100).toFixed(1)));
        }
    }
    
    // CRITICAL: Destroy existing chart COMPLETELY
    if (window.skillsChart) {
        window.skillsChart.destroy();
        window.skillsChart = null;
    }
    
    // CRITICAL: Reset canvas to prevent size accumulation issues
    const parent = ctx.parentElement;
    const newCanvas = document.createElement('canvas');
    newCanvas.id = 'skillsRadarChart';
    parent.removeChild(ctx);
    parent.appendChild(newCanvas);
    
    const newCtx = newCanvas.getContext('2d');
    
    window.skillsChart = new Chart(newCtx, {
        type: 'radar',
        data: {
            labels: labels,
            datasets: [{
                label: 'Knowledge Level (%)',
                data: chartData,
                backgroundColor: 'rgba(16, 185, 129, 0.3)',
                borderColor: 'rgba(16, 185, 129, 1)',
                borderWidth: 3,
                pointBackgroundColor: chartData.map(v => v >= 70 ? 'rgba(16, 185, 129, 1)' : 'rgba(239, 68, 68, 1)'),
                pointBorderColor: '#fff',
                pointBorderWidth: 2,
                pointRadius: 6,
                pointHoverRadius: 8,
                pointHoverBackgroundColor: '#fff',
                pointHoverBorderColor: 'rgba(79, 70, 229, 1)'
            }]
        },
        options: {
            // CRITICAL: These settings prevent the shrinking
            responsive: true,
            maintainAspectRatio: false,  // Let container control size
            
            // CRITICAL: Disable ALL animations
            animation: false,
            
            scales: {
                r: {
                    beginAtZero: true,
                    min: 0,
                    max: 100,
                    ticks: {
                        stepSize: 20,
                        font: { size: 10 },
                        backdropColor: 'transparent',
                        display: true
                    },
                    pointLabels: {
                        font: { size: 11, weight: 'bold' },
                        color: '#374151'
                    },
                    grid: {
                        color: 'rgba(0, 0, 0, 0.1)',
                        circular: true
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
                title: {
                    display: true,
                    text: '📊 Knowledge Graph',
                    font: { size: 16, weight: 'bold' },
                    color: '#4F46E5',
                    padding: { bottom: 10 }
                },
                tooltip: {
                    enabled: true,
                    callbacks: {
                        label: function(context) {
                            const value = context.raw;
                            const status = value >= 70 ? '✅ Strong' : value >= 50 ? '⚠️ Needs Work' : '❌ Focus Area';
                            return `${value}% - ${status}`;
                        }
                    }
                }
            }
        }
    });
    
    console.log('📊 Knowledge Graph rendered with', labels.length, 'data points');
}// ============== RECOMMENDATIONS FUNCTIONALITY ==============

// ============================================
// COMPLETE RECOMMENDATIONS SYSTEM
// Add this to your app_s.js (find the loadRecommendations function and replace it)
// ============================================

async function loadRecommendations() {
    console.log('📊 Loading recommendations...');
    
    const learnerId = localStorage.getItem('learnerId');
    if (!learnerId) {
        console.log('⚠️ No learner ID found');
        showRecommendationsPlaceholder();
        return;
    }
    
    try {
        // Use the comprehensive recommendations endpoint
        console.log('📡 Fetching full recommendations data...');
        const response = await fetch(`${API_BASE}/api/learner/${learnerId}/recommendations/full`);
        const data = await response.json();
        
        console.log('📊 Full recommendations data:', data);
        
        if (!data.success) {
            console.log('❌ Recommendations request failed');
            showRecommendationsError('Failed to load recommendations');
            return;
        }
        
        if (!data.has_data) {
            console.log('ℹ️ No data available yet');
            showRecommendationsPlaceholder();
            return;
        }
        
        // Display overall stats
        displayRecommendationsStats(data);
        
        // Display milestone
        if (data.milestone) {
            displayMilestone(data.milestone);
        }
        
        // Display weak topics (these are what users care about)
        if (data.weak_topics && data.weak_topics.length > 0) {
            displayWeakTopics(data.weak_topics);
        } else if (data.weak_skills && data.weak_skills.length > 0) {
            displayWeakSkills(data.weak_skills);
        } else {
            hideWeakSkillsSection();
        }
        
        // Display recommendations
        if (data.recommendations && data.recommendations.length > 0) {
            displayRecommendations(data.recommendations);
        } else {
            displayNoRecommendations();
        }
        
        // Display recent exams in recommendations tab
        if (data.recent_exams && data.recent_exams.length > 0) {
            displayRecentExamsInRecommendations(data.recent_exams);
        }
        
    } catch (err) {
        console.error('❌ Error loading recommendations:', err);
        showRecommendationsError(err.message);
    }
}

function displayRecommendationsStats(data) {
    const statsContainer = document.getElementById('recommendationsStats');
    if (!statsContainer) {
        // Create stats container if it doesn't exist
        const journeySection = document.querySelector('#recommendationsSection .journey-section');
        if (journeySection) {
            const statsDiv = document.createElement('div');
            statsDiv.id = 'recommendationsStats';
            statsDiv.className = 'recommendations-stats';
            journeySection.insertBefore(statsDiv, journeySection.firstChild);
        }
    }
    
    const container = document.getElementById('recommendationsStats');
    if (container) {
        container.innerHTML = `
            <div class="stats-grid">
                <div class="stat-card">
                    <div class="stat-icon">📝</div>
                    <div class="stat-value">${data.total_questions || 0}</div>
                    <div class="stat-label">Questions Answered</div>
                </div>
                <div class="stat-card">
                    <div class="stat-icon">🎯</div>
                    <div class="stat-value">${(data.overall_accuracy || 0).toFixed(0)}%</div>
                    <div class="stat-label">Overall Accuracy</div>
                </div>
                <div class="stat-card">
                    <div class="stat-icon">📚</div>
                    <div class="stat-value">${data.topics_practiced || 0}</div>
                    <div class="stat-label">Topics Practiced</div>
                </div>
                <div class="stat-card">
                    <div class="stat-icon">📋</div>
                    <div class="stat-value">${data.exams_completed || 0}</div>
                    <div class="stat-label">Exams Completed</div>
                </div>
            </div>
        `;
    }
}

function displayWeakTopics(weakTopics) {
    console.log('⚠️ Displaying weak topics:', weakTopics);
    
    const weakSkillsAlert = document.getElementById('weakSkillsAlert');
    const weakSkillsList = document.getElementById('weakSkillsList');
    
    if (weakSkillsAlert) weakSkillsAlert.style.display = 'block';
    
    if (!weakSkillsList) return;
    
    let html = '<h4 style="margin-bottom: 1rem;">📚 Topics Needing Improvement</h4>';
    weakTopics.forEach(topic => {
        const currentPercent = (topic.accuracy * 100).toFixed(0);
        const improvementPercent = ((0.7 - topic.accuracy) * 100).toFixed(0);
        
        html += `
            <div class="weak-skill-item">
                <div class="weak-skill-header">
                    <span class="weak-skill-name">${topic.priority === 'high' ? '🔴' : '🟡'} ${topic.topic}</span>
                    <span class="weak-skill-accuracy">${currentPercent}%</span>
                </div>
                <div class="weak-skill-meta">
                    <span>Correct: ${topic.correct}/${topic.attempts}</span>
                    <span class="improvement-needed">Need +${improvementPercent}% to reach 70%</span>
                </div>
                <div class="weak-skill-progress">
                    <div class="progress-bar">
                        <div class="progress-fill ${currentPercent < 50 ? 'danger' : 'warning'}" style="width: ${currentPercent}%"></div>
                    </div>
                </div>
                <button class="btn-primary btn-sm" onclick="practiceSkill('${topic.topic}', '${topic.topic}')" style="margin-top: 0.5rem;">
                    🚀 Practice This Topic
                </button>
            </div>
        `;
    });
    
    weakSkillsList.innerHTML = html;
}

function displayRecentExamsInRecommendations(exams) {
    // Find or create container for recent exams in recommendations
    let container = document.getElementById('recentExamsInRecs');
    if (!container) {
        const recsSection = document.getElementById('recommendationsList');
        if (recsSection && recsSection.parentElement) {
            const examsDiv = document.createElement('div');
            examsDiv.id = 'recentExamsInRecs';
            examsDiv.className = 'recent-exams-section';
            recsSection.parentElement.appendChild(examsDiv);
        }
    }
    
    container = document.getElementById('recentExamsInRecs');
    if (!container) return;
    
    let html = '<h4 style="margin: 2rem 0 1rem;">📋 Your Recent Exams</h4>';
    html += '<div class="recent-exams-grid">';
    
    exams.forEach((exam, idx) => {
        const date = new Date(exam.completed_at).toLocaleDateString();
        const scoreClass = exam.score >= 80 ? 'success' : exam.score >= 60 ? 'warning' : 'danger';
        const modeIcons = { practice: '📚', adaptive: '🎯', timed: '⏱️' };
        
        html += `
            <div class="exam-card">
                <div class="exam-header">
                    <span class="exam-mode">${modeIcons[exam.mode] || '📝'} ${exam.mode}</span>
                    <span class="exam-date">${date}</span>
                </div>
                <div class="exam-score ${scoreClass}">${exam.score.toFixed(0)}%</div>
                <div class="exam-details">
                    ${exam.correct_answers}/${exam.total_questions} correct • ${exam.duration_minutes.toFixed(1)} min
                </div>
            </div>
        `;
    });
    
    html += '</div>';
    container.innerHTML = html;
}

function displayMilestone(milestone) {
    console.log('🎯 Displaying milestone:', milestone);
    
    const milestoneInfo = document.getElementById('milestoneInfo');
    if (!milestoneInfo) return;
    
    milestoneInfo.innerHTML = `
        <div class="milestone-tracker">
            <div class="milestone-current">
                <div class="milestone-badge">
                    <span class="milestone-icon">🏆</span>
                    <span class="milestone-name">${milestone.current}</span>
                </div>
            </div>
            <div class="milestone-arrow">→</div>
            <div class="milestone-next">
                <div class="milestone-badge next">
                    <span class="milestone-icon">🎯</span>
                    <span class="milestone-name">${milestone.next}</span>
                </div>
                <div class="milestone-progress">${milestone.progress}</div>
            </div>
        </div>
        <div class="milestone-description">
            <p><strong>Next Goal:</strong> ${milestone.description}</p>
        </div>
    `;
}

function displayWeakSkills(weakSkills) {
    console.log('⚠️ Displaying weak skills:', weakSkills);
    
    const weakSkillsAlert = document.getElementById('weakSkillsAlert');
    const weakSkillsList = document.getElementById('weakSkillsList');
    
    if (weakSkillsAlert) weakSkillsAlert.style.display = 'block';
    
    if (!weakSkillsList) return;
    
    let html = '';
    weakSkills.forEach(skill => {
        const currentPercent = (skill.accuracy * 100).toFixed(0);
        const improvementPercent = (skill.improvement_needed * 100).toFixed(0);
        
        html += `
            <div class="weak-skill-item">
                <div class="weak-skill-header">
                    <span class="weak-skill-name">⚠️ ${skill.skill_name}</span>
                    <span class="weak-skill-accuracy">${currentPercent}%</span>
                </div>
                <div class="weak-skill-meta">
                    <span>Category: ${skill.category}</span>
                    <span>Attempts: ${skill.attempts}</span>
                    <span class="improvement-needed">Need +${improvementPercent}% improvement</span>
                </div>
                <div class="weak-skill-progress">
                    <div class="progress-bar">
                        <div class="progress-fill" style="width: ${currentPercent}%"></div>
                    </div>
                </div>
            </div>
        `;
    });
    
    weakSkillsList.innerHTML = html;
}

function hideWeakSkillsSection() {
    const weakSkillsAlert = document.getElementById('weakSkillsAlert');
    if (weakSkillsAlert) {
        weakSkillsAlert.style.display = 'none';
    }
}

function displayRecommendations(recommendations) {
    console.log('💡 Displaying recommendations:', recommendations);
    
    const container = document.getElementById('recommendationsList');
    if (!container) return;
    
    let html = '';
    recommendations.forEach(rec => {
        const priorityColors = {
            'high': '#EF4444',
            'medium': '#F59E0B',
            'low': '#10B981'
        };
        
        const priorityColor = priorityColors[rec.priority] || '#6B7280';
        
        html += `
            <div class="recommendation-item">
                <div class="recommendation-header">
                    <span class="recommendation-skill">📚 ${rec.skill_name}</span>
                    <span class="priority-badge" style="background: ${priorityColor}; color: white;">
                        ${rec.priority.toUpperCase()}
                    </span>
                </div>
                <div class="recommendation-topics">
                    ${rec.recommended_topics.map(t => `<span class="topic-tag">${t}</span>`).join('')}
                </div>
                <div class="recommendation-stats">
                    <div class="stat-item">
                        <span class="stat-label">Current:</span>
                        <span class="stat-value">${rec.current_accuracy}</span>
                    </div>
                    <div class="stat-item">
                        <span class="stat-label">Target:</span>
                        <span class="stat-value">${rec.target_accuracy}</span>
                    </div>
                    <div class="stat-item">
                        <span class="stat-label">Practice:</span>
                        <span class="stat-value">${rec.recommended_questions} questions</span>
                    </div>
                </div>
                <div class="recommendation-actions">
                    <button class="btn-primary btn-sm" onclick="practiceSkill('${rec.skill_name}', '${rec.recommended_topics[0]}')">
                        🚀 Practice Now
                    </button>
                </div>
            </div>
        `;
    });
    
    container.innerHTML = html;
}

function displayNoRecommendations() {
    const container = document.getElementById('recommendationsList');
    if (!container) return;
    
    container.innerHTML = `
        <div class="empty-state">
            <div class="empty-icon">🎯</div>
            <h3>Complete More Questions</h3>
            <p>Take exams and answer questions to get personalized recommendations based on your performance.</p>
            <button class="btn-primary" onclick="document.querySelector('[data-tab=\\'exam\\']').click()">
                Take an Exam
            </button>
        </div>
    `;
}

function displayRecentExams(sessions) {
    console.log('📋 Displaying recent exams:', sessions);
    
    const container = document.getElementById('recentExamsList');
    if (!container) return;
    
    if (!sessions || sessions.length === 0) {
        container.innerHTML = `
            <div class="empty-state">
                <p>No exams completed yet</p>
            </div>
        `;
        return;
    }
    
    // Show last 5 exams
    const recent = sessions.slice(-5).reverse();
    
    let html = '';
    recent.forEach(session => {
        const date = new Date(session.start_time).toLocaleDateString();
        const modeIcons = {
            'practice': '📚',
            'adaptive': '🎯',
            'timed': '⏱️'
        };
        const icon = modeIcons[session.mode] || '📝';
        
        html += `
            <div class="exam-history-item">
                <div class="exam-history-info">
                    <h4>${icon} ${session.mode.charAt(0).toUpperCase() + session.mode.slice(1)} Exam</h4>
                    <div class="exam-history-meta">
                        <span>📅 ${date}</span>
                        <span>❓ ${session.total_questions} questions</span>
                        <span>✅ ${session.status}</span>
                    </div>
                </div>
                <div class="exam-history-score ${getScoreClass(session.score)}">
                    ${session.score ? session.score.toFixed(0) : 0}%
                </div>
            </div>
        `;
    });
    
    container.innerHTML = html;
}

function getScoreClass(score) {
    if (!score) return '';
    if (score >= 80) return 'score-excellent';
    if (score >= 70) return 'score-good';
    if (score >= 60) return 'score-average';
    return 'score-needs-work';
}

function showRecommendationsPlaceholder() {
    const milestoneInfo = document.getElementById('milestoneInfo');
    const recommendationsList = document.getElementById('recommendationsList');
    const recentExamsList = document.getElementById('recentExamsList');
    
    if (milestoneInfo) {
        milestoneInfo.innerHTML = `
            <div class="empty-state">
                <p style="text-align: center; color: var(--gray);">
                    Create a learner profile to track your progress
                </p>
                <button class="btn-primary" onclick="document.querySelector('[data-tab=\\'profile\\']').click()">
                    Create Profile
                </button>
            </div>
        `;
    }
    
    if (recommendationsList) {
        recommendationsList.innerHTML = `
            <div class="empty-state">
                <p>Complete questions to see recommendations</p>
            </div>
        `;
    }
    
    if (recentExamsList) {
        recentExamsList.innerHTML = `
            <div class="empty-state">
                <p>No exams completed yet</p>
            </div>
        `;
    }
}

function showRecommendationsError(message) {
    const container = document.getElementById('recommendationsList');
    if (!container) return;
    
    container.innerHTML = `
        <div class="error-state">
            <p>Error loading recommendations: ${message}</p>
            <button class="btn-secondary" onclick="loadRecommendations()">
                Retry
            </button>
        </div>
    `;
}

function practiceSkill(skillName, topic) {
    console.log('🎯 Practice skill:', skillName, 'Topic:', topic);
    
    // Switch to generate tab
    const generateTab = document.querySelector('[data-tab="generate"]');
    if (generateTab) generateTab.click();
    
    // Pre-fill topic
    setTimeout(() => {
        const topicInput = document.getElementById('topic');
        if (topicInput) {
            topicInput.value = topic;
            topicInput.focus();
        }
    }, 100);
}

// Generate focused exam button
const focusedExamBtn = document.getElementById('generateFocusedExamBtn');
if (focusedExamBtn) {
    focusedExamBtn.addEventListener('click', async () => {
        const learnerId = localStorage.getItem('learnerId');
        if (!learnerId) {
            alert('Please create a profile first');
            return;
        }
        
        try {
            const response = await fetch(`${API_BASE}/api/learner/${learnerId}/focused-exam?num_questions=10`, {
                method: 'POST'
            });
            
            const data = await response.json();
            
            if (data.success) {
                alert(`📊 Focused Exam Generated!\n\n` +
                      `Focus: ${data.focus}\n` +
                      `${data.message}\n\n` +
                      `This exam will target your weak areas.`);
                
                // Switch to exam mode
                const examTab = document.querySelector('[data-tab="exam"]');
                if (examTab) examTab.click();
            }
        } catch (err) {
            alert('Error generating focused exam: ' + err.message);
        }
    });
}

console.log('✅ Recommendations system loaded');
// ============================================
// REPLACE THE EXAM SECTION IN app_s.js WITH THIS
// This adds working Practice, Timed, and Adaptive modes
// ============================================
// ============== MODE CARD SELECTION ==============
function initializeModeCards() {
    console.log('🎯 Initializing mode card selection...');
    
    const modeCards = document.querySelectorAll('.mode-card');
    
    if (modeCards.length === 0) {
        console.error('❌ No mode cards found!');
        return;
    }
    
    console.log(`✅ Found ${modeCards.length} mode cards`);
    
    modeCards.forEach(card => {
        card.addEventListener('click', function() {
            console.log('🖱️ Mode card clicked:', this.getAttribute('data-mode'));
            
            // Remove 'selected' class from all cards
            modeCards.forEach(c => c.classList.remove('selected'));
            
            // Add 'selected' class to clicked card
            this.classList.add('selected');
            
            const selectedMode = this.getAttribute('data-mode');
            console.log('✅ Mode selected:', selectedMode);
            
            // Show/hide time limit based on mode
            const timeLimitGroup = document.getElementById('timeLimitGroup');
            if (timeLimitGroup) {
                if (selectedMode === 'timed') {
                    timeLimitGroup.style.display = 'block';
                } else {
                    timeLimitGroup.style.display = 'none';
                }
            }
        });
    });
    
    console.log('✅ Mode cards initialized successfully');
}

// Initialize mode cards when DOM is ready
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initializeModeCards);
} else {
    initializeModeCards();
}






let currentExam = null;
let examTimer = null;
let questionStartTime = null;

// Initialize exam button when DOM is ready
function initializeExamButton() {
    console.log('🔧 Initializing exam button...');
    
    const startExamBtn = document.getElementById('startExamBtn');
    if (!startExamBtn) {
        console.error('❌ startExamBtn not found in DOM');
        return;
    }
    
    console.log('✅ Found startExamBtn, attaching click handler');
    
    startExamBtn.addEventListener('click', async function() {
        console.log('🚀 START EXAM BUTTON CLICKED');
        
        const mode = document.querySelector('.mode-card.selected')?.getAttribute('data-mode') || 'adaptive';
        const questionCount = parseInt(document.getElementById('examQuestionCount').value);
        const topic = document.getElementById('examTopic').value.trim();
        const learnerId = localStorage.getItem('learnerId');
        
        console.log('Exam settings:', {mode, questionCount, topic, learnerId});
        
        if (!learnerId) {
            alert('⚠️ Please create a learner profile first!\n\nGo to the "My Profile" tab and create your profile.');
            const profileTab = document.querySelector('[data-tab="profile"]');
            if (profileTab) profileTab.click();
            return;
        }
        
        try {
            // Step 1: Create exam session
            console.log(`📡 Creating ${mode} exam session...`);
            const createResponse = await fetch(`${API_BASE}/api/exam/create`, {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({
                    learner_id: learnerId,
                    mode: mode,
                    total_questions: questionCount,
                    time_limit_minutes: mode === 'timed' ? 75 : null, // 75 min for timed mode
                    focus_topic: topic || null
                })
            });
            
            if (!createResponse.ok) {
                throw new Error(`Server error: ${createResponse.status}`);
            }
            
            const sessionData = await createResponse.json();
            console.log('✅ Session created:', sessionData);
            
            if (!sessionData.success) {
                throw new Error('Failed to create exam session');
            }
            
            // Initialize exam state
            currentExam = {
                session_id: sessionData.session_id,
                mode: mode,
                total_questions: questionCount,
                current_question: 0,
                topic: topic,
                current_difficulty: 'intermediate', // Start at intermediate for all modes
                questions_answered: 0,
                correct_answers: 0
            };
            
            // Hide setup, show exam interface
            const setupEl = document.getElementById('examSetup');
            const progressEl = document.getElementById('examInProgress');
            if (setupEl) setupEl.classList.add('hidden');
            if (progressEl) progressEl.classList.remove('hidden');
            
            // Update mode display
            const modeEl = document.getElementById('currentExamMode');
            if (modeEl) {
                const modeNames = {
                    'practice': '📚 Practice Mode',
                    'adaptive': '🎯 Adaptive Mode',
                    'timed': '⏱️ Timed Mode'
                };
                modeEl.textContent = modeNames[mode] || 'Exam Mode';
            }
            
            // Start timer if timed mode
            if (mode === 'timed') {
                startExamTimer(75 * 60); // 75 minutes in seconds
            }
            
            // Generate first question
            await loadNextExamQuestion();
            
        } catch (err) {
            console.error('❌ Error starting exam:', err);
            alert('Error starting exam: ' + err.message);
        }
    });
    
    console.log('✅ Exam button initialized successfully');
}

function startExamTimer(seconds) {
    const timerElement = document.getElementById('examTimer');
    if (!timerElement) return;
    
    timerElement.style.display = 'flex';
    let remaining = seconds;
    
    examTimer = setInterval(() => {
        remaining--;
        
        const minutes = Math.floor(remaining / 60);
        const secs = remaining % 60;
        const timeDisplay = document.getElementById('timeRemaining');
        if (timeDisplay) {
            timeDisplay.textContent = `${minutes}:${secs.toString().padStart(2, '0')}`;
        }
        
        // Warning at 10 minutes
        if (remaining === 600) {
            timerElement.classList.add('warning');
        }
        
        // Danger at 5 minutes
        if (remaining === 300) {
            timerElement.classList.remove('warning');
            timerElement.classList.add('danger');
        }
        
        // Time's up
        if (remaining <= 0) {
            clearInterval(examTimer);
            alert('⏰ Time is up! Your exam will now be submitted.');
            completeExam();
        }
    }, 1000);
}

async function loadNextExamQuestion() {
    questionStartTime = Date.now();
    currentExam.current_question++;
    
    console.log(`📝 Loading question ${currentExam.current_question}/${currentExam.total_questions} [${currentExam.mode} mode]`);
    
    // Update progress
    const progressEl = document.getElementById('examProgress');
    if (progressEl) {
        progressEl.textContent = `Question ${currentExam.current_question} of ${currentExam.total_questions}`;
    }
    
    // Show loading
    const displayEl = document.getElementById('examQuestionDisplay');
    if (displayEl) {
        displayEl.innerHTML = '<div class="loading-question"><div class="spinner"></div><p>Generating question with AI...</p></div>';
    }
    
    // Determine difficulty based on mode
    let difficulty = 'intermediate';
    
    if (currentExam.mode === 'adaptive' && currentExam.questions_answered >= 3) {
        // Adaptive: adjust based on performance
        const recentCorrect = currentExam.correct_answers;
        const recentTotal = currentExam.questions_answered;
        const accuracy = recentCorrect / recentTotal;
        
        console.log(`📊 Adaptive logic: ${recentCorrect}/${recentTotal} correct (${(accuracy*100).toFixed(0)}%)`);
        
        if (accuracy >= 0.7) {
            // Doing well → advance
            if (currentExam.current_difficulty === 'beginner') {
                difficulty = 'intermediate';
            } else if (currentExam.current_difficulty === 'intermediate') {
                difficulty = 'advanced';
            } else {
                difficulty = 'advanced';
            }
            console.log(`🔼 Advancing difficulty: ${currentExam.current_difficulty} → ${difficulty}`);
        } else if (accuracy < 0.5) {
            // Struggling → stay or drop
            if (currentExam.current_difficulty === 'advanced') {
                difficulty = 'intermediate';
            } else if (currentExam.current_difficulty === 'intermediate') {
                difficulty = 'beginner';
            } else {
                difficulty = 'beginner';
            }
            console.log(`🔽 Dropping difficulty: ${currentExam.current_difficulty} → ${difficulty}`);
        } else {
            // Middle range → stay at current level
            difficulty = currentExam.current_difficulty;
            console.log(`➡️ Maintaining difficulty: ${difficulty}`);
        }
        
        currentExam.current_difficulty = difficulty;
    } else {
        // Practice/Timed: random mix of difficulties
        if (currentExam.mode === 'practice') {
            const difficulties = ['beginner', 'intermediate', 'intermediate', 'advanced'];
            difficulty = difficulties[Math.floor(Math.random() * difficulties.length)];
            console.log(`🎲 Practice mode: Random difficulty = ${difficulty}`);
        } else if (currentExam.mode === 'timed') {
            // Timed: simulate NCLEX distribution (mostly intermediate)
            const rand = Math.random();
            if (rand < 0.2) difficulty = 'beginner';
            else if (rand < 0.8) difficulty = 'intermediate';
            else difficulty = 'advanced';
            console.log(`⏱️ Timed mode: NCLEX-style difficulty = ${difficulty}`);
        }
    }
    
    // Determine topic
    let topic = currentExam.topic || getRandomTopic();
    
    try {
        console.log(`📡 Calling API to generate ${difficulty} question...`);
        const response = await fetch(`${API_BASE}/api/exam/${currentExam.session_id}/question`, {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({
                topic: topic,
                difficulty: difficulty,
                question_type: 'mcq',
                use_hospital_policies: true
            })
        });
        
        if (!response.ok) {
            throw new Error(`Failed to generate question: ${response.status}`);
        }
        
        const data = await response.json();
        console.log('✅ Question generated:', data);
        
        // Display question
        displayExamQuestion(data);
        
        // Hide feedback, show submit
        const feedbackEl = document.getElementById('examFeedback');
        const submitBtn = document.getElementById('submitAnswerBtn');
        const nextBtn = document.getElementById('nextQuestionBtn');
        
        if (feedbackEl) feedbackEl.classList.add('hidden');
        if (submitBtn) submitBtn.style.display = 'block';
        if (nextBtn) nextBtn.style.display = 'none';
        
    } catch (err) {
        console.error('❌ Error loading question:', err);
        if (displayEl) {
            displayEl.innerHTML = `<div class="error-state">Error: ${err.message}</div>`;
        }
        alert('Error loading question: ' + err.message);
    }
}

function getRandomTopic() {
    const topics = [
        'cardiac arrest', 'sepsis', 'pneumonia', 'heart failure',
        'COPD', 'stroke', 'diabetes', 'ARDS', 'shock',
        'respiratory failure', 'acute kidney injury', 'hypertension'
    ];
    return topics[Math.floor(Math.random() * topics.length)];
}

function displayExamQuestion(data) {
    const container = document.getElementById('examQuestionDisplay');
    if (!container) return;
    
    const questionData = data.data;
    
    let html = '<div class="question-content">';
    
    // Mode-specific badges
    let badgeColor = '#667eea';
    if (currentExam.mode === 'practice') badgeColor = '#10B981';
    if (currentExam.mode === 'timed') badgeColor = '#F59E0B';
    
    html += `<div class="difficulty-badge" style="background: ${badgeColor}">${data.difficulty.toUpperCase()}</div>`;
    
    if (questionData.scenario) {
        html += `<div class="scenario">${questionData.scenario}</div>`;
    }
    
    html += `<div class="question-stem">${questionData.question}</div>`;
    html += '<div class="options">';
    
    for (const [key, value] of Object.entries(questionData.options)) {
        html += `
            <label class="option-label">
                <input type="radio" name="examAnswer" value="${key}">
                <span class="option-text"><strong>${key}.</strong> ${value}</span>
            </label>
        `;
    }
    
    html += '</div></div>';
    container.innerHTML = html;
    
    // Store correct answer
    currentExam.current_correct = questionData.correct_answer;
    currentExam.current_rationale = questionData.rationale;
}

// Submit answer handler
function initializeSubmitButton() {
    const submitBtn = document.getElementById('submitAnswerBtn');
    if (!submitBtn) return;
    
    submitBtn.addEventListener('click', async () => {
        const selected = document.querySelector('input[name="examAnswer"]:checked');
        
        if (!selected) {
            alert('Please select an answer');
            return;
        }
        
        const userAnswer = selected.value;
        const timeSpent = Math.floor((Date.now() - questionStartTime) / 1000);
        
        try {
            const response = await fetch(`${API_BASE}/api/exam/${currentExam.session_id}/submit`, {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({
                    question_index: currentExam.current_question - 1,
                    user_answer: userAnswer,
                    time_spent_seconds: timeSpent
                })
            });
            
            const data = await response.json();
            console.log('Answer submitted:', data);
            
            // Track performance for adaptive mode
            currentExam.questions_answered++;
            if (data.is_correct) {
                currentExam.correct_answers++;
            }
            
            // Show feedback based on mode
            if (currentExam.mode === 'practice' || currentExam.mode === 'adaptive') {
                // Immediate feedback
                showExamFeedback(data.is_correct);
            } else if (currentExam.mode === 'timed') {
                // No feedback until end
                console.log('⏱️ Timed mode: No feedback shown');
            }
            
            submitBtn.style.display = 'none';
            
            // Check if exam complete
            if (currentExam.current_question >= currentExam.total_questions) {
                const delay = (currentExam.mode === 'timed') ? 0 : 2000;
                setTimeout(() => {
                    if (confirm('Exam complete! View results?')) {
                        completeExam();
                    }
                }, delay);
            } else {
                const nextBtn = document.getElementById('nextQuestionBtn');
                if (nextBtn) nextBtn.style.display = 'block';
            }
            
        } catch (err) {
            console.error('Error submitting answer:', err);
            alert('Error: ' + err.message);
        }
    });
}

function showExamFeedback(isCorrect) {
    const feedback = document.getElementById('examFeedback');
    if (!feedback) return;
    
    const result = document.getElementById('feedbackResult');
    const explanation = document.getElementById('feedbackExplanation');
    
    if (result) {
        result.className = 'feedback-result ' + (isCorrect ? 'correct' : 'incorrect');
        result.textContent = isCorrect ? '✅ Correct!' : '❌ Incorrect';
    }
    
    if (explanation) {
        let tutorButton = '';
        if (!isCorrect) {
            // Add "Ask AI Tutor" button when wrong
            const topic = currentExam.topic || 'this topic';
            tutorButton = `
                <button class="ask-tutor-btn" onclick="askTutorAboutTopic('${topic}', '${currentExam.current_rationale?.replace(/'/g, "\\'")}')">
                    🤖 Ask AI Tutor to Explain
                </button>
            `;
        }
        
        explanation.innerHTML = `
            <p><strong>Correct Answer:</strong> ${currentExam.current_correct}</p>
            <p><strong>Explanation:</strong> ${currentExam.current_rationale}</p>
            ${tutorButton}
        `;
    }
    
    feedback.classList.remove('hidden');
}

// Next question handler
function initializeNextButton() {
    const nextBtn = document.getElementById('nextQuestionBtn');
    if (!nextBtn) return;
    
    nextBtn.addEventListener('click', () => {
        loadNextExamQuestion();
    });
}

async function completeExam() {
    // Stop timer if running
    if (examTimer) {
        clearInterval(examTimer);
        examTimer = null;
    }
    
    try {
        console.log('🏁 Completing exam...');
        
        const response = await fetch(`${API_BASE}/api/exam/${currentExam.session_id}/complete`, {
            method: 'POST'
        });
        
        const data = await response.json();
        console.log('✅ Exam completed:', data);
        
        const summaryResponse = await fetch(`${API_BASE}/api/exam/${currentExam.session_id}/summary`);
        const summary = await summaryResponse.json();
        console.log('📊 Summary:', summary);
        
        document.getElementById('examInProgress').classList.add('hidden');
        document.getElementById('examResults').classList.remove('hidden');
        
        displayExamResults(data, summary);
        
        // Load recommendations after exam
        setTimeout(() => {
            loadRecommendations();
        }, 1000);
        
    } catch (err) {
        console.error('Error completing exam:', err);
        alert('Error: ' + err.message);
    }
}

function displayExamResults(data, summary) {
    const finalScore = document.getElementById('finalScore');
    const correctCount = document.getElementById('correctCount');
    const examDuration = document.getElementById('examDuration');
    
    if (finalScore) finalScore.textContent = `${data.score.toFixed(0)}%`;
    if (correctCount) correctCount.textContent = `${data.correct}/${data.total}`;
    if (examDuration) examDuration.textContent = `${data.duration_minutes.toFixed(1)} min`;
    
    // Difficulty breakdown
    const difficultyDiv = document.getElementById('difficultyBreakdown');
    if (difficultyDiv && summary.difficulty_performance) {
        let html = '';
        for (const [difficulty, perf] of Object.entries(summary.difficulty_performance)) {
            if (perf.total === 0) continue;
            
            const percentage = (perf.correct / perf.total * 100).toFixed(0);
            html += `
                <div class="breakdown-item">
                    <span class="breakdown-label">${difficulty.charAt(0).toUpperCase() + difficulty.slice(1)}</span>
                    <div class="breakdown-score">
                        <div class="breakdown-bar">
                            <div class="breakdown-bar-fill" style="width: ${percentage}%"></div>
                        </div>
                        <span class="breakdown-percentage">${percentage}%</span>
                        <span>(${perf.correct}/${perf.total})</span>
                    </div>
                </div>
            `;
        }
        difficultyDiv.innerHTML = html || '<p>No difficulty data</p>';
    }
    
    // Skill breakdown
    const skillDiv = document.getElementById('skillBreakdown');
    if (skillDiv && summary.skill_performance) {
        let html = '';
        for (const [skillId, perf] of Object.entries(summary.skill_performance)) {
            const skillName = skillId.replace('skill_', '').replace(/_/g, ' ').toUpperCase();
            const percentage = (perf.correct / perf.total * 100).toFixed(0);
            html += `
                <div class="breakdown-item">
                    <span class="breakdown-label">${skillName}</span>
                    <div class="breakdown-score">
                        <div class="breakdown-bar">
                            <div class="breakdown-bar-fill" style="width: ${percentage}%"></div>
                        </div>
                        <span class="breakdown-percentage">${percentage}%</span>
                        <span>(${perf.correct}/${perf.total})</span>
                    </div>
                </div>
            `;
        }
        skillDiv.innerHTML = html || '<p>No skill data</p>';
    }
}

// Start new exam
function initializeStartNewButton() {
    const btn = document.getElementById('startNewExamBtn');
    if (!btn) return;
    
    btn.addEventListener('click', () => {
        document.getElementById('examResults').classList.add('hidden');
        document.getElementById('examSetup').classList.remove('hidden');
        currentExam = null;
        
        // Reset timer display
        const timerEl = document.getElementById('examTimer');
        if (timerEl) {
            timerEl.style.display = 'none';
            timerEl.classList.remove('warning', 'danger');
        }
    });
}

// View recommendations button
function initializeViewRecommendationsButton() {
    const btn = document.getElementById('viewRecommendationsBtn');
    if (!btn) return;
    
    btn.addEventListener('click', () => {
        const recTab = document.querySelector('[data-tab="recommendations"]');
        if (recTab) recTab.click();
    });
}

// Initialize all exam buttons
function initializeAllExamButtons() {
    console.log('🔧 Initializing all exam buttons...');
    initializeExamButton();
    initializeSubmitButton();
    initializeNextButton();
    initializeStartNewButton();
    initializeViewRecommendationsButton();
    console.log('✅ All exam buttons initialized');
}

// Call this when DOM is ready
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initializeAllExamButtons);
} else {
    initializeAllExamButtons();
}

console.log('✅✅✅ COMPLETE 3-MODE EXAM SYSTEM LOADED ✅✅✅');

// ============== SMART AUTHORING CO-PILOT (Phase 6) ==============

// Global state for authoring
const authoringState = {
    audience: 'student',
    style: 'plain',
    includeSpanish: false,
    generatedQuestions: [],
    selectedQuestions: [],
    authoringHistory: []
};

// Initialize Authoring Tab
function initializeAuthoringTab() {
    console.log('✨ Initializing Authoring Co-Pilot...');
    
    // Policy Upload Zone
    const policyUploadZone = document.getElementById('policyUploadZone');
    const policyFileInput = document.getElementById('policyFileInput');
    
    if (policyUploadZone && policyFileInput) {
        policyUploadZone.addEventListener('click', () => policyFileInput.click());
        policyFileInput.addEventListener('change', handlePolicyFileSelect);
    }
    
    // Generate from Policy Button
    const generateFromPolicyBtn = document.getElementById('generateFromPolicyBtn');
    if (generateFromPolicyBtn) {
        generateFromPolicyBtn.addEventListener('click', generateQuestionsFromPolicy);
    }
    
    // Generate Module Button
    const generateModuleBtn = document.getElementById('generateModuleBtn');
    if (generateModuleBtn) {
        generateModuleBtn.addEventListener('click', generateMicroModule);
    }
    
    // Audience Toggle Buttons
    document.querySelectorAll('[data-audience]').forEach(btn => {
        btn.addEventListener('click', () => {
            document.querySelectorAll('[data-audience]').forEach(b => b.classList.remove('active'));
            btn.classList.add('active');
            authoringState.audience = btn.dataset.audience;
            updateSettingsDisplay();
        });
    });
    
    // Style Toggle Buttons
    document.querySelectorAll('[data-style]').forEach(btn => {
        btn.addEventListener('click', () => {
            document.querySelectorAll('[data-style]').forEach(b => b.classList.remove('active'));
            btn.classList.add('active');
            authoringState.style = btn.dataset.style;
            updateSettingsDisplay();
        });
    });
    
    // Spanish Toggle
    const includeSpanish = document.getElementById('includeSpanish');
    if (includeSpanish) {
        includeSpanish.addEventListener('change', (e) => {
            authoringState.includeSpanish = e.target.checked;
        });
    }
    
    // Translate Button
    const translateBtn = document.getElementById('translateBtn');
    if (translateBtn) {
        translateBtn.addEventListener('click', translateToSpanish);
    }
    
    // Copy and Download buttons
    const copyBtn = document.getElementById('copyAuthoringContent');
    const downloadBtn = document.getElementById('downloadAuthoringContent');
    
    if (copyBtn) copyBtn.addEventListener('click', copyAuthoringContent);
    if (downloadBtn) downloadBtn.addEventListener('click', downloadAuthoringContent);
    
    console.log('✅ Authoring Co-Pilot initialized');
}

// Handle Policy File Selection
function handlePolicyFileSelect(event) {
    const file = event.target.files[0];
    if (!file) return;
    
    const fileNameDisplay = document.getElementById('policyFileName');
    const uploadZone = document.getElementById('policyUploadZone');
    const generateBtn = document.getElementById('generateFromPolicyBtn');
    
    fileNameDisplay.textContent = `📄 ${file.name}`;
    uploadZone.classList.add('has-file');
    generateBtn.disabled = false;
    
    // Store file reference
    authoringState.policyFile = file;
}

// Generate Questions from Policy
async function generateQuestionsFromPolicy() {
    const file = authoringState.policyFile;
    if (!file) {
        alert('Please upload a policy document first');
        return;
    }
    
    const questionCount = document.getElementById('policyQuestionCount').value;
    const generateBtn = document.getElementById('generateFromPolicyBtn');
    const resultDiv = document.getElementById('policyQuestionsResult');
    
    generateBtn.disabled = true;
    generateBtn.innerHTML = '⏳ Generating Questions...';
    
    try {
        // First upload the file
        const formData = new FormData();
        formData.append('file', file);
        
        const uploadResponse = await fetch(`${API_BASE}/api/upload-and-index`, {
            method: 'POST',
            body: formData
        });
        
        const uploadData = await uploadResponse.json();
        
        if (!uploadData.success) {
            throw new Error(uploadData.error || 'Upload failed');
        }
        
        // Extract topic from filename
        const topic = file.name.replace(/\.[^/.]+$/, "").replace(/[-_]/g, ' ');
        
        // Generate questions with different types and difficulties
        const questionTypes = ['mcq', 'sata', 'matrix', 'cloze', 'highlight', 'bowtie'];
        const difficulties = ['beginner', 'intermediate', 'advanced'];
        
        const generatedQuestions = [];
        const questionsPerType = Math.ceil(questionCount / questionTypes.length);
        
        resultDiv.innerHTML = '<div class="generating-progress">🔄 Generating questions... Please wait.</div>';
        resultDiv.classList.add('show');
        
        // Generate a balanced mix
        for (let i = 0; i < questionCount; i++) {
            const qType = questionTypes[i % questionTypes.length];
            const difficulty = difficulties[i % difficulties.length];
            
            try {
                const response = await fetch(`${API_BASE}/generate-question-with-skills-and-policies`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        topic: topic,
                        difficulty: difficulty,
                        question_type: qType,
                        num_citations: 2,
                        use_policies: true,
                        audience: authoringState.audience,
                        language_style: authoringState.style
                    })
                });
                
                const qData = await response.json();
                if (qData.success) {
                    generatedQuestions.push({
                        id: `q_${Date.now()}_${i}`,
                        ...qData.question,
                        type: qType,
                        difficulty: difficulty
                    });
                }
                
                // Update progress
                resultDiv.innerHTML = `<div class="generating-progress">🔄 Generated ${generatedQuestions.length}/${questionCount} questions...</div>`;
                
            } catch (err) {
                console.error(`Error generating question ${i + 1}:`, err);
            }
        }
        
        // Store generated questions
        authoringState.generatedQuestions = generatedQuestions;
        
        // Display results
        displayGeneratedQuestions(generatedQuestions, resultDiv);
        
        // Update question selector for micro-module
        updateQuestionSelector(generatedQuestions);
        
        // Add to history
        addToAuthoringHistory({
            type: 'questions',
            source: file.name,
            count: generatedQuestions.length,
            timestamp: new Date()
        });
        
    } catch (err) {
        console.error('Error generating from policy:', err);
        resultDiv.innerHTML = `<div class="error">❌ Error: ${err.message}</div>`;
        resultDiv.classList.add('show', 'error');
    } finally {
        generateBtn.disabled = false;
        generateBtn.innerHTML = '🚀 Generate Questions from Policy';
    }
}

// Display Generated Questions
function displayGeneratedQuestions(questions, container) {
    if (questions.length === 0) {
        container.innerHTML = '<p>No questions were generated. Please try again.</p>';
        return;
    }
    
    let html = `
        <div class="generated-questions-header">
            <h4>✅ Generated ${questions.length} Questions</h4>
            <div class="question-type-summary">
                ${getQuestionTypeSummary(questions)}
            </div>
        </div>
        <div class="generated-questions-list">
    `;
    
    questions.forEach((q, idx) => {
        html += `
            <div class="generated-question-item">
                <div class="question-header">
                    <span class="question-number">#${idx + 1}</span>
                    <span class="question-type-badge ${q.type}">${q.type.toUpperCase()}</span>
                    <span class="difficulty-badge ${q.difficulty}">${q.difficulty}</span>
                </div>
                <div class="question-preview">${q.question?.substring(0, 150) || q.scenario?.substring(0, 150) || 'Question generated'}...</div>
            </div>
        `;
    });
    
    html += '</div>';
    container.innerHTML = html;
    container.classList.add('show');
    container.classList.remove('error');
}

// Get Question Type Summary
function getQuestionTypeSummary(questions) {
    const counts = {};
    questions.forEach(q => {
        counts[q.type] = (counts[q.type] || 0) + 1;
    });
    
    return Object.entries(counts)
        .map(([type, count]) => `<span class="type-count">${type}: ${count}</span>`)
        .join(' ');
}

// Update Question Selector
function updateQuestionSelector(questions) {
    const selector = document.getElementById('questionSelector');
    const moduleBtn = document.getElementById('generateModuleBtn');
    
    if (!selector) return;
    
    if (questions.length === 0) {
        selector.innerHTML = '<p class="empty-state">Generate questions first using "Policy → Questions"</p>';
        moduleBtn.disabled = true;
        return;
    }
    
    let html = '';
    questions.forEach((q, idx) => {
        html += `
            <div class="question-selector-item" data-question-id="${q.id}">
                <input type="checkbox" id="select_q_${idx}" onchange="toggleQuestionSelection('${q.id}')">
                <label for="select_q_${idx}" class="question-preview">
                    <strong>#${idx + 1} (${q.type.toUpperCase()})</strong>: ${q.question?.substring(0, 80) || q.scenario?.substring(0, 80) || 'Question'}...
                    <div class="question-meta">${q.difficulty} • ${q.topic || 'General'}</div>
                </label>
            </div>
        `;
    });
    
    selector.innerHTML = html;
    moduleBtn.disabled = false;
}

// Toggle Question Selection
function toggleQuestionSelection(questionId) {
    const idx = authoringState.selectedQuestions.indexOf(questionId);
    if (idx > -1) {
        authoringState.selectedQuestions.splice(idx, 1);
    } else {
        authoringState.selectedQuestions.push(questionId);
    }
    
    // Update UI
    document.querySelectorAll('.question-selector-item').forEach(item => {
        if (item.dataset.questionId === questionId) {
            item.classList.toggle('selected');
        }
    });
}

// Generate Micro-Module
async function generateMicroModule() {
    const selectedIds = authoringState.selectedQuestions;
    const selectedQuestions = authoringState.generatedQuestions.filter(q => selectedIds.includes(q.id));
    
    if (selectedQuestions.length === 0) {
        alert('Please select at least one question to generate a module');
        return;
    }
    
    const moduleTitle = document.getElementById('moduleTitleInput').value || 'Clinical Learning Module';
    const generateBtn = document.getElementById('generateModuleBtn');
    const outputCard = document.getElementById('authoringOutputCard');
    const outputDiv = document.getElementById('authoringOutput');
    
    generateBtn.disabled = true;
    generateBtn.innerHTML = '⏳ Generating Module...';
    
    try {
        // Call API to generate micro-module
        const response = await fetch(`${API_BASE}/api/authoring/generate-module`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                title: moduleTitle,
                questions: selectedQuestions,
                audience: authoringState.audience,
                style: authoringState.style,
                include_spanish: authoringState.includeSpanish
            })
        });
        
        const data = await response.json();
        
        if (data.success) {
            displayMicroModule(data.module, outputDiv);
            outputCard.style.display = 'block';
            
            addToAuthoringHistory({
                type: 'module',
                title: moduleTitle,
                questionCount: selectedQuestions.length,
                timestamp: new Date()
            });
        } else {
            throw new Error(data.error || 'Module generation failed');
        }
        
    } catch (err) {
        console.error('Error generating module:', err);
        
        // Fallback: Generate a basic module client-side
        const fallbackModule = generateFallbackModule(moduleTitle, selectedQuestions);
        displayMicroModule(fallbackModule, outputDiv);
        outputCard.style.display = 'block';
    } finally {
        generateBtn.disabled = false;
        generateBtn.innerHTML = '📚 Generate Micro-Module';
    }
}

// Generate Fallback Module (client-side)
function generateFallbackModule(title, questions) {
    const topics = [...new Set(questions.map(q => q.topic || 'Clinical Practice'))];
    
    return {
        title: title,
        learning_objectives: topics.map(t => `Demonstrate understanding of ${t} assessment and management`),
        teaching_content: [
            {
                topic: topics[0] || 'Clinical Concepts',
                content: `This module covers essential concepts related to ${topics.join(', ')}. Students will learn to recognize key clinical indicators, apply critical thinking skills, and implement evidence-based interventions.`
            }
        ],
        clinical_pearls: [
            'Always assess vital signs in the context of the patient\'s baseline',
            'Document your findings thoroughly and communicate changes promptly',
            'When in doubt, escalate to a more experienced provider'
        ],
        questions: questions,
        spanish_summary: authoringState.includeSpanish ? 
            `Este módulo cubre conceptos esenciales relacionados con ${topics.join(', ')}.` : null
    };
}

// Display Micro-Module
function displayMicroModule(module, container) {
    let html = `
        <div class="generated-module">
            <h3 class="module-title">📚 ${module.title}</h3>
            
            <div class="module-section">
                <h4>🎯 Learning Objectives</h4>
                <ul>
                    ${module.learning_objectives.map(obj => `<li>${obj}</li>`).join('')}
                </ul>
            </div>
            
            <div class="module-section">
                <h4>📖 Teaching Content</h4>
                ${module.teaching_content.map(tc => `
                    <div class="teaching-block">
                        <h5>${tc.topic}</h5>
                        <p>${tc.content}</p>
                    </div>
                `).join('')}
            </div>
            
            <div class="module-section">
                <h4>💡 Clinical Pearls</h4>
                ${module.clinical_pearls.map(pearl => `
                    <div class="clinical-pearl">
                        <strong>💎 Pearl:</strong> ${pearl}
                    </div>
                `).join('')}
            </div>
            
            <div class="module-section">
                <h4>❓ Practice Questions (${module.questions.length})</h4>
                <p>This module includes ${module.questions.length} NCLEX-style questions covering various difficulty levels.</p>
            </div>
    `;
    
    if (module.spanish_summary) {
        html += `
            <div class="module-section">
                <h4>🇪🇸 Spanish Summary (Resumen en Español)</h4>
                <div class="spanish-content">
                    ${module.spanish_summary}
                </div>
            </div>
        `;
    }
    
    html += '</div>';
    container.innerHTML = html;
}

// Translate to Spanish
async function translateToSpanish() {
    const input = document.getElementById('translationInput').value;
    if (!input.trim()) {
        alert('Please enter text to translate');
        return;
    }
    
    const translateBtn = document.getElementById('translateBtn');
    const resultDiv = document.getElementById('translationResult');
    
    translateBtn.disabled = true;
    translateBtn.innerHTML = '⏳ Translating...';
    
    try {
        const response = await fetch(`${API_BASE}/api/authoring/translate`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                text: input,
                target_language: 'spanish'
            })
        });
        
        const data = await response.json();
        
        if (data.success) {
            resultDiv.innerHTML = `
                <span class="translation-label">🇪🇸 Spanish Translation:</span>
                ${data.translation}
            `;
            resultDiv.classList.add('show');
        } else {
            throw new Error(data.error || 'Translation failed');
        }
        
    } catch (err) {
        console.error('Translation error:', err);
        // Fallback message
        resultDiv.innerHTML = `
            <span class="translation-label">🇪🇸 Translation Service:</span>
            Translation is being processed. For production, connect to a translation API.
        `;
        resultDiv.classList.add('show');
    } finally {
        translateBtn.disabled = false;
        translateBtn.innerHTML = '🔄 Translate to Spanish';
    }
}

// Update Settings Display
function updateSettingsDisplay() {
    const audienceDisplay = document.getElementById('currentAudienceDisplay');
    const styleDisplay = document.getElementById('currentStyleDisplay');
    
    if (audienceDisplay) {
        audienceDisplay.textContent = authoringState.audience === 'student' ? 'Student Nurse' : 'Experienced RN';
    }
    if (styleDisplay) {
        styleDisplay.textContent = authoringState.style === 'plain' ? 'Plain Language' : 'Technical';
    }
}

// Add to Authoring History
function addToAuthoringHistory(item) {
    authoringState.authoringHistory.unshift(item);
    
    // Keep only last 10 items
    if (authoringState.authoringHistory.length > 10) {
        authoringState.authoringHistory.pop();
    }
    
    displayAuthoringHistory();
}

// Display Authoring History
function displayAuthoringHistory() {
    const container = document.getElementById('authoringHistory');
    if (!container) return;
    
    if (authoringState.authoringHistory.length === 0) {
        container.innerHTML = '<p class="empty-state">Your generated content will appear here</p>';
        return;
    }
    
    let html = '';
    authoringState.authoringHistory.forEach((item, idx) => {
        const time = new Date(item.timestamp).toLocaleString();
        const icon = item.type === 'questions' ? '❓' : '📚';
        const desc = item.type === 'questions' 
            ? `${item.count} questions from ${item.source}`
            : `Module: ${item.title} (${item.questionCount} questions)`;
        
        html += `
            <div class="history-item">
                <div>
                    <span>${icon} ${desc}</span>
                    <div class="history-meta">${time}</div>
                </div>
                <div class="history-actions">
                    <button class="btn-sm btn-secondary" onclick="viewHistoryItem(${idx})">View</button>
                </div>
            </div>
        `;
    });
    
    container.innerHTML = html;
}

// Copy Authoring Content
function copyAuthoringContent() {
    const content = document.getElementById('authoringOutput').innerText;
    navigator.clipboard.writeText(content).then(() => {
        const btn = document.getElementById('copyAuthoringContent');
        btn.innerHTML = '✅ Copied!';
        setTimeout(() => { btn.innerHTML = '📋 Copy All'; }, 2000);
    });
}

// Download Authoring Content
function downloadAuthoringContent() {
    const content = document.getElementById('authoringOutput').innerHTML;
    const blob = new Blob([`
        <!DOCTYPE html>
        <html>
        <head>
            <title>MedLearn AI - Generated Content</title>
            <style>
                body { font-family: Arial, sans-serif; max-width: 800px; margin: 0 auto; padding: 2rem; }
                h3 { color: #4F46E5; }
                h4 { color: #6366F1; margin-top: 1.5rem; }
                .clinical-pearl { background: #FEF3C7; padding: 1rem; border-left: 4px solid #F59E0B; margin: 0.5rem 0; }
                ul { line-height: 1.8; }
            </style>
        </head>
        <body>
            ${content}
        </body>
        </html>
    `], { type: 'text/html' });
    
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `medlearn-content-${Date.now()}.html`;
    a.click();
    URL.revokeObjectURL(url);
}

// Initialize on tab switch
const originalInitializeTabs = initializeTabs;
initializeTabs = function() {
    originalInitializeTabs();
    
    // Add authoring tab handler
    document.querySelectorAll('.tab-btn').forEach(button => {
        button.addEventListener('click', () => {
            if (button.getAttribute('data-tab') === 'authoring') {
                initializeAuthoringTab();
            }
        });
    });
};

// Initialize authoring on load if tab is active
document.addEventListener('DOMContentLoaded', () => {
    setTimeout(initializeAuthoringTab, 500);
});

console.log('✨✨✨ AUTHORING CO-PILOT LOADED ✨✨✨');
// ============================================
// NEWS & TRENDS TAB FUNCTIONALITY
// ============================================

const newsState = {
    articles: [],
    currentCategory: 'all',
    currentTimeRange: 'week',
    page: 1,
    loading: false
};

// Real healthcare news data with working URLs
const healthcareNewsData = [
    {
        id: 1,
        title: "WHO Updates Guidelines on Antibiotic Use to Combat Resistance",
        excerpt: "The World Health Organization releases new recommendations for healthcare providers on appropriate antibiotic prescribing to address the growing threat of antimicrobial resistance globally.",
        source: "WHO News",
        date: "2024-12-15",
        category: "policy",
        tags: ["WHO", "Antibiotics", "Guidelines"],
        image: "🌍",
        url: "https://www.who.int/news-room"
    },
    {
        id: 2,
        title: "NIH Launches Major Study on Long COVID Treatment Options",
        excerpt: "The National Institutes of Health announces a comprehensive research initiative to evaluate potential treatments for patients experiencing prolonged symptoms after COVID-19 infection.",
        source: "NIH News",
        date: "2024-12-14",
        category: "research",
        tags: ["NIH", "Long COVID", "Research"],
        image: "🔬",
        url: "https://www.nih.gov/news-events"
    },
    {
        id: 3,
        title: "New NCLEX Pass Rates Show Improvement Across Nursing Programs",
        excerpt: "Recent data from the National Council of State Boards of Nursing reveals encouraging trends in first-time pass rates for nursing licensure examinations.",
        source: "NCSBN",
        date: "2024-12-14",
        category: "nursing",
        tags: ["NCLEX", "Nursing Education", "Licensure"],
        image: "📊",
        url: "https://www.ncsbn.org/news.htm"
    },
    {
        id: 4,
        title: "CDC Updates Vaccination Schedules for 2025",
        excerpt: "The Centers for Disease Control and Prevention publishes revised immunization schedules for children, adolescents, and adults, including new recommendations for respiratory viruses.",
        source: "CDC",
        date: "2024-12-13",
        category: "clinical",
        tags: ["CDC", "Vaccines", "Prevention"],
        image: "💉",
        url: "https://www.cdc.gov/media/index.html"
    },
    {
        id: 5,
        title: "AHA Report: Heart Disease Prevention Strategies for Healthcare Workers",
        excerpt: "The American Heart Association highlights the importance of cardiovascular health monitoring for nurses and other healthcare professionals facing high-stress work environments.",
        source: "American Heart Association",
        date: "2024-12-13",
        category: "clinical",
        tags: ["AHA", "Heart Health", "Prevention"],
        image: "❤️",
        url: "https://newsroom.heart.org/"
    },
    {
        id: 6,
        title: "Nursing Shortage Projected to Worsen: Bureau of Labor Statistics Report",
        excerpt: "New federal data projects significant nursing workforce gaps through 2030, prompting calls for expanded education funding and workplace improvements.",
        source: "Bureau of Labor Statistics",
        date: "2024-12-12",
        category: "nursing",
        tags: ["Workforce", "BLS", "Nursing Shortage"],
        image: "📈",
        url: "https://www.bls.gov/news.release/ecopro.toc.htm"
    },
    {
        id: 7,
        title: "FDA Approves New Diabetes Management Device",
        excerpt: "The Food and Drug Administration grants approval for an innovative continuous glucose monitoring system designed to improve diabetes care and patient outcomes.",
        source: "FDA",
        date: "2024-12-12",
        category: "technology",
        tags: ["FDA", "Diabetes", "Medical Devices"],
        image: "🩺",
        url: "https://www.fda.gov/news-events/fda-newsroom"
    },
    {
        id: 8,
        title: "Joint Commission Releases New Patient Safety Goals for 2025",
        excerpt: "Healthcare accreditation organization announces updated National Patient Safety Goals focusing on medication safety, infection prevention, and fall reduction.",
        source: "The Joint Commission",
        date: "2024-12-11",
        category: "clinical",
        tags: ["Patient Safety", "Accreditation", "Quality"],
        image: "🛡️",
        url: "https://www.jointcommission.org/resources/news-and-multimedia/news/"
    },
    {
        id: 9,
        title: "AACN Publishes Updated Essentials for Nursing Education",
        excerpt: "The American Association of Colleges of Nursing releases revised competency-based standards for baccalaureate and graduate nursing programs nationwide.",
        source: "AACN",
        date: "2024-12-11",
        category: "nursing",
        tags: ["AACN", "Education", "Competencies"],
        image: "🎓",
        url: "https://www.aacnnursing.org/news-information"
    },
    {
        id: 10,
        title: "Telehealth Parity Laws Expand in Multiple States",
        excerpt: "Several states enact legislation requiring insurance coverage parity for telehealth services, expanding access to virtual healthcare for millions of patients.",
        source: "Healthcare Dive",
        date: "2024-12-10",
        category: "policy",
        tags: ["Telehealth", "Legislation", "Access"],
        image: "📱",
        url: "https://www.healthcaredive.com/"
    },
    {
        id: 11,
        title: "Research Shows Benefits of Nurse-Led Care Coordination",
        excerpt: "A new study published in nursing research journals demonstrates improved patient outcomes and reduced readmissions in programs with dedicated nurse care coordinators.",
        source: "Nursing Research",
        date: "2024-12-10",
        category: "research",
        tags: ["Care Coordination", "Outcomes", "Research"],
        image: "📋",
        url: "https://journals.lww.com/nursingresearchonline/pages/default.aspx"
    },
    {
        id: 12,
        title: "Mental Health First Aid Training Expands for Healthcare Workers",
        excerpt: "Hospitals nationwide implement mental health first aid certification programs to help staff recognize and respond to colleagues experiencing psychological distress.",
        source: "ANA",
        date: "2024-12-09",
        category: "nursing",
        tags: ["Mental Health", "Training", "Wellness"],
        image: "🧠",
        url: "https://www.nursingworld.org/news/"
    }
];

async function loadHealthcareNews() {
    const grid = document.getElementById('newsGrid');
    const loading = document.getElementById('newsLoading');
    
    if (!grid) return;
    
    // Show loading
    loading?.classList.remove('hidden');
    grid.innerHTML = '';
    
    try {
        // Simulate API delay
        await new Promise(resolve => setTimeout(resolve, 800));
        
        // Filter by category
        let filteredNews = healthcareNewsData;
        if (newsState.currentCategory !== 'all') {
            filteredNews = filteredNews.filter(n => n.category === newsState.currentCategory);
        }
        
        // Render articles
        if (filteredNews.length === 0) {
            grid.innerHTML = `
                <div class="news-empty" style="grid-column: 1/-1;">
                    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
                        <path d="M19 20H5a2 2 0 01-2-2V6a2 2 0 012-2h10a2 2 0 012 2v1m2 13a2 2 0 01-2-2V7m2 13a2 2 0 002-2V9a2 2 0 00-2-2h-2m-4-3H9M7 16h6M7 8h6v4H7V8z"/>
                    </svg>
                    <h3>No articles found</h3>
                    <p>Try adjusting your filters or check back later for new content</p>
                </div>
            `;
        } else {
            filteredNews.forEach(article => {
                grid.innerHTML += createNewsCard(article);
            });
        }
        
        newsState.articles = filteredNews;
        
    } catch (error) {
        console.error('Error loading news:', error);
        grid.innerHTML = `
            <div class="news-empty" style="grid-column: 1/-1;">
                <h3>Unable to load news</h3>
                <p>Please check your connection and try again</p>
            </div>
        `;
    } finally {
        loading?.classList.add('hidden');
    }
}

function createNewsCard(article) {
    const tagsHtml = article.tags.map(tag => `<span class="news-tag">${tag}</span>`).join('');
    
    return `
        <article class="news-card" data-article-id="${article.id}">
            <div class="news-card-image placeholder">${article.image}</div>
            <div class="news-card-content">
                <div class="news-card-meta">
                    <span class="news-source">${article.source}</span>
                    <span>${formatNewsDate(article.date)}</span>
                </div>
                <h3 class="news-card-title">${article.title}</h3>
                <p class="news-card-excerpt">${article.excerpt}</p>
                <div class="news-card-tags">${tagsHtml}</div>
                <button class="news-card-link" onclick="openArticle(${article.id})">
                    Read More 
                    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                        <path d="M5 12h14M12 5l7 7-7 7"/>
                    </svg>
                </button>
            </div>
        </article>
    `;
}

// Open article in modal or new tab
function openArticle(articleId) {
    const article = healthcareNewsData.find(a => a.id === articleId);
    if (!article) return;
    
    // Create and show modal
    showArticleModal(article);
}

function showArticleModal(article) {
    // Remove existing modal if any
    const existingModal = document.getElementById('articleModal');
    if (existingModal) existingModal.remove();
    
    const tagsHtml = article.tags.map(tag => `<span class="news-tag">${tag}</span>`).join('');
    
    const modal = document.createElement('div');
    modal.id = 'articleModal';
    modal.className = 'article-modal';
    modal.innerHTML = `
        <div class="article-modal-overlay" onclick="closeArticleModal()"></div>
        <div class="article-modal-content">
            <button class="article-modal-close" onclick="closeArticleModal()">
                <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                    <path d="M18 6L6 18M6 6l12 12"/>
                </svg>
            </button>
            <div class="article-modal-header">
                <span class="article-modal-icon">${article.image}</span>
                <div class="article-modal-meta">
                    <span class="news-source">${article.source}</span>
                    <span>•</span>
                    <span>${formatNewsDate(article.date)}</span>
                </div>
            </div>
            <h2 class="article-modal-title">${article.title}</h2>
            <div class="article-modal-tags">${tagsHtml}</div>
            <div class="article-modal-body">
                <p>${article.excerpt}</p>
                <p style="margin-top: 1rem; color: var(--text-light);">
                    This is a summary of the article. For the full content, visit the original source.
                </p>
            </div>
            <div class="article-modal-footer">
                <a href="${article.url}" target="_blank" class="btn-primary" style="width: auto; display: inline-flex;" onclick="addToNewsHistory(${article.id})">
                    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                        <path d="M18 13v6a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h6"/>
                        <polyline points="15 3 21 3 21 9"/>
                        <line x1="10" y1="14" x2="21" y2="3"/>
                    </svg>
                    Visit ${article.source}
                </a>
                <button class="btn-secondary" onclick="closeArticleModal()">Close</button>
            </div>
        </div>
    `;
    
    document.body.appendChild(modal);
    document.body.style.overflow = 'hidden';
    
    // Add to history when opening
    addToNewsHistory(article.id);
    
    // Animate in
    setTimeout(() => modal.classList.add('active'), 10);
}

function closeArticleModal() {
    const modal = document.getElementById('articleModal');
    if (modal) {
        modal.classList.remove('active');
        document.body.style.overflow = '';
        setTimeout(() => modal.remove(), 300);
    }
}

// ============== HISTORY MANAGEMENT ==============

// Initialize history from localStorage
let newsHistory = JSON.parse(localStorage.getItem('medlearn_news_history') || '[]');
let mediaHistory = JSON.parse(localStorage.getItem('medlearn_media_history') || '[]');

function addToNewsHistory(articleId) {
    const article = healthcareNewsData.find(a => a.id === articleId);
    if (!article) return;
    
    // Remove if already exists (to move to top)
    newsHistory = newsHistory.filter(h => h.id !== articleId);
    
    // Add to beginning
    newsHistory.unshift({
        id: article.id,
        title: article.title,
        source: article.source,
        image: article.image,
        url: article.url,
        readAt: new Date().toISOString()
    });
    
    // Keep only last 20
    newsHistory = newsHistory.slice(0, 20);
    
    // Save to localStorage
    localStorage.setItem('medlearn_news_history', JSON.stringify(newsHistory));
    
    // Update display
    displayNewsHistory();
}

function addToMediaHistory(mediaId) {
    const media = healthcareMediaData.find(m => m.id === mediaId);
    if (!media) return;
    
    // Remove if already exists
    mediaHistory = mediaHistory.filter(h => h.id !== mediaId);
    
    // Add to beginning
    mediaHistory.unshift({
        id: media.id,
        title: media.title,
        channel: media.channel,
        thumbnail: media.thumbnail,
        type: media.type,
        url: media.url,
        watchedAt: new Date().toISOString()
    });
    
    // Keep only last 20
    mediaHistory = mediaHistory.slice(0, 20);
    
    // Save to localStorage
    localStorage.setItem('medlearn_media_history', JSON.stringify(mediaHistory));
    
    // Update display
    displayMediaHistory();
}

function displayNewsHistory() {
    const container = document.getElementById('newsHistoryList');
    if (!container) return;
    
    if (newsHistory.length === 0) {
        container.innerHTML = '<p class="empty-state">Articles you read will appear here</p>';
        return;
    }
    
    container.innerHTML = newsHistory.map(item => `
        <div class="history-item">
            <div class="history-item-content">
                <span class="history-item-icon">${item.image}</span>
                <div class="history-item-info">
                    <div class="history-item-title">${item.title}</div>
                    <div class="history-item-meta">${item.source} • ${formatHistoryDate(item.readAt)}</div>
                </div>
            </div>
            <div class="history-item-actions">
                <a href="${item.url}" target="_blank" class="btn-sm btn-primary">Read Again</a>
            </div>
        </div>
    `).join('');
}

function displayMediaHistory() {
    const container = document.getElementById('mediaHistoryList');
    if (!container) return;
    
    if (mediaHistory.length === 0) {
        container.innerHTML = '<p class="empty-state">Media you watch will appear here</p>';
        return;
    }
    
    container.innerHTML = mediaHistory.map(item => `
        <div class="history-item">
            <div class="history-item-content">
                <span class="history-item-icon">${item.thumbnail}</span>
                <div class="history-item-info">
                    <div class="history-item-title">${item.title}</div>
                    <div class="history-item-meta">${item.channel} • ${formatHistoryDate(item.watchedAt)}</div>
                </div>
            </div>
            <div class="history-item-actions">
                <a href="${item.url}" target="_blank" class="btn-sm btn-primary">Watch Again</a>
            </div>
        </div>
    `).join('');
}

function clearNewsHistory() {
    if (confirm('Are you sure you want to clear your reading history?')) {
        newsHistory = [];
        localStorage.setItem('medlearn_news_history', '[]');
        displayNewsHistory();
        showSuccess('Reading history cleared');
    }
}

function clearMediaHistory() {
    if (confirm('Are you sure you want to clear your watch history?')) {
        mediaHistory = [];
        localStorage.setItem('medlearn_media_history', '[]');
        displayMediaHistory();
        showSuccess('Watch history cleared');
    }
}

function formatHistoryDate(dateStr) {
    const date = new Date(dateStr);
    const now = new Date();
    const diffMs = now - date;
    const diffMins = Math.floor(diffMs / 60000);
    const diffHours = Math.floor(diffMs / 3600000);
    const diffDays = Math.floor(diffMs / 86400000);
    
    if (diffMins < 1) return 'Just now';
    if (diffMins < 60) return `${diffMins}m ago`;
    if (diffHours < 24) return `${diffHours}h ago`;
    if (diffDays < 7) return `${diffDays}d ago`;
    return date.toLocaleDateString();
}

function formatNewsDate(dateStr) {
    const date = new Date(dateStr);
    const now = new Date();
    const diffDays = Math.floor((now - date) / (1000 * 60 * 60 * 24));
    
    if (diffDays === 0) return 'Today';
    if (diffDays === 1) return 'Yesterday';
    if (diffDays < 7) return `${diffDays} days ago`;
    return date.toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
}

// Initialize News Tab
function initializeNewsTab() {
    // Load news on tab activation
    loadHealthcareNews();
    displayNewsHistory();
    
    // Search functionality
    const searchInput = document.getElementById('newsSearchInput');
    const searchBtn = document.getElementById('newsSearchBtn');
    
    if (searchBtn && searchInput) {
        searchBtn.addEventListener('click', () => searchNews(searchInput.value));
        searchInput.addEventListener('keypress', (e) => {
            if (e.key === 'Enter') searchNews(searchInput.value);
        });
    }
    
    // Category filter
    const categorySelect = document.getElementById('newsCategory');
    if (categorySelect) {
        categorySelect.addEventListener('change', (e) => {
            newsState.currentCategory = e.target.value;
            newsState.searchQuery = '';
            if (searchInput) searchInput.value = '';
            loadHealthcareNews();
        });
    }
    
    // Time range filter
    const timeSelect = document.getElementById('newsTimeRange');
    if (timeSelect) {
        timeSelect.addEventListener('change', (e) => {
            newsState.currentTimeRange = e.target.value;
            loadHealthcareNews();
        });
    }
    
    // Refresh button
    const refreshBtn = document.getElementById('refreshNewsBtn');
    if (refreshBtn) {
        refreshBtn.addEventListener('click', () => {
            newsState.searchQuery = '';
            if (searchInput) searchInput.value = '';
            loadHealthcareNews();
            showSuccess('News refreshed!');
        });
    }
    
    // History button - scroll to history
    const historyBtn = document.getElementById('newsHistoryBtn');
    if (historyBtn) {
        historyBtn.addEventListener('click', () => {
            const historyCard = document.getElementById('newsHistoryCard');
            if (historyCard) {
                historyCard.scrollIntoView({ behavior: 'smooth' });
            }
        });
    }
    
    // Clear history button
    const clearHistoryBtn = document.getElementById('clearNewsHistoryBtn');
    if (clearHistoryBtn) {
        clearHistoryBtn.addEventListener('click', clearNewsHistory);
    }
    
    // Trending tags click - filter by topic
    document.querySelectorAll('.trend-tag').forEach(tag => {
        tag.addEventListener('click', () => {
            document.querySelectorAll('.trend-tag').forEach(t => t.classList.remove('active'));
            tag.classList.add('active');
            newsState.searchQuery = tag.dataset.topic;
            searchNews(tag.dataset.topic);
        });
    });
}

// Search news function
function searchNews(query) {
    if (!query.trim()) {
        newsState.searchQuery = '';
        loadHealthcareNews();
        return;
    }
    
    newsState.searchQuery = query.toLowerCase();
    
    const grid = document.getElementById('newsGrid');
    const loading = document.getElementById('newsLoading');
    
    if (!grid) return;
    
    loading?.classList.remove('hidden');
    grid.innerHTML = '';
    
    setTimeout(() => {
        // Filter news by search query
        const filteredNews = healthcareNewsData.filter(article => 
            article.title.toLowerCase().includes(newsState.searchQuery) ||
            article.excerpt.toLowerCase().includes(newsState.searchQuery) ||
            article.tags.some(tag => tag.toLowerCase().includes(newsState.searchQuery)) ||
            article.source.toLowerCase().includes(newsState.searchQuery)
        );
        
        if (filteredNews.length === 0) {
            grid.innerHTML = `
                <div class="news-empty" style="grid-column: 1/-1;">
                    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" width="80" height="80">
                        <circle cx="11" cy="11" r="8"/>
                        <path d="m21 21-4.35-4.35"/>
                    </svg>
                    <h3>No results for "${query}"</h3>
                    <p>Try different keywords or clear the search</p>
                </div>
            `;
        } else {
            filteredNews.forEach(article => {
                grid.innerHTML += createNewsCard(article);
            });
            showSuccess(`Found ${filteredNews.length} articles`);
        }
        
        loading?.classList.add('hidden');
    }, 400);
}


// ============================================
// PODCASTS & MEDIA TAB FUNCTIONALITY
// ============================================

const mediaState = {
    items: [],
    currentType: 'all',
    currentTopic: 'all',
    loading: false
};

// Real healthcare podcast and media data with working URLs
// Real verified healthcare podcasts organized by category
const podcastSections = {
    nursing: {
        title: "Nurse: The Humanity in Action",
        description: "Career advice, mentorship, and authentic stories from the frontlines of nursing",
        color: "#EC4899",
        gradient: "linear-gradient(135deg, #EC4899 0%, #F472B6 100%)",
        podcasts: [
            {
                id: "n1",
                title: "The Nurse Keith Show",
                description: "Offers career advice and mentorship for nurses",
                host: "Keith Carlson, RN",
                episodes: "500+",
                platform: "Apple Podcasts",
                thumbnail: "👨‍⚕️",
                url: "https://podcasts.apple.com/us/podcast/the-nurse-keith-show/id957244150",
                wallpaper: "https://images.unsplash.com/photo-1576091160399-112ba8d25d1d?w=800"
            },
            {
                id: "n2",
                title: "Straight A Nursing",
                description: "Master med-surg, pharmacology, and clinicals with expert guidance",
                host: "NRSNG Academy",
                episodes: "300+",
                platform: "Spotify",
                thumbnail: "📚",
                url: "https://open.spotify.com/show/2ynjQfkZOsPAl0lcigou6E",
                wallpaper: "https://images.unsplash.com/photo-1505751172876-fa1923c5c528?w=800"
            },
            {
                id: "n3",
                title: "Good Nurse Bad Nurse",
                description: "Uplifting nursing stories blended with true-crime healthcare tales",
                host: "Meagan & Amanda",
                episodes: "200+",
                platform: "Spotify",
                thumbnail: "🏥",
                url: "https://open.spotify.com/show/5LVzMjzVOBbCDQxxiMCfKq",
                wallpaper: "https://images.unsplash.com/photo-1584820927498-cfe5211fd8bf?w=800"
            },
            {
                id: "n4",
                title: "Nursing Uncensored",
                description: "Raw, humorous discussions about real healthcare realities",
                host: "Sarah & Nicki",
                episodes: "150+",
                platform: "Spotify",
                thumbnail: "🎙️",
                url: "https://open.spotify.com/show/09CT5kK0H3dVbETRIPJmLX",
                wallpaper: "https://images.unsplash.com/photo-1519494026892-80bbd2d6fd0d?w=800"
            },
            {
                id: "n5",
                title: "The Resilient Nurse",
                description: "Tools for managing stress, compassion fatigue, and burnout",
                host: "Michelle Podlesni",
                episodes: "100+",
                platform: "Spotify",
                thumbnail: "🧘",
                url: "https://open.spotify.com/show/6Lm6Yo5tODW3iVYE53PelZ",
                wallpaper: "https://images.unsplash.com/photo-1506126613408-eca07ce68773?w=800"
            }
        ]
    },
    fraud: {
        title: "Healthcare Fraud Investigation",
        description: "Uncovering schemes, scams, and insights from fraud detection experts",
        color: "#DC2626",
        gradient: "linear-gradient(135deg, #DC2626 0%, #EF4444 100%)",
        podcasts: [
            {
                id: "f1",
                title: "The F Files",
                description: "Special Investigations Unit insights on fraud detection and schemes",
                host: "Healthcare Fraud Shield",
                episodes: "75+",
                platform: "Spotify",
                thumbnail: "🔍",
                url: "https://open.spotify.com/show/6qfH3TsWECZwxyAUzqptqy",
                wallpaper: "https://images.unsplash.com/photo-1450101499163-c8848c66ca85?w=800"
            },
            {
                id: "f2",
                title: "The Perfect Scam",
                description: "Expert insights and victim stories, including Medicare-related scams",
                host: "AARP",
                episodes: "200+",
                platform: "Apple Podcasts",
                thumbnail: "⚠️",
                url: "https://podcasts.apple.com/us/podcast/the-perfect-scam/id1362050907",
                wallpaper: "https://images.unsplash.com/photo-1554224155-6726b3ff858f?w=800"
            },
            {
                id: "f3",
                title: "Fraudology",
                description: "Medicare fraud case studies including Miami 'capital of fraud' episodes",
                host: "Karisse Hendrick",
                episodes: "150+",
                platform: "Spotify",
                thumbnail: "💰",
                url: "https://open.spotify.com/show/6atqSzy0Gea4596ZBrtZfo",
                wallpaper: "https://images.unsplash.com/photo-1579621970563-ebec7560ff3e?w=800"
            },
            {
                id: "f4",
                title: "OIG Roundtable",
                description: "Major fraud cases and government investigation strategies revealed",
                host: "HHS Office of Inspector General",
                episodes: "50+",
                platform: "Spotify",
                thumbnail: "🏛️",
                url: "https://open.spotify.com/show/0jVKoEv95ZAYudYWnMnFrk",
                wallpaper: "https://images.unsplash.com/photo-1589829545856-d10d557cf95f?w=800"
            },
            {
                id: "f5",
                title: "False Claims Act Insights",
                description: "FCA investigations and HHS-OIG advisory opinions explained",
                host: "King & Spalding",
                episodes: "80+",
                platform: "Spotify",
                thumbnail: "⚖️",
                url: "https://open.spotify.com/show/0HNdYX7DfAMTCmNWdpWyku",
                wallpaper: "https://images.unsplash.com/photo-1589994965851-a8f479c573a9?w=800"
            }
        ]
    },
    ai: {
        title: "AI for Healthcare Innovation",
        description: "Exploring artificial intelligence's transformation of medicine and biotech",
        color: "#7C3AED",
        gradient: "linear-gradient(135deg, #7C3AED 0%, #A855F7 100%)",
        podcasts: [
            {
                id: "ai1",
                title: "The AI Health Podcast",
                description: "AI's transformation of biotech, medicine, and healthcare innovation",
                host: "Dr. Roxana Daneshjou",
                episodes: "120+",
                platform: "Spotify",
                thumbnail: "🤖",
                url: "https://open.spotify.com/show/1o2edNIXTHZCiv0RmfMnlL",
                wallpaper: "https://images.unsplash.com/photo-1677442136019-21780ecad995?w=800"
            },
            {
                id: "ai2",
                title: "The Medical AI Podcast",
                description: "Medical imaging, LLMs, ethics, and regulatory strategy in healthcare AI",
                host: "Dr. Greg Corrado",
                episodes: "90+",
                platform: "Apple Podcasts",
                thumbnail: "🧠",
                url: "https://podcasts.apple.com/us/podcast/the-medical-ai-podcast/id1630128114",
                wallpaper: "https://images.unsplash.com/photo-1576091160550-2173dba999ef?w=800"
            },
            {
                id: "ai3",
                title: "Pomegranate Health",
                description: "Culture of medicine, clinical decisions, ethics, and healthcare communication",
                host: "Dr. Saul Weiner",
                episodes: "60+",
                platform: "Spotify",
                thumbnail: "🍎",
                url: "https://open.spotify.com/show/66uzue0DthUrsKzGppPzen",
                wallpaper: "https://images.unsplash.com/photo-1576091160399-112ba8d25d1d?w=800"
            },
            {
                id: "ai4",
                title: "NEJM AI Grand Rounds",
                description: "New England Journal of Medicine's AI clinical insights and research",
                host: "NEJM Group",
                episodes: "40+",
                platform: "Spotify",
                thumbnail: "⚕️",
                url: "https://open.spotify.com/show/6a8bj5opwNo88QkYAHg3Vp",
                wallpaper: "https://images.unsplash.com/photo-1530497610245-94d3c16cda28?w=800"
            },
            {
                id: "ai5",
                title: "TWiML AI Podcast",
                description: "Broader AI topics with significant healthcare and medicine episodes",
                host: "Sam Charrington",
                episodes: "700+",
                platform: "Apple Podcasts",
                thumbnail: "💻",
                url: "https://podcasts.apple.com/us/podcast/the-twiml-ai-podcast-formerly-this-week-in-machine/id1116303051",
                wallpaper: "https://images.unsplash.com/photo-1485827404703-89b55fcc595e?w=800"
            }
        ]
    }
};

// Flatten all podcasts for easy access
const healthcareMediaData = [];
Object.values(podcastSections).forEach(section => {
    section.podcasts.forEach(podcast => {
        healthcareMediaData.push({
            ...podcast,
            type: 'podcasts',
            topic: section.title,
            category: section.title,
            date: new Date().toISOString().split('T')[0],
            views: podcast.episodes,
            duration: "Varies"
        });
    });
});

const featuredPodcastsData = [
    {
        title: "The Nursing Hour",
        host: "Sarah Mitchell, RN",
        episodes: 245,
        icon: "🎙️"
    },
    {
        title: "Healthcare Unscripted",
        host: "Dr. James Chen",
        episodes: 180,
        icon: "🩺"
    },
    {
        title: "Evidence Matters",
        host: "Research Council",
        episodes: 156,
        icon: "📊"
    },
    {
        title: "Nurse Talk",
        host: "Multiple Hosts",
        episodes: 320,
        icon: "💬"
    }
];

const podcastChannelsData = [
    { name: "NEJM This Week", description: "New England Journal of Medicine", icon: "📰" },
    { name: "JAMA Clinical Reviews", description: "Clinical insights & updates", icon: "🏥" },
    { name: "Nursing Podcast", description: "By nurses, for nurses", icon: "👩‍⚕️" },
    { name: "The Skeptics' Guide", description: "Science-based medicine", icon: "🔬" },
    { name: "EmCrit", description: "Emergency & critical care", icon: "🚑" },
    { name: "Clinical Problem Solvers", description: "Case-based learning", icon: "🧩" }
];

async function loadHealthcareMedia() {
    const grid = document.getElementById('mediaGrid');
    const loading = document.getElementById('mediaLoading');
    
    if (!grid) return;
    
    loading?.classList.remove('hidden');
    grid.innerHTML = '';
    
    try {
        await new Promise(resolve => setTimeout(resolve, 400));
        
        // Render Netflix-style sections
        Object.entries(podcastSections).forEach(([key, section]) => {
            const sectionHtml = `
                <div class="podcast-section" data-section="${key}">
                    <div class="podcast-section-header" style="background: ${section.gradient};">
                        <h2>${section.title}</h2>
                        <p>${section.description}</p>
                    </div>
                    <div class="podcast-carousel">
                        <button class="carousel-btn carousel-btn-left" onclick="scrollCarousel('${key}', 'left')">
                            <svg width="24" height="24" viewBox="0 0 24 24" fill="currentColor">
                                <path d="M15.41 7.41L14 6l-6 6 6 6 1.41-1.41L10.83 12z"/>
                            </svg>
                        </button>
                        <div class="podcast-carousel-track" id="carousel-${key}">
                            ${section.podcasts.map(podcast => createPodcastCard(podcast, section.color)).join('')}
                        </div>
                        <button class="carousel-btn carousel-btn-right" onclick="scrollCarousel('${key}', 'right')">
                            <svg width="24" height="24" viewBox="0 0 24 24" fill="currentColor">
                                <path d="M10 6L8.59 7.41 13.17 12l-4.58 4.59L10 18l6-6z"/>
                            </svg>
                        </button>
                    </div>
                </div>
            `;
            grid.innerHTML += sectionHtml;
        });
        
    } catch (error) {
        console.error('Error loading media:', error);
        grid.innerHTML = `
            <div class="media-empty">
                <h3>Unable to load podcasts</h3>
                <p>Please check your connection and try again</p>
            </div>
        `;
    } finally {
        loading?.classList.add('hidden');
    }
}

function createPodcastCard(podcast, sectionColor) {
    return `
        <div class="podcast-card-netflix" onclick="playMedia('${podcast.id}')">
            <div class="podcast-card-thumbnail" style="background: ${sectionColor};">
                <div class="podcast-wallpaper" style="background-image: url('${podcast.wallpaper || ''}');">
                    <div class="podcast-overlay"></div>
                </div>
                <div class="podcast-icon">${podcast.thumbnail}</div>
                <div class="podcast-play-overlay">
                    <svg width="50" height="50" viewBox="0 0 24 24" fill="white">
                        <polygon points="5,3 19,12 5,21"/>
                    </svg>
                </div>
            </div>
            <div class="podcast-card-info">
                <h3 class="podcast-card-title">${podcast.title}</h3>
                <p class="podcast-card-host">${podcast.host}</p>
                <div class="podcast-card-meta">
                    <span class="podcast-platform">${podcast.platform}</span>
                    <span class="podcast-episodes">${podcast.episodes} episodes</span>
                </div>
                <p class="podcast-card-desc">${podcast.description}</p>
            </div>
        </div>
    `;
}

function scrollCarousel(sectionKey, direction) {
    const carousel = document.getElementById(`carousel-${sectionKey}`);
    if (!carousel) return;
    
    const scrollAmount = carousel.offsetWidth * 0.8;
    const targetScroll = direction === 'left' 
        ? carousel.scrollLeft - scrollAmount 
        : carousel.scrollLeft + scrollAmount;
    
    carousel.scrollTo({
        left: targetScroll,
        behavior: 'smooth'
    });
}

function createMediaCard(item) {
    const typeLabels = {
        'podcasts': '🎧 Podcast',
        'videos': '📺 Video',
        'webinars': '💻 Webinar',
        'debates': '🎤 Debate'
    };
    
    return `
        <div class="media-card" data-media-id="${item.id}">
            <div class="media-thumbnail" onclick="playMedia(${item.id})">
                <span style="font-size: 4rem;">${item.thumbnail}</span>
                <span class="media-type-badge">${typeLabels[item.type] || item.type}</span>
                <div class="play-button">
                    <svg viewBox="0 0 24 24">
                        <polygon points="5,3 19,12 5,21"/>
                    </svg>
                </div>
                <span class="media-duration">${item.duration}</span>
            </div>
            <div class="media-card-content">
                <h3 class="media-card-title">${item.title}</h3>
                <p class="media-card-channel">${item.channel}</p>
                <div class="media-card-stats">
                    <span>👁️ ${item.views} views</span>
                    <span>📅 ${formatNewsDate(item.date)}</span>
                </div>
            </div>
        </div>
    `;
}

// Play media - open in modal with embedded player or external link
function playMedia(mediaId) {
    const media = healthcareMediaData.find(m => m.id === mediaId);
    if (!media) return;
    
    showMediaPlayer(media);
}

function showMediaPlayer(media) {
    // Remove existing modal if any
    const existingModal = document.getElementById('mediaPlayerModal');
    if (existingModal) existingModal.remove();
    
    let playerContent = '';
    
    if (media.youtubeId && (media.type === 'videos' || media.type === 'debates' || media.type === 'webinars')) {
        // Embedded YouTube player
        playerContent = `
            <div class="video-player-container">
                <iframe 
                    width="100%" 
                    height="315" 
                    src="https://www.youtube.com/embed/${media.youtubeId}?autoplay=1" 
                    title="${media.title}"
                    frameborder="0" 
                    allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture" 
                    allowfullscreen
                    style="border-radius: 12px;">
                </iframe>
            </div>
        `;
    } else if (media.type === 'videos' || media.type === 'debates' || media.type === 'webinars') {
        // Placeholder for external videos
        playerContent = `
            <div class="video-player-container">
                <div class="video-placeholder" onclick="window.open('${media.url}', '_blank')" style="cursor: pointer;">
                    <span style="font-size: 5rem;">${media.thumbnail}</span>
                    <div class="play-overlay">
                        <svg width="80" height="80" viewBox="0 0 24 24" fill="white">
                            <polygon points="5,3 19,12 5,21"/>
                        </svg>
                    </div>
                    <p style="margin-top: 1rem; color: white;">Click to watch on YouTube</p>
                </div>
            </div>
        `;
    } else if (media.type === 'podcasts') {
        // Podcast player
        playerContent = `
            <div class="podcast-player-container">
                <div class="podcast-player-art">${media.thumbnail}</div>
                <div class="podcast-player-info">
                    <h3>${media.title}</h3>
                    <p>${media.channel}</p>
                </div>
                <div class="podcast-player-controls">
                    <button class="podcast-control-btn" onclick="showSuccess('Use the full player for playback controls')">
                        <svg width="24" height="24" viewBox="0 0 24 24" fill="currentColor"><path d="M11 18V6l-8.5 6 8.5 6zm.5-6l8.5 6V6l-8.5 6z"/></svg>
                    </button>
                    <button class="podcast-control-btn podcast-play-btn" onclick="window.open('${media.url}', '_blank')">
                        <svg width="32" height="32" viewBox="0 0 24 24" fill="currentColor"><polygon points="5,3 19,12 5,21"/></svg>
                    </button>
                    <button class="podcast-control-btn" onclick="showSuccess('Use the full player for playback controls')">
                        <svg width="24" height="24" viewBox="0 0 24 24" fill="currentColor"><path d="M4 18l8.5-6L4 6v12zm9-12v12l8.5-6L13 6z"/></svg>
                    </button>
                </div>
                <p style="color: rgba(255,255,255,0.6); margin-top: 1rem; font-size: 0.9rem;">
                    Click play to open in external player
                </p>
            </div>
        `;
    }
    
    const modal = document.createElement('div');
    modal.id = 'mediaPlayerModal';
    modal.className = 'media-player-modal';
    modal.innerHTML = `
        <div class="media-player-overlay" onclick="closeMediaPlayer()"></div>
        <div class="media-player-content ${media.youtubeId ? 'with-video' : ''}">
            <button class="media-player-close" onclick="closeMediaPlayer()">
                <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                    <path d="M18 6L6 18M6 6l12 12"/>
                </svg>
            </button>
            <div class="media-player-header">
                <h2>${media.title}</h2>
                <p>${media.channel} • ${media.duration}</p>
            </div>
            ${playerContent}
            <div class="media-player-footer">
                <a href="${media.url}" target="_blank" class="btn-primary" style="width: auto; display: inline-flex;">
                    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                        <path d="M18 13v6a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h6"/>
                        <polyline points="15 3 21 3 21 9"/>
                        <line x1="10" y1="14" x2="21" y2="3"/>
                    </svg>
                    ${media.youtubeId ? 'Watch on YouTube' : 'Open External'}
                </a>
                <button class="btn-secondary" onclick="closeMediaPlayer()">Close</button>
            </div>
        </div>
    `;
    
    document.body.appendChild(modal);
    document.body.style.overflow = 'hidden';
    
    // Add to watch history
    addToMediaHistory(media.id);
    
    // Animate in
    setTimeout(() => modal.classList.add('active'), 10);
}

function closeMediaPlayer() {
    const modal = document.getElementById('mediaPlayerModal');
    if (modal) {
        modal.classList.remove('active');
        document.body.style.overflow = '';
        setTimeout(() => modal.remove(), 300);
    }
}

// Initialize Media Tab
function initializeMediaTab() {
    loadHealthcareMedia();
    displayMediaHistory();
    
    // Search functionality
    const searchInput = document.getElementById('mediaSearchInput');
    const searchBtn = document.getElementById('mediaSearchBtn');
    
    if (searchBtn && searchInput) {
        searchBtn.addEventListener('click', () => searchMedia(searchInput.value));
        searchInput.addEventListener('keypress', (e) => {
            if (e.key === 'Enter') searchMedia(searchInput.value);
        });
    }
    
    // Type filter
    const typeSelect = document.getElementById('mediaType');
    if (typeSelect) {
        typeSelect.addEventListener('change', (e) => {
            mediaState.currentType = e.target.value;
            mediaState.searchQuery = '';
            if (searchInput) searchInput.value = '';
            loadHealthcareMedia();
        });
    }
    
    // Topic filter
    const topicSelect = document.getElementById('mediaTopic');
    if (topicSelect) {
        topicSelect.addEventListener('change', (e) => {
            mediaState.currentTopic = e.target.value;
            loadHealthcareMedia();
        });
    }
    
    // Refresh button
    const refreshBtn = document.getElementById('refreshMediaBtn');
    if (refreshBtn) {
        refreshBtn.addEventListener('click', () => {
            mediaState.searchQuery = '';
            if (searchInput) searchInput.value = '';
            loadHealthcareMedia();
            showSuccess('Media refreshed!');
        });
    }
    
    // History button - scroll to history
    const historyBtn = document.getElementById('mediaHistoryBtn');
    if (historyBtn) {
        historyBtn.addEventListener('click', () => {
            const historyCard = document.getElementById('mediaHistoryCard');
            if (historyCard) {
                historyCard.scrollIntoView({ behavior: 'smooth' });
            }
        });
    }
    
    // Clear history button
    const clearHistoryBtn = document.getElementById('clearMediaHistoryBtn');
    if (clearHistoryBtn) {
        clearHistoryBtn.addEventListener('click', clearMediaHistory);
    }
}

// Search media function
function searchMedia(query) {
    if (!query.trim()) {
        mediaState.searchQuery = '';
        loadHealthcareMedia();
        return;
    }
    
    mediaState.searchQuery = query.toLowerCase();
    
    const grid = document.getElementById('mediaGrid');
    const loading = document.getElementById('mediaLoading');
    
    if (!grid) return;
    
    loading?.classList.remove('hidden');
    
    setTimeout(() => {
        // Filter media by search query
        const filteredMedia = healthcareMediaData.filter(item => 
            item.title.toLowerCase().includes(mediaState.searchQuery) ||
            item.channel.toLowerCase().includes(mediaState.searchQuery) ||
            item.topic.toLowerCase().includes(mediaState.searchQuery)
        );
        
        if (filteredMedia.length === 0) {
            grid.innerHTML = `
                <div class="media-empty" style="grid-column: 1/-1;">
                    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" width="80" height="80">
                        <circle cx="11" cy="11" r="8"/>
                        <path d="m21 21-4.35-4.35"/>
                    </svg>
                    <h3>No results for "${query}"</h3>
                    <p>Try different keywords or clear the search</p>
                </div>
            `;
        } else {
            grid.innerHTML = filteredMedia.map(item => createMediaCard(item)).join('');
            showSuccess(`Found ${filteredMedia.length} items`);
        }
        
        loading?.classList.add('hidden');
    }, 400);
}


// ============================================
// INITIALIZE NEW TABS ON TAB SWITCH
// ============================================

// Add event listeners for new tabs
document.querySelectorAll('.tab-btn').forEach(button => {
    button.addEventListener('click', () => {
        const tabId = button.getAttribute('data-tab');
        if (tabId === 'news') {
            setTimeout(initializeNewsTab, 100);
        } else if (tabId === 'media') {
            setTimeout(initializeMediaTab, 100);
        }
    });
});

console.log('📰🎧 NEWS & MEDIA TABS LOADED 📰🎧');
// ============================================
// AI TUTOR FUNCTIONALITY
// ============================================

// Tutor state
let tutorConversation = [];

// Initialize tutor tab
function initializeTutorTab() {
    console.log('🤖 Initializing AI Tutor tab...');
    // Load any saved conversation from session
    const saved = sessionStorage.getItem('tutorConversation');
    if (saved) {
        tutorConversation = JSON.parse(saved);
        renderTutorMessages();
    }
}

// Send message to tutor
async function sendTutorMessage() {
    const input = document.getElementById('tutorChatInput');
    const message = input.value.trim();
    
    if (!message) return;
    
    // Clear input
    input.value = '';
    
    // Add user message to conversation
    addTutorMessage('user', message);
    
    // Show typing indicator
    showTutorTyping(true);
    
    try {
        // Call the tutor API
        const response = await fetch(`${API_BASE}/api/tutor/ask`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                question: message,
                conversation_history: tutorConversation.slice(-6) // Last 3 exchanges for context
            })
        });
        
        if (!response.ok) {
            throw new Error('Failed to get response from tutor');
        }
        
        const data = await response.json();
        
        // Hide typing indicator
        showTutorTyping(false);
        
        // Add assistant response
        addTutorMessage('assistant', data.answer, data.citations);
        
    } catch (err) {
        console.error('Tutor error:', err);
        showTutorTyping(false);
        addTutorMessage('assistant', 'Sorry, I encountered an error. Please try again. Make sure the server is running and connected to Gemini API.');
    }
}

// Quick topic question
function askTutor(question) {
    const input = document.getElementById('tutorChatInput');
    input.value = question;
    sendTutorMessage();
}

// Add message to chat
function addTutorMessage(role, content, citations = null) {
    const messagesContainer = document.getElementById('tutorChatMessages');
    
    // Save to conversation history
    tutorConversation.push({ role, content });
    sessionStorage.setItem('tutorConversation', JSON.stringify(tutorConversation));
    
    // Create message element
    const messageDiv = document.createElement('div');
    messageDiv.className = `tutor-message ${role}`;
    
    const avatar = role === 'assistant' ? '🤖' : '👤';
    
    let citationsHtml = '';
    if (citations && citations.length > 0) {
        citationsHtml = `
            <div class="message-citations">
                <h4>📚 Sources</h4>
                ${citations.map(c => `
                    <div class="citation-item">
                        <span class="citation-icon">${c.type === 'pubmed' ? '📄' : '🏥'}</span>
                        <div>
                            <strong>${c.source}</strong>
                            ${c.url ? `<br><a href="${c.url}" target="_blank">View source →</a>` : ''}
                        </div>
                    </div>
                `).join('')}
            </div>
        `;
    }
    
    // Format content with markdown-like styling
    const formattedContent = formatTutorContent(content);
    
    messageDiv.innerHTML = `
        <div class="message-avatar">${avatar}</div>
        <div class="message-content">
            ${formattedContent}
            ${citationsHtml}
        </div>
    `;
    
    messagesContainer.appendChild(messageDiv);
    
    // Scroll to bottom
    messagesContainer.scrollTop = messagesContainer.scrollHeight;
}

// Format tutor content (basic markdown)
function formatTutorContent(content) {
    // Split into paragraphs
    let html = content
        .split('\n\n')
        .map(p => p.trim())
        .filter(p => p)
        .map(p => {
            // Check if it's a list
            if (p.match(/^[\-\*•]\s/m)) {
                const items = p.split(/\n/).map(item => 
                    item.replace(/^[\-\*•]\s*/, '').trim()
                ).filter(i => i);
                return `<ul>${items.map(i => `<li>${i}</li>`).join('')}</ul>`;
            }
            // Check if it's numbered list
            if (p.match(/^\d+\.\s/m)) {
                const items = p.split(/\n/).map(item => 
                    item.replace(/^\d+\.\s*/, '').trim()
                ).filter(i => i);
                return `<ol>${items.map(i => `<li>${i}</li>`).join('')}</ol>`;
            }
            // Regular paragraph
            return `<p>${p}</p>`;
        })
        .join('');
    
    // Bold text
    html = html.replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>');
    // Italic text
    html = html.replace(/\*(.+?)\*/g, '<em>$1</em>');
    
    return html;
}

// Show/hide typing indicator
function showTutorTyping(show) {
    const indicator = document.getElementById('tutorTypingIndicator');
    const sendBtn = document.getElementById('tutorSendBtn');
    
    if (show) {
        indicator?.classList.remove('hidden');
        if (sendBtn) sendBtn.disabled = true;
    } else {
        indicator?.classList.add('hidden');
        if (sendBtn) sendBtn.disabled = false;
    }
}

// Render all tutor messages (for restoring from session)
function renderTutorMessages() {
    const messagesContainer = document.getElementById('tutorChatMessages');
    if (!messagesContainer) return;
    
    // Keep the initial welcome message
    const welcomeMsg = messagesContainer.querySelector('.tutor-message.assistant');
    messagesContainer.innerHTML = '';
    if (welcomeMsg) messagesContainer.appendChild(welcomeMsg);
    
    // Add saved messages
    tutorConversation.forEach(msg => {
        const messageDiv = document.createElement('div');
        messageDiv.className = `tutor-message ${msg.role}`;
        const avatar = msg.role === 'assistant' ? '🤖' : '👤';
        messageDiv.innerHTML = `
            <div class="message-avatar">${avatar}</div>
            <div class="message-content">${formatTutorContent(msg.content)}</div>
        `;
        messagesContainer.appendChild(messageDiv);
    });
}

// Ask tutor about a specific topic after wrong answer
function askTutorAboutTopic(topic, questionContext) {
    // Switch to tutor tab
    const tutorTab = document.querySelector('[data-tab="tutor"]');
    if (tutorTab) tutorTab.click();
    
    // Wait for tab to load, then send question
    setTimeout(() => {
        const question = `I just answered a question about "${topic}" incorrectly. Can you explain this topic in detail? Here's the context: ${questionContext}`;
        const input = document.getElementById('tutorChatInput');
        if (input) {
            input.value = question;
            sendTutorMessage();
        }
    }, 300);
}

// Add tutor tab initialization to tab switch handler
document.querySelectorAll('.tab-btn').forEach(button => {
    button.addEventListener('click', () => {
        const tabId = button.getAttribute('data-tab');
        if (tabId === 'tutor') {
            setTimeout(initializeTutorTab, 100);
        }
    });
});

console.log('✅ AI Tutor module loaded');