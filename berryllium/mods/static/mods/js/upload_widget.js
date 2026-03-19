function fileInputProcessor() {
  // note: implicit global vars go here; attach to window object

  return {
    isDragging: false,
    isUploading: false,
    disableOpacityLevel: 20,

    getUrlFieldLength() {
      if (!this.$refs.urlInput) return 0;
      return this.$refs.urlInput.value.length;
    },

    enableInput(ref) {
      ref.classList.remove('pointer-events-none', `opacity-${this.disableOpacityLevel}`);
    },

    disableInput(ref) {
      ref.classList.add('pointer-events-none', `opacity-${this.disableOpacityLevel}`);
    }
    
    handleFileSelect(event) {
      const file = event.target.files[0];
      if (file) {
        console.log('File selected:', file.name, file.size);
        // Click the hidden submit button to trigger htmx
        this.$refs.submitBtn.click();
      }
    },
    
    handleDrop(event) {
      this.isDragging = false;
      const file = event.dataTransfer.files[0];
      if (file) {
        console.log('File dropped:', file.name, file.size);
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
