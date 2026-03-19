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
      window.addEventListener('htmx:afterSwap', () => {
        this.$nextTick(() => {
          this.hasExistingFiles = this.getFileQueueLength() > 0;
        });
      });

      if (this.hasExistingFiles) {
        console.log('files found in queue on init, disabling url field and enabling help');
        this.disableInput(this.$refs.urlBlock, 'urlFieldEnabled');
        this.showHelp();
      }
      if (this.hasExistingUrl) {
        this.disableInput(this.$refs.dropzoneBlock, 'fileDropzoneEnabled');
        this.showHelp();
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

    showHelp() {
      this.$refs.helpText.classList.remove('hidden');
    },  

    forceDisableHelp() {
      this.$refs.helpText.classList.add('hidden');
    },

    onUrlFieldInput() {
      if (this.getUrlFieldLength() > 0) {
        this.disableInput(this.$refs.dropzoneBlock, 'fileDropzoneEnabled');
        this.hasExistingUrl = true;
        this.showHelp();
      } else {
        console.log('url field cleared, enabling dropzone and hiding help');
        this.enableInput(this.$refs.dropzoneBlock, 'fileDropzoneEnabled');
        this.hasExistingUrl = false;
        this.forceDisableHelp();
      }
    },

    getUrlFieldLength() {
      if (!this.$refs.urlInput) return 0;
      return this.$refs.urlInput.value.length;
    },

    getFileQueueLength() {
      const fileQueue = this.$el.querySelectorAll('[data-file]');
      console.log('checking file queue length, found:', fileQueue.length);
      if (fileQueue.length > 0) {
        console.log('in getFileQueueLength, found file queue and enabling help');
        this.showHelp();
      }

      return fileQueue ? fileQueue.length : 0;
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
