function fileInputProcessor() {
  // note: implicit global vars go here; attach to window object

  return {
    isDragging: false,
    isUploading: false,
    fileCount: 0,
    urlFieldEnabled: true,
    fileDropzoneEnabled: true,

    getUrlFieldLength() {
      if (!this.$refs.urlInput) return 0;
      return this.$refs.urlInput.value.length;
    },

    getFileQueueLength(ref) {
      if (!this.$refs.fileInput) return 0;
      return this.$refs.fileInput.files.length;
    },

    enableInput(ref, flag) {
      flag = !flag;
      ref.classList.remove('pointer-events-none', `opacity-20`);
    },

    disableInput(ref, flag) {
      flag = !flag;
      ref.classList.add('pointer-events-none', `opacity-20`);
    },
    
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
