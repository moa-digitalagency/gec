// Variables globales
let cropper = null;
let currentFile = null;

// Gestion du champ Secrétaire Général en copie
function toggleSGCopieField() {
    const typeCourrier = document.getElementById('type_courrier').value;
    const sgSection = document.getElementById('sg-copie-section');
    const sgSelect = document.getElementById('secretaire_general_copie');

    if (typeCourrier === 'ENTRANT') {
        sgSection.style.display = 'block';
        sgSelect.setAttribute('required', 'required');
    } else {
        sgSection.style.display = 'none';
        sgSelect.removeAttribute('required');
        sgSelect.value = '';  // Réinitialiser la valeur
    }
}

// Système de fichiers avancé
class AdvancedFileHandler {
    constructor() {
        this.initializeEventListeners();
    }

    initializeEventListeners() {
        // Zone d'upload de fichier
        const uploadZone = document.getElementById('file-upload-zone');
        if (uploadZone) {
            uploadZone.addEventListener('click', () => {
                document.getElementById('fichier').click();
            });
        }

        // Gestion du fichier sélectionné
        const fileInput = document.getElementById('fichier');
        if (fileInput) {
            fileInput.addEventListener('change', (e) => {
                this.handleFileSelection(e);
            });
        }

        // Bouton rogner (dans la zone de prévisualisation)
        const cropBtn = document.getElementById('crop-image-btn');
        if (cropBtn) {
            cropBtn.addEventListener('click', () => {
                if (currentFile && currentFile.type.startsWith('image/')) {
                    this.openCropModal();
                }
            });
        }

        // Bouton supprimer
        const removeBtn = document.getElementById('remove-file');
        if (removeBtn) {
            removeBtn.addEventListener('click', () => {
                this.removeFile();
            });
        }

        // Modal de rognage
        this.initializeCropModal();
    }

    handleFileSelection(e) {
        const file = e.target.files[0];
        if (!file) return;

        // Vérification de taille
        if (file.size > 16 * 1024 * 1024) {
            alert('Erreur: Le fichier est trop volumineux (max 16MB)');
            e.target.value = '';
            return;
        }

        // Vérification du type
        const allowedTypes = ['application/pdf', 'image/jpeg', 'image/jpg', 'image/png', 'image/tiff'];
        if (!allowedTypes.includes(file.type)) {
            alert('Erreur: Type de fichier non autorisé');
            e.target.value = '';
            return;
        }

        currentFile = file;
        this.showFilePreview(file);
    }

    showFilePreview(file) {
        const preview = document.getElementById('file-preview');
        const previewContent = document.getElementById('preview-content');
        const fileInfo = document.getElementById('file-info');
        const cropBtn = document.getElementById('crop-image-btn');

        // Mise à jour des informations
        fileInfo.textContent = `${file.name} - ${this.formatFileSize(file.size)}`;

        // Prévisualisation selon le type
        if (file.type.startsWith('image/')) {
            const reader = new FileReader();
            reader.onload = (e) => {
                previewContent.innerHTML = `
                    <img src="${e.target.result}" alt="Prévisualisation" class="max-w-full h-32 object-cover rounded-lg mx-auto">
                `;
            };
            reader.readAsDataURL(file);

            // Afficher le bouton de rognage pour les images
            cropBtn.classList.remove('hidden');
        } else if (file.type === 'application/pdf') {
            previewContent.innerHTML = `
                <div class="flex items-center justify-center h-32 bg-red-50 rounded-lg">
                    <i class="fas fa-file-pdf text-4xl text-red-500"></i>
                </div>
            `;

            // Masquer le bouton de rognage pour les PDF
            cropBtn.classList.add('hidden');
        }

        preview.classList.remove('hidden');
    }

    removeFile() {
        document.getElementById('fichier').value = '';
        document.getElementById('file-preview').classList.add('hidden');
        document.getElementById('crop-image-btn').classList.add('hidden');
        currentFile = null;
    }



    // Crop Modal
    initializeCropModal() {
        const modal = document.getElementById('crop-modal');
        const applyBtn = document.getElementById('apply-crop');
        const cancelBtn = document.getElementById('cancel-crop');
        const closeBtn = document.getElementById('close-crop');

        if (!modal) return;

        if (applyBtn) {
            applyBtn.addEventListener('click', () => {
                if (cropper) {
                    cropper.getCroppedCanvas().toBlob((blob) => {
                        const file = new File([blob], currentFile.name, { type: currentFile.type });
                        this.setFileFromBlob(file);
                        this.closeCropModal();
                    }, currentFile.type);
                }
            });
        }

        if (cancelBtn) {
            cancelBtn.addEventListener('click', () => {
                this.closeCropModal();
            });
        }

        if (closeBtn) {
            closeBtn.addEventListener('click', () => {
                this.closeCropModal();
            });
        }
    }

    openCropModal() {
        if (!currentFile || !currentFile.type.startsWith('image/')) return;

        const modal = document.getElementById('crop-modal');
        const img = document.getElementById('crop-image');

        const reader = new FileReader();
        reader.onload = (e) => {
            img.src = e.target.result;
            img.style.display = 'block';

            // Initialiser Cropper
            cropper = new Cropper(img, {
                aspectRatio: NaN, // Libre
                viewMode: 2,
                dragMode: 'move',
                autoCropArea: 1,
                restore: false,
                guides: true,
                center: true,
                highlight: false,
                cropBoxMovable: true,
                cropBoxResizable: true,
                toggleDragModeOnDblclick: false,
            });
        };
        reader.readAsDataURL(currentFile);

        modal.classList.remove('hidden');
    }

    closeCropModal() {
        const modal = document.getElementById('crop-modal');
        modal.classList.add('hidden');

        if (cropper) {
            cropper.destroy();
            cropper = null;
        }

        document.getElementById('crop-image').style.display = 'none';
    }

    setFileFromBlob(file) {
        // Créer un DataTransfer pour simuler un fichier sélectionné
        const dt = new DataTransfer();
        dt.items.add(file);
        document.getElementById('fichier').files = dt.files;

        currentFile = file;
        this.showFilePreview(file);

        // Afficher le bouton de rognage pour les images
        const cropBtn = document.getElementById('crop-image-btn');
        if (file.type.startsWith('image/')) {
            cropBtn.classList.remove('hidden');
        }
    }

    formatFileSize(bytes) {
        if (bytes === 0) return '0 Bytes';
        const k = 1024;
        const sizes = ['Bytes', 'KB', 'MB', 'GB'];
        const i = Math.floor(Math.log(bytes) / Math.log(k));
        return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
    }
}

// Fonctions existantes (maintenues pour compatibilité)
function updateCurrentTime() {
    const timeElement = document.querySelector('.current-time');
    if (!timeElement) return;

    const now = new Date();
    const timeString = now.toLocaleDateString('fr-FR') + ' à ' + now.toLocaleTimeString('fr-FR', {
        hour: '2-digit',
        minute: '2-digit'
    });
    timeElement.textContent = timeString;
}

function initializeRadioButtons() {
    const radioOptions = document.querySelectorAll('.mail-type-option');

    radioOptions.forEach(option => {
        const radio = option.querySelector('input[type="radio"]');
        const visual = option.querySelector('.radio-visual div');

        if (radio.checked) {
            visual.classList.remove('hidden');
            option.classList.add('border-rdc-blue', 'bg-blue-50');
        }

        option.addEventListener('click', function() {
            radioOptions.forEach(opt => {
                const vis = opt.querySelector('.radio-visual div');
                vis.classList.add('hidden');
                opt.classList.remove('border-rdc-blue', 'bg-blue-50');
            });

            radio.checked = true;
            visual.classList.remove('hidden');
            option.classList.add('border-rdc-blue', 'bg-blue-50');

            toggleContactField();
        });
    });
}

function toggleContactField() {
    const typeSelectedInput = document.querySelector('input[name="type_courrier"]:checked');
    if (!typeSelectedInput) return;

    const typeSelected = typeSelectedInput.value;
    const contactLabel = document.getElementById('contact-label');
    const contactInput = document.getElementById('contact');
    const destinataireField = document.querySelector('input[name="destinataire"]');

    // Gestion du champ SG en copie
    const sgSection = document.getElementById('sg-copie-section');
    const sgSelect = document.getElementById('secretaire_general_copie');

    // Gestion du champ type de courrier sortant
    const typeCourrierSortantSection = document.getElementById('type-courrier-sortant-section');
    const typeCourrierSortantSelect = document.getElementById('type_courrier_sortant_id');

    // Gestion du champ autres informations
    const autresInfoSection = document.getElementById('autres-informations-section');

    // Gestion des labels et hints de date
    const dateRedactionLabel = document.getElementById('date-redaction-label');
    const dateEmissionLabel = document.getElementById('date-emission-label');
    const dateRedactionHint = document.getElementById('date-redaction-hint');
    const dateEmissionHint = document.getElementById('date-emission-hint');
    const dateRedactionInput = document.getElementById('date_redaction');

    if (typeSelected === 'ENTRANT') {
        contactLabel.textContent = 'Expéditeur';
        contactInput.placeholder = 'Nom de l\'expéditeur';
        contactInput.name = 'expediteur';
        if (destinataireField) destinataireField.value = '';

        // Afficher le champ SG en copie pour les courriers entrants
        if (sgSection) sgSection.style.display = 'block';
        if (sgSelect) sgSelect.setAttribute('required', 'required');

        // Cacher le champ type de courrier sortant
        if (typeCourrierSortantSection) {
            typeCourrierSortantSection.style.display = 'none';
            if (typeCourrierSortantSelect) {
                typeCourrierSortantSelect.removeAttribute('required');
                typeCourrierSortantSelect.value = '';
            }
        }

        // Cacher le champ autres informations
        if (autresInfoSection) {
            autresInfoSection.style.display = 'none';
        }

        // Afficher le label "Date de Rédaction" (optionnel)
        if (dateRedactionLabel) dateRedactionLabel.style.display = 'inline';
        if (dateEmissionLabel) dateEmissionLabel.style.display = 'none';
        if (dateRedactionHint) dateRedactionHint.style.display = 'inline';
        if (dateEmissionHint) dateEmissionHint.style.display = 'none';
        if (dateRedactionInput) dateRedactionInput.removeAttribute('required');
    } else {
        contactLabel.textContent = 'Destinataire';
        contactInput.placeholder = 'Nom du destinataire';
        contactInput.name = 'destinataire';

        // Cacher le champ SG en copie pour les courriers sortants
        if (sgSection) sgSection.style.display = 'none';
        if (sgSelect) {
            sgSelect.removeAttribute('required');
            sgSelect.value = '';
        }

        // Afficher le champ type de courrier sortant
        if (typeCourrierSortantSection) {
            typeCourrierSortantSection.style.display = 'block';
            if (typeCourrierSortantSelect) typeCourrierSortantSelect.setAttribute('required', 'required');
        }

        // Afficher le champ autres informations
        if (autresInfoSection) {
            autresInfoSection.style.display = 'block';
        }

        // Afficher le label "Date d'Émission" (obligatoire)
        if (dateRedactionLabel) dateRedactionLabel.style.display = 'none';
        if (dateEmissionLabel) dateEmissionLabel.style.display = 'inline';
        if (dateRedactionHint) dateRedactionHint.style.display = 'none';
        if (dateEmissionHint) dateEmissionHint.style.display = 'inline';
        if (dateRedactionInput) dateRedactionInput.setAttribute('required', 'required');
    }
}



// Initialisation
document.addEventListener('DOMContentLoaded', function() {
    // Initialiser le gestionnaire de fichiers avancé
    new AdvancedFileHandler();

    // Initialiser les autres fonctions
    initializeRadioButtons();
    toggleContactField();

    // Attach event listeners for radio buttons explicitly for accessibility/robustness
    document.querySelectorAll('input[name="type_courrier"]').forEach(input => {
        input.addEventListener('change', toggleContactField);
    });

    setInterval(updateCurrentTime, 1000);
    updateCurrentTime();
});
