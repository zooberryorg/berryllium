function fileInputProcessor(hasExistingFiles = false, hasExistingUrl = false) {
  // note: implicit global vars go here; attach to window object

  return {
    isDragging: false,
    isUploading: false,
    urlFieldEnabled: true,
    fileDropzoneEnabled: true,
    hasExistingFiles: hasExistingFiles,
    hasExistingUrl: hasExistingUrl,

    get helpMessage() {
      // when files exist and url field disabled
      if (this.hasExistingFiles && !this.urlFieldEnabled) {
        return `Files currently added to queue. If you wish to add a URL instead, remove all files from the queue first.`;
      }
      // when url exists and file dropzone disabled
      if (this.hasExistingUrl && !this.fileDropzoneEnabled) {
        return `URL field is currently populated. If you wish to add files instead, clear the URL field first.`;
      }
      return '';
    },

    init() {
      if (this.hasExistingFiles) {
        this.disableInput(this.$refs.urlBlock, 'urlFieldEnabled');
        this.showComponent(this.$refs.helpText);
      }
      if (this.hasExistingUrl) {
        this.disableInput(this.$refs.dropzoneBlock, 'fileDropzoneEnabled');
        this.showComponent(this.$refs.helpText);
      }
    },

    getUrlFieldLength() {
      if (!this.$refs.urlInput) return 0;
      return this.$refs.urlInput.value.length;
    },

    getFileQueueLength() {
      if (!this.$refs.fileInput) return 0;
      return this.$refs.fileInput.files.length;
    },

    enableInput(ref, flag) {
      this[flag] = true;
      ref.classList.remove('pointer-events-none', `opacity-20`);
    },

    disableInput(ref, flag) {
      this[flag] = false;
      ref.classList.add('pointer-events-none', `opacity-20`);
    },

    showComponent(ref) {
      ref.classList.remove('hidden');
    },

    hideComponent(ref) {
      ref.classList.add('hidden');
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
