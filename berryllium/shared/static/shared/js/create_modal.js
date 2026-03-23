function createModal() {
    return {
        // modal closed by default
        isOpen: false,
        modalTitle: "Modal Title",
        form: "",

        openModal(detail = {}) {
            this.isOpen = true;
            this.form = detail.form || "";
            this.modalTitle = detail.title || "Modal Title";

            // HTMX for form content
            setTimeout(() => {
                const modalContent = document.getElementById('modal-content');
                if (modalContent) {
                    htmx.trigger(modalContent, 'load-form', { form: this.form });
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