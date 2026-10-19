/**
 * Markdown editor for the mod description step.
 *
 * Usage:
 *   <div x-data="markdownEditor($el.dataset)"
 *        data-upload-url="..." data-preview-url="...">
 *     <div x-ref="editor"> <textarea>...</textarea> </div>
 *     <div x-ref="preview"></div>
 *     <input type="file" x-ref="imageInput" @change="uploadImage($event)">
 *   </div>
 */
function markdownEditor({ uploadUrl, previewUrl }) {
  return {
    showPreview: false,
    uploading: false,
    uploadError: '',

    get textarea() {
      return this.$refs.editor.querySelector('textarea');
    },

    csrfToken() {
      const input = this.$root.closest('form')?.querySelector('[name=csrfmiddlewaretoken]');
      return input ? input.value : '';
    },

    /**
     * Replaces current selection with given text.
     * Uses execCommand so Ctrl+Z still works; falls back to setRangeText.
     */
    insert(text, selectStart = null, selectEnd = null) {
      const ta = this.textarea;
      ta.focus();
      const start = ta.selectionStart;
      if (!document.execCommand('insertText', false, text)) {
        ta.setRangeText(text, ta.selectionStart, ta.selectionEnd, 'end');
        ta.dispatchEvent(new Event('input', { bubbles: true }));
      }
      if (selectStart !== null) {
        ta.setSelectionRange(start + selectStart, start + (selectEnd ?? selectStart));
      }
    },

    wrap(before, after = before, placeholder = 'text') {
      const ta = this.textarea;
      const s = ta.selectionStart;
      const e = ta.selectionEnd;
      const selected = ta.value.slice(s, e);

      const alreadyWrapped =
        selected &&
        ta.value.slice(s - before.length, s) === before &&
        ta.value.slice(e, e + after.length) === after;

      if (alreadyWrapped) {
        ta.setSelectionRange(s - before.length, e + after.length);
        this.insert(selected, 0, selected.length);
        return;
      }

      const inner = selected || placeholder;
      this.insert(before + inner + after, before.length, before.length + inner.length);
    },

    // Headings, lists, quotes: add a prefix to every selected line.
    prefixLines(prefix) {
      const ta = this.textarea;
      const value = ta.value;
      const lineStart = value.lastIndexOf('\n', ta.selectionStart - 1) + 1;
      let lineEnd = value.indexOf('\n', ta.selectionEnd);
      if (lineEnd === -1) lineEnd = value.length;

      const numbered = prefix === '1. ';
      const lines = value.slice(lineStart, lineEnd).split('\n');
      const result = lines.map((line, i) => (numbered ? `${i + 1}. ` : prefix) + line).join('\n');

      ta.setSelectionRange(lineStart, lineEnd);
      this.insert(result, 0, result.length);
    },

    link() {
      const ta = this.textarea;
      const label = ta.value.slice(ta.selectionStart, ta.selectionEnd) || 'link text';
      const text = `[${label}](https://)`;
      // select "https://" so typing replaces it with the real URL
      this.insert(text, label.length + 3, text.length - 1);
    },

    codeBlock() {
      this.wrap('\n```\n', '\n```\n', 'code');
    },

    pickImage() {
      this.uploadError = '';
      this.$refs.imageInput.click();
    },

    async uploadImage(event) {
      const file = event.target.files[0];
      event.target.value = ''; // duplicate files should be allowed
      if (!file) return;

      // remember the cursor pos
      const ta = this.textarea;
      const cursor = { start: ta.selectionStart, end: ta.selectionEnd };

      this.uploading = true;
      this.uploadError = '';
      try {
        const body = new FormData();
        body.append('image', file);
        const response = await fetch(uploadUrl, {
          method: 'POST',
          body,
          headers: { 'X-CSRFToken': this.csrfToken() },
        });
        const data = await response.json().catch(() => ({}));
        if (!response.ok) throw new Error(data.error || 'Upload failed.');

        const alt = file.name.replace(/\.[^.]+$/, '').replace(/[\[\]]/g, '');
        ta.setSelectionRange(cursor.start, cursor.end);
        this.insert(`![${alt}](${data.url})`);
      } catch (err) {
        this.uploadError = err.message;
      } finally {
        this.uploading = false;
      }
    },

    async togglePreview() {
      this.showPreview = !this.showPreview;
      if (!this.showPreview) {
        this.$nextTick(() => this.textarea.focus());
        return;
      }

      const preview = this.$refs.preview;
      preview.innerHTML = '<p class="opacity-60">Loading preview…</p>';
      try {
        const body = new FormData();
        body.append('description', this.textarea.value);
        const response = await fetch(previewUrl, {
          method: 'POST',
          body,
          headers: { 'X-CSRFToken': this.csrfToken() },
        });
        if (!response.ok) throw new Error();
        // safe: the server returns HTML that has already been sanitized
        preview.innerHTML = await response.text();
      } catch {
        preview.innerHTML = '<p class="text-red-400">Could not load the preview.</p>';
      }
    },
  };
}