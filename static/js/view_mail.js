// Fonctions globales
function toggleSortOrder() {
    const sortOrderSelect = document.getElementById('sort_order');
    const currentOrder = sortOrderSelect.value;
    sortOrderSelect.value = currentOrder === 'desc' ? 'asc' : 'desc';

    // Submit the form automatically
    document.querySelector('form').submit();
}

function confirmDelete(id, numero) {
    if (confirm(`Êtes-vous sûr de vouloir supprimer le courrier ${numero} ?\n\nCette action déplacera le courrier dans la corbeille.`)) {
        // Créer un formulaire pour envoyer la requête POST
        const form = document.createElement('form');
        form.method = 'POST';
        form.action = `/delete_courrier/${id}`;
        document.body.appendChild(form);
        form.submit();
    }
}

document.addEventListener('DOMContentLoaded', function() {
    // Toggle filters based on mail type
    const typeCourrierSelect = document.getElementById('type_courrier');
    const typeCourrierSortantFilter = document.getElementById('type-courrier-sortant-filter');
    const sgCopieFilter = document.getElementById('sg-copie-filter');

    if (typeCourrierSelect) {
        typeCourrierSelect.addEventListener('change', function() {
            // Handle outgoing mail type filter
            if (typeCourrierSortantFilter) {
                if (this.value === 'SORTANT') {
                    typeCourrierSortantFilter.style.display = 'block';
                } else {
                    typeCourrierSortantFilter.style.display = 'none';
                    // Reset selection when hiding
                    const typeCourrierSortantSelect = document.getElementById('type_courrier_sortant_id');
                    if (typeCourrierSortantSelect) {
                        typeCourrierSortantSelect.value = '';
                    }
                }
            }

            // Handle SG en copie filter (only for ENTRANT)
            if (sgCopieFilter) {
                if (this.value === 'ENTRANT') {
                    sgCopieFilter.style.display = 'block';
                } else {
                    sgCopieFilter.style.display = 'none';
                    // Reset selection when hiding
                    const sgCopieSelect = document.getElementById('sg_copie');
                    if (sgCopieSelect) {
                        sgCopieSelect.value = '';
                    }
                }
            }
        });
    }

    // Sort Order Button
    const sortOrderBtn = document.getElementById('sort-order-btn');
    if (sortOrderBtn) {
        sortOrderBtn.addEventListener('click', toggleSortOrder);
    }

    // Delete Buttons
    document.querySelectorAll('.delete-btn').forEach(btn => {
        btn.addEventListener('click', function(e) {
            e.preventDefault(); // Prevent any default action just in case
            const id = this.dataset.id;
            const numero = this.dataset.numero;
            confirmDelete(id, numero);
        });
    });

    // DataTables désactivé volontairement : le filtrage, le tri et la recherche se font
    // côté serveur (formulaire de filtres + boutons de tri + autocomplete). DataTables
    // ajoutait des contrôles redondants (« Show entries », « Showing X of Y ») et son
    // wrapper cassait le défilement horizontal (colonne Actions coupée, scroll de toute
    // la page). Le défilement est désormais contenu au tableau via .gec-table-wrap.

    // Autocomplete pour la recherche
    const searchInput = document.getElementById('search');
    const suggestionsDiv = document.getElementById('searchSuggestions');
    let debounceTimer;

    if (searchInput && suggestionsDiv) {
        searchInput.addEventListener('input', function() {
            clearTimeout(debounceTimer);
            const query = this.value.trim();

            if (query.length < 2) {
                suggestionsDiv.classList.add('hidden');
                return;
            }

            debounceTimer = setTimeout(() => {
                fetch(`/api/search_suggestions?q=${encodeURIComponent(query)}`)
                    .then(response => response.json())
                    .then(suggestions => {
                        if (suggestions.length > 0) {
                            suggestionsDiv.innerHTML = '';
                            suggestions.forEach(suggestion => {
                                const div = document.createElement('div');
                                div.className = 'px-3 py-2 hover:bg-gray-100 cursor-pointer border-b border-gray-200 text-sm';
                                div.textContent = suggestion;
                                div.addEventListener('click', function() {
                                    searchInput.value = suggestion;
                                    suggestionsDiv.classList.add('hidden');
                                    // Soumettre le formulaire automatiquement
                                    searchInput.form.submit();
                                });
                                suggestionsDiv.appendChild(div);
                            });
                            suggestionsDiv.classList.remove('hidden');
                        } else {
                            suggestionsDiv.classList.add('hidden');
                        }
                    })
                    .catch(error => {
                        console.error('Erreur lors de la récupération des suggestions:', error);
                        suggestionsDiv.classList.add('hidden');
                    });
            }, 300); // Délai de 300ms avant d'envoyer la requête
        });

        // Cacher les suggestions quand on clique ailleurs
        document.addEventListener('click', function(event) {
            if (!searchInput.contains(event.target) && !suggestionsDiv.contains(event.target)) {
                suggestionsDiv.classList.add('hidden');
            }
        });

        // Navigation au clavier dans les suggestions
        searchInput.addEventListener('keydown', function(event) {
            const suggestions = suggestionsDiv.querySelectorAll('div');
            const activeSuggestion = suggestionsDiv.querySelector('.bg-gray-100');
            let index = Array.from(suggestions).indexOf(activeSuggestion);

            if (event.key === 'ArrowDown') {
                event.preventDefault();
                if (index < suggestions.length - 1) {
                    if (activeSuggestion) activeSuggestion.classList.remove('bg-gray-100');
                    suggestions[index + 1].classList.add('bg-gray-100');
                }
            } else if (event.key === 'ArrowUp') {
                event.preventDefault();
                if (index > 0) {
                    if (activeSuggestion) activeSuggestion.classList.remove('bg-gray-100');
                    suggestions[index - 1].classList.add('bg-gray-100');
                }
            } else if (event.key === 'Enter' && activeSuggestion) {
                event.preventDefault();
                searchInput.value = activeSuggestion.textContent;
                suggestionsDiv.classList.add('hidden');
                searchInput.form.submit();
            } else if (event.key === 'Escape') {
                suggestionsDiv.classList.add('hidden');
            }
        });
    }
});
