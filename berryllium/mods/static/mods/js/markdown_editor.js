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

}