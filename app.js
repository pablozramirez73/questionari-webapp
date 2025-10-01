// Gestione stato dell'applicazione
class QuestionnaireApp {
    constructor() {
        this.questionnaires = this.loadFromStorage();
        this.currentQuestionnaireId = null;
        this.init();
    }

    init() {
        this.setupEventListeners();
        this.renderQuestionnaires();
        this.updateEmptyState();
    }

    // Local Storage
    loadFromStorage() {
        const data = localStorage.getItem('questionnaires');
        return data ? JSON.parse(data) : [];
    }

    saveToStorage() {
        localStorage.setItem('questionnaires', JSON.stringify(this.questionnaires));
    }

    // Event Listeners
    setupEventListeners() {
        // Tab navigation
        document.querySelectorAll('.tab-btn').forEach(btn => {
            btn.addEventListener('click', (e) => this.switchTab(e.target.dataset.tab));
        });

        // Form submission
        document.getElementById('questionnaire-form').addEventListener('submit', (e) => {
            e.preventDefault();
            this.saveQuestionnaire();
        });

        // Add question button
        document.getElementById('add-question-btn').addEventListener('click', () => {
            this.addQuestion();
        });

        // Cancel button
        document.getElementById('cancel-btn').addEventListener('click', () => {
            this.resetForm();
            this.switchTab('list');
        });

        // Back to list button
        document.getElementById('back-to-list-btn').addEventListener('click', () => {
            this.switchTab('list');
        });
    }

    // Tab Management
    switchTab(tabName) {
        // Update tab buttons
        document.querySelectorAll('.tab-btn').forEach(btn => {
            btn.classList.toggle('active', btn.dataset.tab === tabName);
        });

        // Update tab content
        document.querySelectorAll('.tab-content').forEach(content => {
            content.classList.remove('active');
        });

        document.getElementById(`${tabName}-section`).classList.add('active');
    }

    // Questionnaire Management
    renderQuestionnaires() {
        const container = document.getElementById('questionnaires-list');
        container.innerHTML = '';

        this.questionnaires.forEach(q => {
            const card = this.createQuestionnaireCard(q);
            container.appendChild(card);
        });

        this.updateEmptyState();
    }

    createQuestionnaireCard(questionnaire) {
        const card = document.createElement('div');
        card.className = 'questionnaire-card';
        
        const questionCount = questionnaire.questions.length;
        const createdDate = new Date(questionnaire.createdAt).toLocaleDateString('it-IT');

        card.innerHTML = `
            <h3>${this.escapeHtml(questionnaire.title)}</h3>
            <p>${this.escapeHtml(questionnaire.description || 'Nessuna descrizione')}</p>
            <div class="meta">
                📅 ${createdDate} | 📝 ${questionCount} domand${questionCount === 1 ? 'a' : 'e'}
            </div>
            <div class="card-actions">
                <button class="btn btn-success" onclick="app.viewQuestionnaire('${questionnaire.id}')">
                    👁️ Visualizza
                </button>
                <button class="btn btn-warning" onclick="app.editQuestionnaire('${questionnaire.id}')">
                    ✏️ Modifica
                </button>
                <button class="btn btn-danger" onclick="app.deleteQuestionnaire('${questionnaire.id}')">
                    🗑️ Elimina
                </button>
            </div>
        `;

        return card;
    }

    updateEmptyState() {
        const emptyState = document.getElementById('empty-state');
        const list = document.getElementById('questionnaires-list');
        
        if (this.questionnaires.length === 0) {
            emptyState.style.display = 'block';
            list.style.display = 'none';
        } else {
            emptyState.style.display = 'none';
            list.style.display = 'grid';
        }
    }

    saveQuestionnaire() {
        const id = document.getElementById('questionnaire-id').value;
        const title = document.getElementById('questionnaire-title').value.trim();
        const description = document.getElementById('questionnaire-description').value.trim();

        if (!title) {
            alert('Il titolo è obbligatorio!');
            return;
        }

        const questions = this.collectQuestions();

        if (questions.length === 0) {
            alert('Aggiungi almeno una domanda al questionario!');
            return;
        }

        const questionnaire = {
            id: id || this.generateId(),
            title,
            description,
            questions,
            createdAt: id ? this.questionnaires.find(q => q.id === id).createdAt : Date.now(),
            updatedAt: Date.now()
        };

        if (id) {
            // Update existing
            const index = this.questionnaires.findIndex(q => q.id === id);
            this.questionnaires[index] = questionnaire;
            this.showAlert('success', 'Questionario aggiornato con successo!');
        } else {
            // Create new
            this.questionnaires.push(questionnaire);
            this.showAlert('success', 'Questionario creato con successo!');
        }

        this.saveToStorage();
        this.renderQuestionnaires();
        this.resetForm();
        this.switchTab('list');
    }

    collectQuestions() {
        const questions = [];
        const questionItems = document.querySelectorAll('.question-item');

        questionItems.forEach((item, index) => {
            const text = item.querySelector('.question-text').value.trim();
            const type = item.querySelector('.question-type').value;
            const required = item.querySelector('.question-required').checked;
            
            if (!text) return;

            const question = {
                id: this.generateId(),
                text,
                type,
                required,
                order: index
            };

            // Add options for radio/checkbox
            if (type === 'radio' || type === 'checkbox') {
                const optionsText = item.querySelector('.question-options').value.trim();
                question.options = optionsText.split('\n')
                    .map(opt => opt.trim())
                    .filter(opt => opt.length > 0);
            }

            questions.push(question);
        });

        return questions;
    }

    editQuestionnaire(id) {
        const questionnaire = this.questionnaires.find(q => q.id === id);
        if (!questionnaire) return;

        this.currentQuestionnaireId = id;

        // Fill form
        document.getElementById('questionnaire-id').value = questionnaire.id;
        document.getElementById('questionnaire-title').value = questionnaire.title;
        document.getElementById('questionnaire-description').value = questionnaire.description;
        document.getElementById('form-title').textContent = 'Modifica Questionario';

        // Clear and add questions
        document.getElementById('questions-container').innerHTML = '';
        questionnaire.questions.forEach(q => {
            this.addQuestion(q);
        });

        this.switchTab('create');
    }

    deleteQuestionnaire(id) {
        if (!confirm('Sei sicuro di voler eliminare questo questionario?')) return;

        this.questionnaires = this.questionnaires.filter(q => q.id !== id);
        this.saveToStorage();
        this.renderQuestionnaires();
        this.showAlert('success', 'Questionario eliminato!');
    }

    viewQuestionnaire(id) {
        const questionnaire = this.questionnaires.find(q => q.id === id);
        if (!questionnaire) return;

        const container = document.getElementById('questionnaire-view');
        document.getElementById('view-title').textContent = questionnaire.title;

        let html = `
            <div class="view-header">
                <h3>${this.escapeHtml(questionnaire.title)}</h3>
                ${questionnaire.description ? `<p>${this.escapeHtml(questionnaire.description)}</p>` : ''}
            </div>
        `;

        questionnaire.questions.forEach((q, index) => {
            html += `
                <div class="view-question">
                    <h4>
                        ${index + 1}. ${this.escapeHtml(q.text)}
                        ${q.required ? '<span class="required">*</span>' : ''}
                    </h4>
                    ${this.renderAnswerInput(q)}
                </div>
            `;
        });

        html += `
            <div class="form-actions">
                <button class="btn btn-primary" onclick="app.submitAnswers('${id}')">
                    📤 Invia Risposte
                </button>
            </div>
        `;

        container.innerHTML = html;
        this.switchTab('view');
    }

    renderAnswerInput(question) {
        switch (question.type) {
            case 'text':
                return `<input type="text" class="answer-input" placeholder="La tua risposta..." ${question.required ? 'required' : ''}>`;
            
            case 'textarea':
                return `<textarea class="answer-input" rows="4" placeholder="La tua risposta..." ${question.required ? 'required' : ''}></textarea>`;
            
            case 'number':
                return `<input type="number" class="answer-input" placeholder="Inserisci un numero..." ${question.required ? 'required' : ''}>`;
            
            case 'radio':
                return `
                    <div class="answer-options">
                        ${question.options.map((opt, i) => `
                            <label class="answer-option">
                                <input type="radio" name="q-${question.id}" value="${this.escapeHtml(opt)}" ${question.required ? 'required' : ''}>
                                ${this.escapeHtml(opt)}
                            </label>
                        `).join('')}
                    </div>
                `;
            
            case 'checkbox':
                return `
                    <div class="answer-options">
                        ${question.options.map((opt, i) => `
                            <label class="answer-option">
                                <input type="checkbox" name="q-${question.id}" value="${this.escapeHtml(opt)}">
                                ${this.escapeHtml(opt)}
                            </label>
                        `).join('')}
                    </div>
                `;
            
            default:
                return '';
        }
    }

    submitAnswers(id) {
        const questions = document.querySelectorAll('.view-question');
        const answers = [];
        let valid = true;

        questions.forEach(q => {
            const inputs = q.querySelectorAll('input, textarea');
            const required = q.querySelector('.required') !== null;
            
            let answered = false;
            inputs.forEach(input => {
                if (input.type === 'radio' || input.type === 'checkbox') {
                    if (input.checked) answered = true;
                } else if (input.value.trim()) {
                    answered = true;
                }
            });

            if (required && !answered) {
                valid = false;
            }
        });

        if (!valid) {
            alert('Per favore, rispondi a tutte le domande obbligatorie (*)');
            return;
        }

        this.showAlert('success', 'Risposte inviate con successo! 🎉');
        setTimeout(() => {
            this.switchTab('list');
        }, 1500);
    }

    // Question Management
    addQuestion(questionData = null) {
        const template = document.getElementById('question-template');
        const clone = template.content.cloneNode(true);
        const questionItem = clone.querySelector('.question-item');

        // Setup question number
        const container = document.getElementById('questions-container');
        const questionNumber = container.children.length + 1;
        clone.querySelector('.question-number').textContent = `Domanda ${questionNumber}`;

        // Fill with data if editing
        if (questionData) {
            clone.querySelector('.question-text').value = questionData.text;
            clone.querySelector('.question-type').value = questionData.type;
            clone.querySelector('.question-required').checked = questionData.required;
            
            if (questionData.options) {
                clone.querySelector('.question-options').value = questionData.options.join('\n');
                clone.querySelector('.options-group').style.display = 'block';
            }
        }

        // Setup event listeners
        const typeSelect = clone.querySelector('.question-type');
        const optionsGroup = clone.querySelector('.options-group');
        
        typeSelect.addEventListener('change', () => {
            optionsGroup.style.display = 
                (typeSelect.value === 'radio' || typeSelect.value === 'checkbox') ? 'block' : 'none';
        });

        // Delete button
        clone.querySelector('.btn-delete').addEventListener('click', (e) => {
            e.target.closest('.question-item').remove();
            this.updateQuestionNumbers();
        });

        // Move up button
        clone.querySelector('.btn-move-up').addEventListener('click', (e) => {
            const item = e.target.closest('.question-item');
            const prev = item.previousElementSibling;
            if (prev) {
                container.insertBefore(item, prev);
                this.updateQuestionNumbers();
            }
        });

        // Move down button
        clone.querySelector('.btn-move-down').addEventListener('click', (e) => {
            const item = e.target.closest('.question-item');
            const next = item.nextElementSibling;
            if (next) {
                container.insertBefore(next, item);
                this.updateQuestionNumbers();
            }
        });

        container.appendChild(clone);
    }

    updateQuestionNumbers() {
        const questions = document.querySelectorAll('.question-item');
        questions.forEach((q, index) => {
            q.querySelector('.question-number').textContent = `Domanda ${index + 1}`;
        });
    }

    resetForm() {
        document.getElementById('questionnaire-form').reset();
        document.getElementById('questionnaire-id').value = '';
        document.getElementById('questions-container').innerHTML = '';
        document.getElementById('form-title').textContent = 'Crea Nuovo Questionario';
        this.currentQuestionnaireId = null;
    }

    // Utility functions
    generateId() {
        return 'q_' + Date.now() + '_' + Math.random().toString(36).substr(2, 9);
    }

    escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }

    showAlert(type, message) {
        const alertClass = type === 'success' ? 'alert-success' : 
                          type === 'error' ? 'alert-error' : 'alert-info';
        
        const alert = document.createElement('div');
        alert.className = `alert ${alertClass}`;
        alert.innerHTML = `
            <span>${type === 'success' ? '✅' : '❌'}</span>
            <span>${message}</span>
        `;

        const main = document.querySelector('main');
        main.insertBefore(alert, main.firstChild);

        setTimeout(() => {
            alert.remove();
        }, 3000);
    }
}

// Initialize app
const app = new QuestionnaireApp();
