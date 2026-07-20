document.addEventListener('DOMContentLoaded', function() {
    console.log('GEC Application Initialized');

    // Variables globales pour le menu
    let menuOverlay = null;
    let isMenuOpen = false;

    const mobileMenuButton = document.getElementById('mobile-menu-button');
    const mobileMenu = document.getElementById('mobile-menu');

    console.log('Menu elements:', { button: !!mobileMenuButton, menu: !!mobileMenu });

    function openMenu() {
        if (!mobileMenu || isMenuOpen) return;

        console.log('Opening menu');
        isMenuOpen = true;

        // Create overlay
        if (!menuOverlay) {
            menuOverlay = document.createElement('div');
            menuOverlay.style.cssText = 'position: fixed; top: 0; left: 0; width: 100%; height: 100%; background: rgba(0,0,0,0.5); z-index: 999; display: none;';
            document.body.appendChild(menuOverlay);

            menuOverlay.addEventListener('click', closeMenu);
        }

        // Show overlay and prevent body scroll
        menuOverlay.style.display = 'block';
        document.body.style.overflow = 'hidden';

        // Animate menu in
        mobileMenu.style.right = '0px';

        // Change icon to X
        const icon = mobileMenuButton?.querySelector('i');
        if (icon) icon.className = 'fas fa-times';
    }

    function closeMenu() {
        if (!mobileMenu || !isMenuOpen) return;

        console.log('Closing menu');
        isMenuOpen = false;

        // Animate menu out
        mobileMenu.style.right = '-320px';

        // Change icon back to hamburger
        const icon = mobileMenuButton?.querySelector('i');
        if (icon) icon.className = 'fas fa-bars';

        // Hide overlay and restore body scroll after animation
        setTimeout(() => {
            if (menuOverlay) menuOverlay.style.display = 'none';
            document.body.style.overflow = '';
        }, 300);
    }

    // Button click handler
    if (mobileMenuButton) {
        mobileMenuButton.addEventListener('click', function(e) {
            e.preventDefault();
            e.stopPropagation();
            console.log('Menu button clicked, current state:', isMenuOpen ? 'open' : 'closed');

            if (isMenuOpen) {
                closeMenu();
            } else {
                openMenu();
            }
        });
    }

    // Close menu when clicking links
    if (mobileMenu) {
        const menuLinks = mobileMenu.querySelectorAll('a');
        menuLinks.forEach(link => {
            link.addEventListener('click', function() {
                console.log('Menu link clicked:', this.href);
                closeMenu();
            });
        });
    }

    // Close menu with Escape key
    document.addEventListener('keydown', function(e) {
        if (e.key === 'Escape' && isMenuOpen) {
            closeMenu();
        }
    });

    // User dropdown functionality
    const userMenuButton = document.getElementById('user-menu');
    const userDropdown = document.getElementById('user-dropdown');
    let isUserDropdownOpen = false;

    if (userMenuButton && userDropdown) {
        userMenuButton.addEventListener('click', function(e) {
            e.preventDefault();
            e.stopPropagation();

            if (isUserDropdownOpen) {
                userDropdown.classList.add('hidden');
                isUserDropdownOpen = false;
            } else {
                userDropdown.classList.remove('hidden');
                isUserDropdownOpen = true;
            }
        });

        // Close dropdown when clicking outside
        document.addEventListener('click', function() {
            if (isUserDropdownOpen) {
                userDropdown.classList.add('hidden');
                isUserDropdownOpen = false;
            }
        });

        // Prevent dropdown from closing when clicking inside it
        userDropdown.addEventListener('click', function(e) {
            e.stopPropagation();
        });

        // Close dropdown with Escape key
        document.addEventListener('keydown', function(e) {
            if (e.key === 'Escape' && isUserDropdownOpen) {
                userDropdown.classList.add('hidden');
                isUserDropdownOpen = false;
            }
        });
    }

    // Logo error handling
    const logoImgs = document.querySelectorAll('.logo-img');
    logoImgs.forEach(img => {
        img.addEventListener('error', function() {
            this.style.display = 'none';
            if (this.nextElementSibling && this.nextElementSibling.classList.contains('logo-fallback')) {
                this.nextElementSibling.style.display = '';
            }
        });
    });
});

// ─────────────────────────────────────────────────────────────────────────────
// Reconnexion après timeout : intercepteur fetch global.
// Si une requête AJAX échoue parce que la session a expiré (le serveur renvoie
// 401 { error: 'session_expired' }), on prévient l'utilisateur et on le redirige
// proprement vers /login — au lieu de laisser l'UI casser silencieusement
// (un fetch recevant une page HTML de login au lieu du JSON attendu).
(function () {
    if (!window.fetch || window.__gecFetchPatched) return;
    window.__gecFetchPatched = true;
    var _fetch = window.fetch;
    var _redirecting = false;
    window.fetch = function () {
        return _fetch.apply(this, arguments).then(function (response) {
            try {
                if (response && response.status === 401) {
                    var ct = response.headers.get('content-type') || '';
                    if (ct.indexOf('application/json') !== -1) {
                        response.clone().json().then(function (data) {
                            if (data && data.error === 'session_expired' && !_redirecting) {
                                _redirecting = true;
                                alert(data.message || 'Votre session a expiré. Veuillez vous reconnecter.');
                                window.location.href = data.login_url || '/login';
                            }
                        }).catch(function () {});
                    }
                }
            } catch (e) { /* ne jamais casser la chaîne fetch */ }
            return response;
        });
    };
})();
