function dropdown() {
  return {
    open: false,
    value: '',
    active: 0,
    options: [],

    init() {
      this.value = this.$refs.input.value;
      this.options = [...this.$refs.list.querySelectorAll('[role="option"]')].map((el) => ({
        value: el.dataset.value,
        label: el.dataset.label,
      }));
    },

    get currentLabel() {
      const option = this.options.find((o) => o.value === this.value) || this.options[0];
      return option ? option.label : '';
    },

    isSelected(el) {
      return el.dataset.value === this.value;
    },

    optionId(index) {
      return `${this.$id('dropdown')}-option-${index}`;
    },

    openMenu() {
      this.open = true;
      this.active = Math.max(0, this.options.findIndex((o) => o.value === this.value));
      this.$nextTick(() => {
        this.$refs.list.focus();
        this.scrollToActive();
      });
    },

    close(focusButton = false) {
      if (!this.open) return;
      this.open = false;
      if (focusButton) this.$refs.button.focus();
    },

    toggle() {
      this.open ? this.close() : this.openMenu();
    },

    move(step) {
      const count = this.options.length;
      this.active = (this.active + step + count) % count;
      this.scrollToActive();
    },

    moveTo(index) {
      this.active = index;
      this.scrollToActive();
    },

    scrollToActive() {
      this.$nextTick(() => this.$refs.list.children[this.active]?.scrollIntoView({ block: 'nearest' }));
    },

    choose(index) {
      const option = this.options[index];
      this.close(true);
      if (!option || option.value === this.value) return;
      this.setValue(option.value);
    },

    setValue(value) {
      this.value = value;
      this.$refs.input.value = value;
      this.$refs.input.dispatchEvent(new Event('change', { bubbles: true }));
    },

    clearFilter({ name = '' } = {}) {
      const input = this.$refs.input;
      if (name ? name !== input.name : input.dataset.clearable !== 'true') return;
      if (this.value !== '') this.setValue('');
    },
  };
}
