function autosaveForm({ interval = 2000 } = {}) {
  return {
    status: 'saved', // saved | dirty | saving | error
    errorText: '',
    lastSaved: '',
    saving: false,
    _timer: null,
    _onConfirm: null,

    init() {
      // let Alpine fill in widget hidden inputs before taking the first snapshot
      this.$nextTick(() => {
        this.lastSaved = this.snapshot();
      });
      this._timer = setInterval(() => this.tick(), interval);
      this._onConfirm = (event) => this.saveBeforeLeaving(event);
      document.addEventListener('htmx:confirm', this._onConfirm);
    },

    destroy() {
      clearInterval(this._timer);
      document.removeEventListener('htmx:confirm', this._onConfirm);
    },

    snapshot() {
      const data = new FormData(this.$root);
      data.delete('csrfmiddlewaretoken');
      data.delete('action');
      return new URLSearchParams(data).toString();
    },

    get statusText() {
      return {
        saved: 'All changes saved',
        dirty: 'Unsaved changes',
        saving: 'Saving…',
        error: this.errorText || 'Not saved',
      }[this.status];
    },

    get statusClass() {
      return this.status === 'error' ? 'text-red-400' : 'text-white/40';
    },

    async tick() {
      if (this.saving || !document.body.contains(this.$root)) return;
      const current = this.snapshot();
      if (current === this.lastSaved) return;
      await this.save(current);
    },

    async save(current = this.snapshot()) {
      this.saving = true;
      this.status = 'saving';
      const data = new FormData(this.$root);
      data.set('action', 'autosave');
      try {
        const response = await fetch(this.$root.dataset.autosaveUrl || this.$root.getAttribute('hx-post'), {
          method: 'POST',
          body: data,
          headers: { 'X-CSRFToken': data.get('csrfmiddlewaretoken') || '' },
        });
        const result = await response.json();
        this.lastSaved = current;
        if (result.saved) {
          this.status = 'saved';
          this.errorText = '';
        } else {
          this.status = 'error';
          this.errorText = `Not saved: ${(result.errors || [])[0] || 'fix the highlighted fields'}`;
        }
      } catch {
        this.status = 'error';
        this.errorText = 'Not saved: check your connection.';
      } finally {
        this.saving = false;
      }
    },

    // before navigating away from the page, if this form has unsaved changes, save them first
    saveBeforeLeaving(event) {
      const source = event.detail.elt;
      if (!document.body.contains(this.$root)) return;
      if (this.$root.contains(source)) return;
      if (this.snapshot() === this.lastSaved) return;
      event.preventDefault();
      this.save().finally(() => event.detail.issueRequest(true));
    },
  };
}
