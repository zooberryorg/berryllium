function fileInputProcessor({hasExistingUrl = false} = {}) {
  // note: implicit global vars go here; attach to window object

  return {
    isDragging: false,
    isUploading: false,
    urlFieldEnabled: true,
    fileDropzoneEnabled: true,
    fileCount: 0,
    hasExistingUrl: hasExistingUrl,

    // guarantee form state on page load
    init() {
      // get initial file queue length 
      this.fileCount = this.getFileQueueLength();

      if (this.hasFiles) {
        console.log('files found in queue on init, disabling url field and enabling help');
        this.disableInput(this.$refs.urlBlock, 'urlFieldEnabled');
      }
      if (this.hasExistingUrl) {
        this.disableInput(this.$refs.dropzoneBlock, 'fileDropzoneEnabled');
      }
    },

    // preset help messages for help text component
    get helpMessage() {
      // when files exist and url field disabled
      if (this.hasFiles) {
        return `Files currently added to queue. If you wish to add an external URL instead, remove all files from the queue first.`;
      }
      // when url exists and file dropzone disabled
      if (this.hasExistingUrl) {
        return `URL field is currently populated. If you wish to add files instead, clear the URL field first.`;
      }
      return '';
    },

    get showHelp() {
        console.log('checking showHelp condition with fileCount:', this.fileCount, 'hasExistingUrl:', this.hasExistingUrl);
        
        if (this.hasFiles || this.hasExistingUrl) {
          console.log('showHelp condition met, showing help text');
          this.$refs.helpText.classList.remove('hidden');
        } else {
          console.log('showHelp condition not met, hiding help text');
          this.$refs.helpText.classList.add('hidden');
        }
        return this.hasFiles || this.hasExistingUrl;
    },

    get hasFiles() {
      return this.fileCount > 0;
    },

    onUrlFieldInput() {
      if (this.getUrlFieldLength() > 0) {
        this.disableInput(this.$refs.dropzoneBlock, 'fileDropzoneEnabled');
        this.hasExistingUrl = true;
      } else {
        console.log('url field cleared, enabling dropzone and hiding help');
        this.enableInput(this.$refs.dropzoneBlock, 'fileDropzoneEnabled');
        this.hasExistingUrl = false;
      }
    },

    getUrlFieldLength() {
      if (!this.$refs.urlInput) return 0;
      return this.$refs.urlInput.value.length;
    },

    updateQueueState() {
      this.fileCount--;
      if (this.hasFiles) {
        this.$refs.fileQueue.remove();
      }
      console.log('CURRENT TIME:', new Date().toLocaleTimeString());
      console.log('updated queue state, fileCount:', this.fileCount);
    },

    getFileQueueLength() {
      const fileQueue = document.querySelectorAll('[data-file]');
      return fileQueue.length;
    },

    enableInput(ref, flag) {
      this[flag] = true;
      ref.classList.remove('pointer-events-none', `opacity-20`);
    },

    disableInput(ref, flag) {
      this[flag] = false;
      ref.classList.add('pointer-events-none', `opacity-20`);
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
