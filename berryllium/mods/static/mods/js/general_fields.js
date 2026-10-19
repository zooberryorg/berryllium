// Format date as "YYYY-MM-DDTHH:MM" string a datetime-local
function toDatetimeLocal(date) {
  const local = new Date(date.getTime() - date.getTimezoneOffset() * 60000);
  return local.toISOString().slice(0, 16);
}

function publishDatePicker() {
  return {
    local: '',
    timeZone: Intl.DateTimeFormat().resolvedOptions().timeZone,

    init() {
      const iso = this.$refs.publishValue.value;
      const parsed = iso ? new Date(iso) : new Date();
      this.local = toDatetimeLocal(isNaN(parsed) ? new Date() : parsed);
      this.sync();
    },

    sync() {
      if (this.local) {
        this.$refs.publishValue.value = new Date(this.local).toISOString();
      }
    },

    setNow() {
      this.local = toDatetimeLocal(new Date());
      this.sync();
    },
  };
}

//thumbnail picker with a square, cropped live preview.
function thumbnailPicker({ initialUrl = '' }) {
  return {
    previewUrl: initialUrl,
    fileName: '',

    preview(event) {
      const file = event.target.files[0];
      if (!file) return;
      this.fileName = file.name;
      if (this.previewUrl && this.previewUrl.startsWith('blob:')) {
        URL.revokeObjectURL(this.previewUrl);
      }
      this.previewUrl = URL.createObjectURL(file);
    },
  };
}