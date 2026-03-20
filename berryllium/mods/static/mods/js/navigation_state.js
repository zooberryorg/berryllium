function navigationState({currentIndex = 1} = {}) {
    return {
        currentIndex: currentIndex,
        updateNavigation() {
        const navLinks = document.querySelectorAll('[x-ref^="navLink-"]');
            navLinks.forEach((link, idx) => {
            if (idx == this.currentIndex - 1) {
                link.classList.add('bg-pine-300', 'text-pine-900');
                link.classList.remove('bg-pine-600', 'text-pine-300');
            } else {
                link.classList.remove('bg-pine-300', 'text-pine-900');
                link.classList.add('bg-pine-600', 'text-pine-300');
            }
            });
        }
    }
}
