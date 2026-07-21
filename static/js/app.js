/**
 * Application JavaScript for GEC
 * Handles client-side interactions and enhancements
 */

document.addEventListener('DOMContentLoaded', function() {
    
    // Initialize all components
    initializeDataTables();
    initializeTooltips();
    initializeFormValidation();
    initializeFileUpload();
    initializeDateFilters();
    setupGlobalEventListeners();
    
    console.log('GEC Application Initialized');
});

/**
 * Initialize DataTables for enhanced table functionality
 */
function initializeDataTables() {
    const tables = document.querySelectorAll('#courriersTable');
    
    tables.forEach(table => {
        if (table && typeof $.fn.DataTable !== 'undefined') {
            $(table).DataTable({
                language: {
                    url: '/static/vendor/datatables/i18n/fr-FR.json'
                },
                pageLength: 25,
                responsive: true,
                order: [[4, 'desc']], // Sort by date column by default
                columnDefs: [
                    { orderable: false, targets: [6] }, // Actions column not sortable
                    { className: 'text-center', targets: [5, 6] } // Center align file and actions columns
                ]
            });
        }
    });
}

/**
 * Initialize Bootstrap tooltips
 */
function initializeTooltips() {
    if (typeof bootstrap !== 'undefined') {
        const tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"], [title]'));
        tooltipTriggerList.map(function (tooltipTriggerEl) {
            return new bootstrap.Tooltip(tooltipTriggerEl);
        });
    }
}

/**
 * Form validation and enhancement
 */
function initializeFormValidation() {
    const forms = document.querySelectorAll('form');
    
    forms.forEach(form => {
        // Add Bootstrap validation classes
        form.addEventListener('submit', function(event) {
            if (!form.checkValidity()) {
                event.preventDefault();
                event.stopPropagation();
                
                // Focus on first invalid field
                const firstInvalid = form.querySelector(':invalid');
                if (firstInvalid) {
                    firstInvalid.focus();
                }
            }
            
            form.classList.add('was-validated');
        });
        
        // Real-time validation for required fields
        const requiredFields = form.querySelectorAll('[required]');
        requiredFields.forEach(field => {
            field.addEventListener('blur', function() {
                validateField(field);
            });
            
            field.addEventListener('input', function() {
                if (field.classList.contains('is-invalid')) {
                    validateField(field);
                }
            });
        });
    });
}

/**
 * Validate individual form field
 */
function validateField(field) {
    const isValid = field.checkValidity();
    
    field.classList.remove('is-valid', 'is-invalid');
    field.classList.add(isValid ? 'is-valid' : 'is-invalid');
    
    // Update feedback message
    const feedback = field.parentNode.querySelector('.invalid-feedback');
    if (feedback && !isValid) {
        feedback.textContent = field.validationMessage;
    }
}

/**
 * File upload enhancements
 */
function initializeFileUpload() {
    const fileInputs = document.querySelectorAll('input[type="file"]');
    
    fileInputs.forEach(input => {
        input.addEventListener('change', function(event) {
            const file = event.target.files[0];
            
            if (file) {
                // Check file size (16MB limit)
                const maxSize = 16 * 1024 * 1024; // 16MB
                if (file.size > maxSize) {
                    showAlert('Erreur: Le fichier est trop volumineux (max 16MB)', 'error');
                    input.value = '';
                    return;
                }
                
                // Check file type
                const allowedTypes = ['application/pdf', 'image/jpeg', 'image/jpg', 'image/png', 'image/tiff'];
                if (!allowedTypes.includes(file.type)) {
                    showAlert('Erreur: Type de fichier non autorisé', 'error');
                    input.value = '';
                    return;
                }
                
                // Update file input label
                updateFileInputLabel(input, file.name);
                
                // Show file preview if it's an image
                if (file.type.startsWith('image/')) {
                    showImagePreview(file, input);
                }
            }
        });
    });
}

/**
 * Update file input label with selected filename
 */
function updateFileInputLabel(input, filename) {
    const label = input.parentNode.querySelector('.form-text');
    if (label) {
        label.innerHTML = `<i class="fas fa-check-circle text-success me-1"></i>Fichier sélectionné: <strong>${filename}</strong>`;
    }
}

/**
 * Show image preview
 */
function showImagePreview(file, input) {
    const reader = new FileReader();
    reader.onload = function(e) {
        // Remove existing preview
        const existingPreview = input.parentNode.querySelector('.image-preview');
        if (existingPreview) {
            existingPreview.remove();
        }
        
        // Create preview element
        const preview = document.createElement('div');
        preview.className = 'image-preview mt-2';
        preview.innerHTML = `
            <img src="${e.target.result}" alt="Preview" class="img-thumbnail" style="max-width: 200px; max-height: 200px;">
            <button type="button" class="btn btn-sm btn-outline-danger ms-2" onclick="removePreview(this)">
                <i class="fas fa-times"></i>
            </button>
        `;
        
        input.parentNode.appendChild(preview);
    };
    reader.readAsDataURL(file);
}

/**
 * Remove image preview
 */
function removePreview(button) {
    const preview = button.closest('.image-preview');
    const fileInput = preview.parentNode.querySelector('input[type="file"]');
    
    preview.remove();
    fileInput.value = '';
    
    // Reset label
    const label = fileInput.parentNode.querySelector('.form-text');
    if (label) {
        label.innerHTML = 'Formats acceptés: PDF, JPG, PNG, TIFF (Max: 16MB)';
    }
}

/**
 * Initialize date filters
 */
function initializeDateFilters() {
    const dateInputs = document.querySelectorAll('input[type="date"]');
    
    dateInputs.forEach(input => {
        // Set max date to today
        const today = new Date().toISOString().split('T')[0];
        if (!input.getAttribute('max')) {
            input.setAttribute('max', today);
        }
        
        // Validate date range
        input.addEventListener('change', function() {
            validateDateRange(this);
        });
    });
}

/**
 * Validate date range (from/to)
 */
function validateDateRange(input) {
    const form = input.closest('form');
    if (!form) return;
    
    const dateFrom = form.querySelector('input[name="date_from"]');
    const dateTo = form.querySelector('input[name="date_to"]');
    
    if (dateFrom && dateTo && dateFrom.value && dateTo.value) {
        if (new Date(dateFrom.value) > new Date(dateTo.value)) {
            showAlert('La date de début ne peut pas être postérieure à la date de fin', 'warning');
            input.value = '';
        }
    }
}

/**
 * Setup global event listeners
 */
function setupGlobalEventListeners() {
    // Confirm delete actions
    document.addEventListener('click', function(event) {
        const deleteBtn = event.target.closest('[data-confirm-delete]');
        if (deleteBtn) {
            event.preventDefault();
            
            const message = deleteBtn.getAttribute('data-confirm-delete') || 'Êtes-vous sûr de vouloir supprimer cet élément ?';
            if (confirm(message)) {
                // Proceed with delete action
                if (deleteBtn.href) {
                    window.location.href = deleteBtn.href;
                } else if (deleteBtn.onclick) {
                    deleteBtn.onclick();
                }
            }
        }
    });
    
    // Auto-hide alerts after 5 seconds
    const alerts = document.querySelectorAll('.alert:not(.alert-permanent)');
    alerts.forEach(alert => {
        setTimeout(() => {
            const bsAlert = new bootstrap.Alert(alert);
            bsAlert.close();
        }, 5000);
    });
    
    // Enhanced search functionality
    const searchInputs = document.querySelectorAll('input[name="search"]');
    searchInputs.forEach(input => {
        let searchTimeout;
        input.addEventListener('input', function() {
            clearTimeout(searchTimeout);
            searchTimeout = setTimeout(() => {
                // Auto-submit search after 500ms of inactivity
                if (this.value.length >= 3 || this.value.length === 0) {
                    const form = this.closest('form');
                    if (form && form.querySelector('button[type="submit"]')) {
                        // Only auto-submit if there's a submit button
                        // form.submit();
                    }
                }
            }, 500);
        });
    });
}

/**
 * Show alert message
 */
function showAlert(message, type = 'info') {
    const alertsContainer = document.querySelector('.container-fluid');
    if (!alertsContainer) return;
    
    const alertClass = type === 'error' ? 'alert-danger' : `alert-${type}`;
    const alertHtml = `
        <div class="alert ${alertClass} alert-dismissible fade show" role="alert">
            ${message}
            <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
        </div>
    `;
    
    alertsContainer.insertAdjacentHTML('afterbegin', alertHtml);
    
    // Auto-hide after 5 seconds
    setTimeout(() => {
        const alert = alertsContainer.querySelector('.alert');
        if (alert) {
            const bsAlert = new bootstrap.Alert(alert);
            bsAlert.close();
        }
    }, 5000);
}

/**
 * Copy text to clipboard
 */
function copyToClipboard(text, successMessage = 'Copié dans le presse-papier') {
    if (navigator.clipboard) {
        navigator.clipboard.writeText(text).then(() => {
            showAlert(successMessage, 'success');
        }).catch(() => {
            // Fallback for older browsers
            fallbackCopyToClipboard(text, successMessage);
        });
    } else {
        fallbackCopyToClipboard(text, successMessage);
    }
}

/**
 * Fallback copy method for older browsers
 */
function fallbackCopyToClipboard(text, successMessage) {
    const textArea = document.createElement('textarea');
    textArea.value = text;
    textArea.style.position = 'fixed';
    textArea.style.left = '-999999px';
    document.body.appendChild(textArea);
    textArea.focus();
    textArea.select();
    
    try {
        document.execCommand('copy');
        showAlert(successMessage, 'success');
    } catch (err) {
        showAlert('Erreur lors de la copie', 'error');
    }
    
    document.body.removeChild(textArea);
}

/**
 * Format file size
 */
function formatFileSize(bytes) {
    if (bytes === 0) return '0 Bytes';
    
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
}

/**
 * Export functions for global access
 */
window.GECApp = {
    showAlert,
    copyToClipboard,
    formatFileSize,
    removePreview
};
