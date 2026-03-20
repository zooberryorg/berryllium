function navigationState({currentIndex = 1} = {}) {
    return {
        currentIndex: currentIndex,
        updateNavigation() {
        const navLinks = document.querySelectorAll('[x-ref^="navLink-"]');
            navLinks.forEach((link, idx) => {
                console.log(`Updating nav link ${idx + 1}: currentIndex=${this.currentIndex}: text=${link.textContent.trim()}`);
            if (idx == this.currentIndex ) {
                link.classList.add('bg-pine-300', 'text-pine-900');
            } else {
                link.classList.remove('bg-pine-300', 'text-pine-900');
            }
        });
        }
    }
}
