function createModal() {
    return {
        // modal closed by default
        isOpen: false,
        modalTitle: "Modal Title",
        endpoint: "",

        openModal(detail = {}) {
            this.isOpen = true;
            this.endpoint = detail.endpoint || "";
            this.modalTitle = detail.title || "Modal Title";

            // HTMX for form content
            setTimeout(() => {
                const modalContent = document.getElementById('modal-content');
                if (modalContent) {
                    htmx.ajax('GET', this.endpoint, { target: '#modal-content', swap: 'innerHTML' });
                }
            }, 100);
        },

        closeModal() {
            this.isOpen = false;
            // clear modal content
            const contentDiv = document.getElementById('modal-content');
            if (contentDiv) {
                contentDiv.innerHTML = '<div class="text-white/70">Loading...</div>';
            }
        }
    }
}