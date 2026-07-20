let originalImage = null;
let croppedImage = null;
let canvas = null;
let ctx = null;
let isDragging = false;
let startX = 0;
let startY = 0;
let cropArea = { x: 0, y: 0, width: 200, height: 200 };

function previewImage(input) {
    const file = input.files[0];
    const container = document.getElementById('image-preview-container');
    const fileName = document.getElementById('file-name');

    if (file) {
        // Validation de la taille
        const maxSize = 5 * 1024 * 1024; // 5MB
        if (file.size > maxSize) {
            alert('La taille du fichier dépasse 5 Mo. Veuillez choisir une image plus petite.');
            removeImagePreview();
            return;
        }

        // Validation du type
        const allowedTypes = ['image/jpeg', 'image/png', 'image/gif'];
        if (!allowedTypes.includes(file.type)) {
            alert('Format non supporté. Veuillez choisir une image JPG, PNG ou GIF.');
            removeImagePreview();
            return;
        }

        const reader = new FileReader();
        reader.onload = function(e) {
            originalImage = new Image();
            originalImage.onload = function() {
                setupCropCanvas();
                container.classList.remove('hidden');
            };
            originalImage.src = e.target.result;
        };
        reader.readAsDataURL(file);
        fileName.textContent = file.name;
    }
}

function setupCropCanvas() {
    canvas = document.getElementById('crop-canvas');
    ctx = canvas.getContext('2d');

    // Redimensionner l'image pour le canvas
    const maxWidth = 400;
    const maxHeight = 400;
    let { width, height } = originalImage;

    if (width > maxWidth || height > maxHeight) {
        const ratio = Math.min(maxWidth / width, maxHeight / height);
        width *= ratio;
        height *= ratio;
    }

    canvas.width = width;
    canvas.height = height;

    // Initialiser la zone de crop au centre
    cropArea = {
        x: (width - 200) / 2,
        y: (height - 200) / 2,
        width: 200,
        height: 200
    };

    drawCanvas();
    setupCropEvents();
}

function drawCanvas() {
    ctx.clearRect(0, 0, canvas.width, canvas.height);

    // Dessiner l'image
    ctx.drawImage(originalImage, 0, 0, canvas.width, canvas.height);

    // Dessiner l'overlay sombre
    ctx.fillStyle = 'rgba(0, 0, 0, 0.5)';
    ctx.fillRect(0, 0, canvas.width, canvas.height);

    // Effacer la zone de crop
    ctx.clearRect(cropArea.x, cropArea.y, cropArea.width, cropArea.height);

    // Redessiner l'image dans la zone de crop
    ctx.drawImage(originalImage, 0, 0, canvas.width, canvas.height);

    // Dessiner le cadre de crop
    ctx.strokeStyle = '#003087';
    ctx.lineWidth = 2;
    ctx.strokeRect(cropArea.x, cropArea.y, cropArea.width, cropArea.height);

    // Dessiner les coins pour le redimensionnement
    ctx.fillStyle = '#003087';
    const cornerSize = 8;
    ctx.fillRect(cropArea.x - cornerSize/2, cropArea.y - cornerSize/2, cornerSize, cornerSize);
    ctx.fillRect(cropArea.x + cropArea.width - cornerSize/2, cropArea.y - cornerSize/2, cornerSize, cornerSize);
    ctx.fillRect(cropArea.x - cornerSize/2, cropArea.y + cropArea.height - cornerSize/2, cornerSize, cornerSize);
    ctx.fillRect(cropArea.x + cropArea.width - cornerSize/2, cropArea.y + cropArea.height - cornerSize/2, cornerSize, cornerSize);
}

function setupCropEvents() {
    canvas.addEventListener('mousedown', handleMouseDown);
    canvas.addEventListener('mousemove', handleMouseMove);
    canvas.addEventListener('mouseup', handleMouseUp);
    canvas.style.cursor = 'crosshair';
}

function handleMouseDown(e) {
    const rect = canvas.getBoundingClientRect();
    const x = e.clientX - rect.left;
    const y = e.clientY - rect.top;

    if (x >= cropArea.x && x <= cropArea.x + cropArea.width &&
        y >= cropArea.y && y <= cropArea.y + cropArea.height) {
        isDragging = true;
        startX = x - cropArea.x;
        startY = y - cropArea.y;
        canvas.style.cursor = 'move';
    }
}

function handleMouseMove(e) {
    if (!isDragging) return;

    const rect = canvas.getBoundingClientRect();
    const x = e.clientX - rect.left;
    const y = e.clientY - rect.top;

    cropArea.x = Math.max(0, Math.min(canvas.width - cropArea.width, x - startX));
    cropArea.y = Math.max(0, Math.min(canvas.height - cropArea.height, y - startY));

    drawCanvas();
}

function handleMouseUp() {
    isDragging = false;
    canvas.style.cursor = 'crosshair';
}

function applyCrop() {
    if (!originalImage) return;

    // Calculer les proportions pour l'image originale
    const scaleX = originalImage.width / canvas.width;
    const scaleY = originalImage.height / canvas.height;

    // Créer un canvas temporaire pour le crop
    const tempCanvas = document.createElement('canvas');
    const tempCtx = tempCanvas.getContext('2d');
    tempCanvas.width = cropArea.width * scaleX;
    tempCanvas.height = cropArea.height * scaleY;

    // Extraire la zone croppée
    tempCtx.drawImage(
        originalImage,
        cropArea.x * scaleX, cropArea.y * scaleY,
        cropArea.width * scaleX, cropArea.height * scaleY,
        0, 0,
        tempCanvas.width, tempCanvas.height
    );

    // Afficher la prévisualisation finale
    const finalPreview = document.getElementById('final-preview');
    finalPreview.src = tempCanvas.toDataURL('image/jpeg', 0.8);

    // Stocker l'image croppée
    croppedImage = tempCanvas.toDataURL('image/jpeg', 0.8);
}

function resetCrop() {
    if (originalImage) {
        setupCropCanvas();
        document.getElementById('final-preview').src = '';
        croppedImage = null;
    }
}

function removeImagePreview() {
    const container = document.getElementById('image-preview-container');
    const input = document.getElementById('photo_profile');
    const fileName = document.getElementById('file-name');
    const finalPreview = document.getElementById('final-preview');

    container.classList.add('hidden');
    input.value = '';
    fileName.textContent = '';
    finalPreview.src = '';
    originalImage = null;
    croppedImage = null;
    canvas = null;
    ctx = null;
}

// Ajouter l'image croppée au formulaire avant soumission
document.addEventListener('DOMContentLoaded', function() {
    const form = document.querySelector('form');
    if (form) {
        form.addEventListener('submit', function(e) {
            if (croppedImage) {
                // Convertir l'image croppée en Blob et l'ajouter au FormData
                const byteCharacters = atob(croppedImage.split(',')[1]);
                const byteNumbers = new Array(byteCharacters.length);
                for (let i = 0; i < byteCharacters.length; i++) {
                    byteNumbers[i] = byteCharacters.charCodeAt(i);
                }
                const byteArray = new Uint8Array(byteNumbers);
                const blob = new Blob([byteArray], { type: 'image/jpeg' });

                // Remplacer le fichier original par l'image croppée
                const fileInput = document.getElementById('photo_profile');
                const dt = new DataTransfer();
                dt.items.add(new File([blob], 'cropped_image.jpg', { type: 'image/jpeg' }));
                fileInput.files = dt.files;
            }
        });
    }

    // Attach event listeners for buttons
    const btnApplyCrop = document.getElementById('btn-apply-crop');
    if (btnApplyCrop) btnApplyCrop.addEventListener('click', applyCrop);

    const btnResetCrop = document.getElementById('btn-reset-crop');
    if (btnResetCrop) btnResetCrop.addEventListener('click', resetCrop);

    const btnRemovePreview = document.getElementById('btn-remove-preview');
    if (btnRemovePreview) btnRemovePreview.addEventListener('click', removeImagePreview);

    const photoInput = document.getElementById('photo_profile');
    if (photoInput) {
        photoInput.addEventListener('change', function() {
            previewImage(this);
        });
    }

    // Drag and drop functionality
    const label = document.querySelector('label[for="photo_profile"]');
    if (label) {
        ['dragenter', 'dragover', 'dragleave', 'drop'].forEach(eventName => {
            label.addEventListener(eventName, preventDefaults, false);
        });

        function preventDefaults(e) {
            e.preventDefault();
            e.stopPropagation();
        }

        ['dragenter', 'dragover'].forEach(eventName => {
            label.addEventListener(eventName, highlight, false);
        });

        ['dragleave', 'drop'].forEach(eventName => {
            label.addEventListener(eventName, unhighlight, false);
        });

        function highlight(e) {
            label.classList.add('border-rdc-blue', 'bg-blue-50');
        }

        function unhighlight(e) {
            label.classList.remove('border-rdc-blue', 'bg-blue-50');
        }

        label.addEventListener('drop', handleDrop, false);

        function handleDrop(e) {
            const dt = e.dataTransfer;
            const files = dt.files;

            const input = document.getElementById('photo_profile');
            input.files = files;
            previewImage(input);
        }
    }
});
