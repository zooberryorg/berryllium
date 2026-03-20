function navigationState({currentIndex = 1} = {}) {
    return {
        currentIndex: currentIndex,
        linkClasses: [
            'text-white', 
            'bg-gradient-to-r', 
            'from-gold-500/50', 
            'to-gold-300/50', 
            'border-gold-300/30'
        ],
        iconActiveClass: 'text-gold-300',
        iconInactiveClass: 'text-gray-400',
        linkActiveBgClass: 'bg-gold-400/20',
        linkInactiveBgClass: 'bg-transparent',
        updateNavigation() {

        const navLinks = document.querySelectorAll('[x-ref^="navLink-"]');
            navLinks.forEach((link, idx) => {
                if (idx == this.currentIndex ) {
                    // update link bg and text color
                    link.classList.add(...this.linkClasses);
                    // update inner div icon bg
                    const innerDiv = link.querySelector('div');
                    if (innerDiv) {
                        innerDiv.classList.remove(this.linkInactiveBgClass);
                        innerDiv.classList.add(this.linkActiveBgClass);
                        // update icon color
                        const icon = innerDiv.querySelector('i');
                        if (icon) {
                            icon.classList.remove(this.iconInactiveClass);
                            icon.classList.add(this.iconActiveClass);
                        }
                    }
                } else {
                    link.classList.remove(...this.linkClasses);

                    const innerDiv = link.querySelector('div');
                    if (innerDiv) {
                        innerDiv.classList.remove(this.linkActiveBgClass);
                        const icon = innerDiv.querySelector('i');
                        if (icon) {
                            icon.classList.add(this.iconInactiveClass);
                            icon.classList.remove(this.iconActiveClass);
                        }
                    }
                }
        });
        }
    }
}
