function fileInputProcessor({hasExistingFiles = false, hasExistingUrl = false} = {}) {
  // note: implicit global vars go here; attach to window object

  return {
    isDragging: false,
    isUploading: false,
    urlFieldEnabled: true,
    fileDropzoneEnabled: true,
    hasExistingFiles: hasExistingFiles,
    hasExistingUrl: hasExistingUrl,

    // guarantee form state on page load
    init() {
      // event listener for file input changes to guarantee state is updated
      this.$el.addEventListener('htmx:afterRequest', () => {
        console.log('htmx request completed, checking file queue length...');
        this.hasExistingFiles = this.getFileQueueLength() > 0;
        console.log('Updated hasExistingFiles:', this.hasExistingFiles);
      });

      console.log('Initializing file input processor with existing files:', this.hasExistingFiles, 'and existing URL:', this.hasExistingUrl);
      if (this.hasExistingFiles) {
        this.disableInput(this.$refs.urlBlock, 'urlFieldEnabled');
      }
      if (this.hasExistingUrl) {
        this.disableInput(this.$refs.dropzoneBlock, 'fileDropzoneEnabled');
      }
    },

    // preset help messages for help text component
    get helpMessage() {
      // when files exist and url field disabled
      if (this.hasExistingFiles) {
        return `Files currently added to queue. If you wish to add an external URL instead, remove all files from the queue first.`;
      }
      // when url exists and file dropzone disabled
      if (this.hasExistingUrl) {
        return `URL field is currently populated. If you wish to add files instead, clear the URL field first.`;
      }
      return '';
    },

    get showHelp() {
      console.log('Existing files:', this.hasExistingFiles, 'Existing URL:', this.hasExistingUrl);
      console.log('Current showHelp:', !!(this.hasExistingFiles || this.hasExistingUrl));
      return !!(this.hasExistingFiles || this.hasExistingUrl);
    },  

    onUrlFieldInput() {
      console.log(this.getUrlFieldLength());
      if (this.getUrlFieldLength() > 0) {
        this.disableInput(this.$refs.dropzoneBlock, 'fileDropzoneEnabled');
        this.hasExistingUrl = true;
      } else if (this.getUrlFieldLength() === 0 && !this.hasExistingFiles) {
        this.enableInput(this.$refs.dropzoneBlock, 'fileDropzoneEnabled');
        this.hasExistingUrl = false;
      }
      console.log('Existing files:', this.hasExistingFiles, 'Existing URL:', this.hasExistingUrl);
    },

    getUrlFieldLength() {
      if (!this.$refs.urlInput) return 0;
      return this.$refs.urlInput.value.length;
    },

    getFileQueueLength() {
      const fileQueue = this.$el.querySelectorAll('[data-file]');
      return fileQueue ? fileQueue.length : 0;
    },

    enableInput(ref, flag) {
      this[flag] = true;
      console.log(`Enabling input for ${flag}`);
      ref.classList.remove('pointer-events-none', `opacity-20`);
    },

    disableInput(ref, flag) {
      this[flag] = false;
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
