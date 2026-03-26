function fileInputProcessor() {
  // note: implicit global vars go here; attach to window object

  return {
    isDragging: false,
    isUploading: false,
    fileDropzoneEnabled: true,

    enableInput(ref, flag) {
      this[flag] = true;
      ref.classList.remove('pointer-events-none', `opacity-50`);
      ref.querySelectorAll('input, textarea, button, select').forEach(el => el.disabled = false);
    },

    disableInput(ref, flag) {
      this[flag] = false;
      ref.classList.add('pointer-events-none', `opacity-50`);
      ref.querySelectorAll('input, textarea, button, select').forEach(el => el.disabled = true);
    },
    
    handleFileSelect(event) {
      const file = event.target.files[0];
      if (file) {
        // Click the hidden submit button to trigger htmx
        this.$refs.submitBtn.click();
      }
    },
    
    handleDrop(event) {
      this.isDragging = false;
      const file = event.dataTransfer.files[0];
      if (file) {
        // Set the file to the input
        const dt = new DataTransfer();
        dt.items.add(file);
        this.$refs.fileInput.files = dt.files;
        // Click the hidden submit button
        this.$refs.submitBtn.click();
      }
    }
  }
}
