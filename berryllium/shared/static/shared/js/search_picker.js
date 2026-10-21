function searchPicker(config) {
  return {
    name: config.name,
    searchUrl: config.searchUrl,
    items: config.items || [],
    title: config.title || 'Search',
    placeholder: config.placeholder || 'Search...',
    allowCreate: !!config.allowCreate,
    emptyText: config.emptyText || 'No results.',
    insertLabel: config.insertLabel || 'Insert',

    open: false,
    query: '',
    results: [],
    staged: [],     // picked in the dialog, not inserted yet
    loading: false,
    error: '',
    _requestId: 0,

    // ---- dialog

    openPicker() {
      this.open = true;
      this.query = '';
      this.staged = [];
      this.error = '';
      this.search();
      this.$nextTick(() => this.$refs.searchInput?.focus());
    },

    close() {
      this.open = false;
    },

    async search() {
      const requestId = ++this._requestId; // ignore responses that arrive out of order
      this.loading = true;
      this.error = '';
      try {
        const separator = this.searchUrl.includes('?') ? '&' : '?';
        const url = `${this.searchUrl}${separator}q=${encodeURIComponent(this.query.trim())}`;
        const response = await fetch(url, { headers: { Accept: 'application/json' } });
        if (!response.ok) throw new Error();
        const data = await response.json();
        if (requestId === this._requestId) this.results = data.results || [];
      } catch {
        if (requestId === this._requestId) {
          this.results = [];
          this.error = 'Search failed. Try again.';
        }
      } finally {
        if (requestId === this._requestId) this.loading = false;
      }
    },

    // ---- selection

    isInserted(value) {
      return this.items.some((item) => item.value === value);
    },

    isStaged(value) {
      return this.staged.some((item) => item.value === value);
    },

    toggle(result) {
      if (this.isInserted(result.value)) return;
      if (this.isStaged(result.value)) {
        this.staged = this.staged.filter((item) => item.value !== result.value);
      } else {
        this.staged.push(result);
      }
    },

    get canCreate() {
      const name = this.query.trim();
      if (!this.allowCreate || !name) return false;
      const lower = name.toLowerCase();
      return ![...this.results, ...this.items, ...this.staged].some(
        (item) => item.label.toLowerCase() === lower
      );
    },

    stageNew() {
      const name = this.query.trim().replace(/\s+/g, ' ');
      if (!name) return;
      this.staged.push({
        value: `new:${name}`,
        label: name,
        sublabel: 'New, added when the mod is published',
        isNew: true,
      });
      this.query = '';
      this.search();
    },

    onEnter() {
      if (this.canCreate) this.stageNew();
    },

    insert() {
      for (const item of this.staged) {
        if (!this.isInserted(item.value)) this.items.push(item);
      }
      this.staged = [];
      this.close();
    },

    remove(value) {
      this.items = this.items.filter((item) => item.locked || item.value !== value);
    },

  };
}

