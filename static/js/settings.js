function clearCaches() {
    if (confirm('Êtes-vous sûr de vouloir vider tous les caches ? Cette action peut temporairement ralentir le système.')) {
        fetch('/admin/clear-cache', { // Assuming the URL is standardized, but the template used {{ url_for }}
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            }
        })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                showNotification('Cache vidé avec succès !', 'success');
            } else {
                showNotification('Erreur lors du vidage du cache: ' + data.message, 'error');
            }
        })
        .catch(error => {
            showNotification('Erreur lors du vidage du cache', 'error');
        });
    }
}

function showNotification(message, type) {
    // Utilise showFlash global (défini dans new_base.html) pour les toasts GEC
    var flashType = type === 'success' ? 'success' : (type === 'warning' ? 'warning' : 'error');
    if (typeof window.showFlash === 'function') {
        window.showFlash(message, flashType);
    } else {
        // Fallback si showFlash non disponible
        alert(message);
    }
}

function toggleFormatField() {
    const modeSelect = document.getElementById('mode_numero_accuse');
    if (!modeSelect) return;

    const mode = modeSelect.value;
    const formatField = document.getElementById('format-field');
    const formatInput = document.getElementById('format_numero_accuse');

    if (mode === 'manuel') {
        formatField.classList.add('hidden');
        formatInput.removeAttribute('required');
    } else {
        formatField.classList.remove('hidden');
        formatInput.setAttribute('required', 'required');
    }
}

function toggleEmailProvider() {
    const emailProviderSelect = document.getElementById('email_provider');
    if (!emailProviderSelect) return;

    const emailProvider = emailProviderSelect.value;
    const smtpSection   = document.getElementById('smtp-section');
    const resendSection = document.getElementById('resend-section');

    if (emailProvider === 'smtp') {
        smtpSection.classList.remove('hidden');
        if (resendSection) resendSection.classList.add('hidden');
    } else {
        smtpSection.classList.add('hidden');
        if (resendSection) resendSection.classList.remove('hidden');
    }
}

function previewLogo(input) {
    const file = input.files[0];
    const previewArea = document.getElementById('file-preview');
    const previewImage = document.getElementById('preview-image');
    const fileName = document.getElementById('file-name');
    const uploadIcon = document.getElementById('upload-icon');
    const currentLogo = document.getElementById('current-logo');

    if (file) {
        const reader = new FileReader();
        reader.onload = function(e) {
            previewImage.src = e.target.result;
            fileName.textContent = file.name + ' - Prêt à télécharger';
            previewArea.classList.remove('hidden');

            // Hide upload icon and current logo
            if (uploadIcon) uploadIcon.classList.add('hidden');
            if (currentLogo) currentLogo.classList.add('hidden');
        };
        reader.readAsDataURL(file);
    } else {
        previewArea.classList.add('hidden');
        if (uploadIcon) uploadIcon.classList.remove('hidden');
        if (currentLogo) currentLogo.classList.remove('hidden');
    }
}

document.addEventListener('DOMContentLoaded', function() {
    // Enhanced format preview with comprehensive pattern support
    const formatInput = document.getElementById('format_numero_accuse');
    const previewElement = document.getElementById('preview-format');

    if (formatInput && previewElement) {
        function updateFormatPreview(format) {
            if (!format) format = 'GEC-{year}-{counter:05d}';

            const now = new Date();
            const year = now.getFullYear();
            const month = String(now.getMonth() + 1).padStart(2, '0');
            const day = String(now.getDate()).padStart(2, '0');

            let preview = format;

            // Replace basic date variables
            preview = preview.replace(/{year}/g, year);
            preview = preview.replace(/{month}/g, month);
            preview = preview.replace(/{day}/g, day);

            // Handle counter patterns with formatting {counter:05d}
            preview = preview.replace(/{counter:(\d+)d}/g, function(match, digits) {
                return String(1).padStart(parseInt(digits), '0');
            });

            // Handle simple counter
            preview = preview.replace(/{counter}/g, '1');

            // Handle random patterns {random:4}
            preview = preview.replace(/{random:(\d+)}/g, function(match, digits) {
                return '1'.repeat(parseInt(digits));
            });

            previewElement.textContent = preview;

            // Visual feedback for valid/invalid format
            if (preview.includes('{') && preview.includes('}')) {
                previewElement.className = 'font-mono bg-red-100 text-red-700 px-2 py-1 rounded';
                previewElement.title = 'Format invalide - variables non reconnues détectées';
            } else {
                previewElement.className = 'font-mono bg-gray-100 px-2 py-1 rounded';
                previewElement.title = 'Aperçu du format';
            }
        }

        formatInput.addEventListener('input', function() {
            updateFormatPreview(this.value);
        });

        updateFormatPreview(formatInput.value);
    }

    // Enhanced file upload with preview for main logo
    function setupFileUpload(inputId, previewContainerSelector, isMainLogo = true) {
        const input = document.getElementById(inputId);
        if (!input) return;

        function handleFileSelect(e) {
            const file = e.target.files[0];
            if (!file) return;

            // Validate file type
            const allowedTypes = ['image/png', 'image/jpeg', 'image/jpg', 'image/svg+xml'];
            if (!allowedTypes.includes(file.type)) {
                showNotification('Erreur: Type de fichier non autorisé. Utilisez PNG, JPG, JPEG ou SVG.', 'error');
                e.target.value = '';
                return;
            }

            // Validate file size (2MB)
            if (file.size > 2 * 1024 * 1024) {
                showNotification('Erreur: Le fichier est trop volumineux (maximum 2MB)', 'error');
                e.target.value = '';
                return;
            }

            // Show upload progress
            const progressBar = createProgressBar();
            const container = document.querySelector(previewContainerSelector);

            // Read file and show preview
            const reader = new FileReader();
            reader.onprogress = function(e) {
                if (e.lengthComputable) {
                    const percentLoaded = Math.round((e.loaded / e.total) * 100);
                    updateProgressBar(progressBar, percentLoaded);
                }
            };

            reader.onload = function(e) {
                setTimeout(() => {
                    removeProgressBar(progressBar);

                    if (isMainLogo) {
                        container.innerHTML = `
                            <div class="mb-4">
                                <img src="${e.target.result}" alt="Aperçu du logo" class="h-16 w-auto mx-auto rounded shadow-sm">
                                <p class="text-sm text-gray-500 mt-2">Nouveau logo (aperçu)</p>
                            </div>
                            <div class="flex text-sm text-gray-600">
                                <label for="${inputId}" class="relative cursor-pointer bg-white rounded-md font-medium text-rdc-blue hover:text-rdc-green focus-within:outline-none focus-within:ring-2 focus-within:ring-offset-2 focus-within:ring-rdc-blue">
                                    <span>Changer le fichier</span>
                                    <input id="${inputId}" name="${inputId}" type="file" class="sr-only" accept=".png,.jpg,.jpeg,.svg">
                                </label>
                            </div>
                            <p class="text-xs text-gray-500">PNG, JPG, JPEG, SVG jusqu'à 2MB</p>
                        `;
                    } else {
                        // For PDF logo
                        const imgContainer = container.querySelector('.mb-4') || document.createElement('div');
                        imgContainer.className = 'mb-4';
                        imgContainer.innerHTML = `<img src="${e.target.result}" alt="Logo PDF" class="mx-auto h-16 object-contain rounded shadow-sm">`;
                        if (!container.querySelector('.mb-4')) {
                            container.insertBefore(imgContainer, container.firstChild);
                        }
                    }

                    // Re-attach event listener
                    const newInput = document.getElementById(inputId);
                    if (newInput) {
                        newInput.addEventListener('change', handleFileSelect);
                    }

                    showNotification('Image chargée avec succès!', 'success');
                }, 500);
            };

            reader.onerror = function() {
                removeProgressBar(progressBar);
                showNotification('Erreur lors du chargement du fichier', 'error');
                e.target.value = '';
            };

            reader.readAsDataURL(file);
        }

        input.addEventListener('change', handleFileSelect);

        // Add drag and drop functionality
        const dropZone = input.closest('.border-dashed') || input.closest('.border');
        if (dropZone) {
            ['dragenter', 'dragover', 'dragleave', 'drop'].forEach(eventName => {
                dropZone.addEventListener(eventName, preventDefaults, false);
            });

            ['dragenter', 'dragover'].forEach(eventName => {
                dropZone.addEventListener(eventName, highlight, false);
            });

            ['dragleave', 'drop'].forEach(eventName => {
                dropZone.addEventListener(eventName, unhighlight, false);
            });

            dropZone.addEventListener('drop', handleDrop, false);

            function preventDefaults(e) {
                e.preventDefault();
                e.stopPropagation();
            }

            function highlight(e) {
                dropZone.classList.add('border-rdc-blue', 'bg-blue-50');
            }

            function unhighlight(e) {
                dropZone.classList.remove('border-rdc-blue', 'bg-blue-50');
            }

            function handleDrop(e) {
                const dt = e.dataTransfer;
                const files = dt.files;

                if (files.length > 0) {
                    input.files = files;
                    handleFileSelect({ target: input });
                }
            }
        }
    }

    // Setup file uploads
    setupFileUpload('logo', '.space-y-1.text-center', true);
    setupFileUpload('logo_pdf', '.border-dashed', false);

    // Form validation and feedback
    function setupFormValidation() {
        const form = document.querySelector('form');
        if (!form) return;

        const inputs = form.querySelectorAll('input[required], textarea[required]');

        inputs.forEach(input => {
            input.addEventListener('blur', validateField);
            input.addEventListener('input', function() {
                if (this.classList.contains('border-red-300')) {
                    validateField.call(this);
                }
            });
        });

        function validateField() {
            const field = this;
            const value = field.value.trim();

            // Remove existing error styling
            field.classList.remove('border-red-300', 'border-green-300');

            // Remove existing feedback
            const existingFeedback = field.parentNode.querySelector('.validation-feedback');
            if (existingFeedback) {
                existingFeedback.remove();
            }

            let isValid = true;
            let message = '';

            if (field.hasAttribute('required') && !value) {
                isValid = false;
                message = 'Ce champ est obligatoire';
            } else if (field.type === 'email' && value && !isValidEmail(value)) {
                isValid = false;
                message = 'Format d\'email invalide';
            } else if (field.type === 'tel' && value && !isValidPhone(value)) {
                isValid = false;
                message = 'Format de téléphone invalide';
            }

            // Apply styling and feedback
            if (!isValid) {
                field.classList.add('border-red-300');
                showFieldFeedback(field, message, 'error');
            } else if (value) {
                field.classList.add('border-green-300');
            }

            return isValid;
        }

        // Form submission handling
        form.addEventListener('submit', function(e) {
            const submitButton = form.querySelector('button[type="submit"]');

            // Validate all required fields only
            let isFormValid = true;
            const requiredInputs = form.querySelectorAll('input[required]');
            requiredInputs.forEach(input => {
                if (!input.value.trim()) {
                    isFormValid = false;
                    input.classList.add('border-red-300');
                }
            });

            if (!isFormValid) {
                e.preventDefault();
                showNotification('Veuillez remplir tous les champs obligatoires', 'error');
                return;
            }

            // Show loading state
            if (submitButton) {
                submitButton.disabled = true;
                submitButton.innerHTML = '<i class="fas fa-spinner fa-spin mr-2"></i>Enregistrement...';
            }
        });
    }

    // Utility functions
    function isValidEmail(email) {
        const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
        return emailRegex.test(email);
    }

    function isValidPhone(phone) {
        const phoneRegex = /^\+?[\d\s\-\(\)]{10,}$/;
        return phoneRegex.test(phone);
    }

    function showFieldFeedback(field, message, type) {
        const feedback = document.createElement('p');
        feedback.className = `validation-feedback mt-1 text-sm ${type === 'error' ? 'text-red-600' : 'text-green-600'}`;
        feedback.innerHTML = `<i class="fas fa-${type === 'error' ? 'exclamation-circle' : 'check-circle'} mr-1"></i>${message}`;
        field.parentNode.appendChild(feedback);
    }

    function createProgressBar() {
        const progressContainer = document.createElement('div');
        progressContainer.className = 'fixed top-4 left-1/2 transform -translate-x-1/2 z-50 bg-white rounded-lg shadow-lg p-4 min-w-64';
        progressContainer.innerHTML = `
            <div class="flex items-center mb-2">
                <i class="fas fa-cloud-upload-alt text-rdc-blue mr-2"></i>
                <span class="text-sm font-medium">Chargement de l'image...</span>
            </div>
            <div class="w-full bg-gray-200 rounded-full h-2">
                <div class="bg-rdc-blue h-2 rounded-full transition-all duration-300" style="width: 0%"></div>
            </div>
        `;

        document.body.appendChild(progressContainer);
        return progressContainer;
    }

    function updateProgressBar(progressContainer, percentage) {
        const progressBar = progressContainer.querySelector('.bg-rdc-blue');
        if (progressBar) {
            progressBar.style.width = `${percentage}%`;
        }
    }

    function removeProgressBar(progressContainer) {
        if (progressContainer && progressContainer.parentNode) {
            progressContainer.remove();
        }
    }

    // Initialize all functionality
    setupFormValidation();

    // Attach event listeners for dynamic toggles
    const modeSelect = document.getElementById('mode_numero_accuse');
    if (modeSelect) {
        modeSelect.addEventListener('change', toggleFormatField);
    }

    const emailProviderSelect = document.getElementById('email_provider');
    if (emailProviderSelect) {
        emailProviderSelect.addEventListener('change', toggleEmailProvider);
    }

    // Attach event listener for clear caches
    const clearCacheBtn = document.getElementById('clear-cache-btn');
    if (clearCacheBtn) {
        clearCacheBtn.addEventListener('click', function(e) {
            e.preventDefault();
            clearCaches();
        });
    }

    // Auto-save draft functionality (optional)
    let autoSaveTimeout;
    const formInputs = document.querySelectorAll('input, textarea');

    formInputs.forEach(input => {
        input.addEventListener('input', function() {
            clearTimeout(autoSaveTimeout);
            autoSaveTimeout = setTimeout(() => {
                // Auto-save draft logic can be implemented here
                console.log('Auto-saving draft...');
            }, 2000);
        });
    });
});
