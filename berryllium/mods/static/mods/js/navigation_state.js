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

        updateIcon(link, {oldBg, newBg, oldIcon, newIcon}) {
            // update inner div icon bg
            const innerDiv = link.querySelector('div');
            if (innerDiv) {
                innerDiv.classList.remove(oldBg);
                innerDiv.classList.add(newBg);
                // update icon color
                const icon = innerDiv.querySelector('i');
                if (icon) {
                    icon.classList.add(newIcon);
                    icon.classList.remove(oldIcon);
                }
            }
        },

        updateNavigation() {
            const navLinks = document.querySelectorAll('[data-nav-link]');
            navLinks.forEach((link, idx) => {
                if (idx === this.currentIndex ) {
                    // update link bg and text color
                    link.classList.add(...this.linkClasses);
                    this.updateIcon(link, {
                        oldBg: this.linkInactiveBgClass,
                        newBg: this.linkActiveBgClass,
                        oldIcon: this.iconInactiveClass,
                        newIcon: this.iconActiveClass
                    });
                } else {
                    link.classList.remove(...this.linkClasses);
                    this.updateIcon(link, {
                        oldBg: this.linkActiveBgClass,
                        newBg: this.linkInactiveBgClass,
                        oldIcon: this.iconActiveClass,
                        newIcon: this.iconInactiveClass
                    });

                }
            });
        }
    }
}
