let listWidgetUid = 0;
function nextRowUid() {
  listWidgetUid += 1;
  return `row-${listWidgetUid}`;
}

// copy properties including getters
function extendComponent(base, extra) {
  const result = {};
  Object.defineProperties(result, Object.getOwnPropertyDescriptors(base));
  Object.defineProperties(result, Object.getOwnPropertyDescriptors(extra));
  return result;
}

function withoutUid(rows) {
  return rows.map(({ uid, ...rest }) => rest);
}

// config ontop of searchPicker. What this does is
// it adds a context field for each inserted search result and lets
// user add a new row not in db
function detailPicker(config) {
  return extendComponent(searchPicker(config), {
    newRow: config.newRow || {},
    insertKind: config.insertKind || null,
    allowExternal: !!config.allowExternal,
    externalLabel: config.externalLabel || 'Add manually',
    contextLabel: config.contextLabel || 'Context',
    contextPlaceholder: config.contextPlaceholder || '',
    showVersion: !!config.showVersion,

    init() {
      this.items = (this.items || []).map((row) => ({ uid: nextRowUid(), ...row }));
    },

    insert() {
      for (const result of this.staged) {
        if (this.isInserted(result.value)) continue;
        const row = { uid: nextRowUid(), ...this.newRow, ...result };
        if (this.insertKind) row.kind = this.insertKind;
        this.items.push(row);
      }
      this.staged = [];
      this.close();
    },

    addExternal() {
      this.items.push({
        uid: nextRowUid(),
        kind: 'external',
        value: '',
        title: '',
        url: '',
        ...this.newRow,
      });
      this.$nextTick(() => {
        const inputs = this.$root.querySelectorAll('[data-external-title]');
        inputs[inputs.length - 1]?.focus();
      });
    },

    removeRow(uid) {
      this.items = this.items.filter((row) => row.uid !== uid);
    },

    serialized() {
      return JSON.stringify(withoutUid(this.items));
    },
  });
}

// config for a table of rows, each with a uid. The rows can be added/removed and serialized to JSON.
function rowTable(config) {
  return {
    name: config.name,
    rows: (config.rows || []).map((row) => ({ uid: nextRowUid(), ...row })),
    blank: config.blank || {},
    columns: config.columns || [],
    presets: config.presets || {},
    addLabel: config.addLabel || 'Add row',
    emptyText: config.emptyText || 'Nothing added yet.',
    maxRows: config.maxRows || 30,

    add() {
      if (this.rows.length >= this.maxRows) return;
      this.rows.push({ uid: nextRowUid(), ...this.blank });
      this.$nextTick(() => {
        const lastRow = this.$root.querySelector('tbody tr:last-child');
        lastRow?.querySelector('input, select')?.focus();
      });
    },

    remove(uid) {
      this.rows = this.rows.filter((row) => row.uid !== uid);
    },

    serialized() {
      return JSON.stringify(withoutUid(this.rows));
    },

    presetIcon(kind) {
      return (this.presets[kind] || this.presets.other || {}).icon || 'bi-link-45deg';
    },

    // after url is entered, try to guess the preset kind based on the domain
    guessPreset(row) {
      if (!row.url || !('kind' in row)) return;
      if (row.kind && !['website', 'other'].includes(row.kind)) return;
      let host;
      try {
        host = new URL(row.url.includes('://') ? row.url : `https://${row.url}`).hostname.replace(/^www\./, '');
      } catch {
        return;
      }
      for (const [key, preset] of Object.entries(this.presets)) {
        if ((preset.domains || []).some((domain) => host === domain || host.endsWith(`.${domain}`))) {
          row.kind = key;
          return;
        }
      }
    },
  };
}
