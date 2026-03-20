function navigationState({currentIndex = 1} = {}) {
    return {
        currentIndex: currentIndex,
        updateNavigation() {
        const navLinks = document.querySelectorAll('[x-ref^="navLink-"]');
            navLinks.forEach((link, idx) => {
                if (idx == this.currentIndex ) {
                    link.classList.add(
                        'text-white', 
                        'bg-gradient-to-r', 
                        'from-gold-500/50', 
                        'to-gold-300/50', 
                        'border-gold-300/30');
                } else {
                    link.classList.remove(
                        'text-white', 
                        'bg-gradient-to-r', 
                        'from-gold-500/50', 
                        'to-gold-300/50', 
                        'border-gold-300/30');
                }
        });
        }
    }
}
