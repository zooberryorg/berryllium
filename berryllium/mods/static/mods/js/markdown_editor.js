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

  };
}