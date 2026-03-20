function navigationState({currentIndex = 1} = {}) {
    return {
        currentIndex: currentIndex,
        updateNavigation() {
        const navLinks = document.querySelectorAll('[x-ref^="navLink-"]');
            navLinks.forEach((link, idx) => {
            if (idx < this.currentIndex) {
                link.classList.add('bg-gold-400/30', 'text-white', 'border-gold-300/30');
            } else {
                link.classList.remove('bg-gold-400/30', 'text-white', 'border-gold-300/30');
                link.classList.add('text-gray-400', 'hover:bg-gradient-to-r', 'hover:from-gold-500/50', 'hover:to-gold-300/50');
            }
            });
        }
    }
}
