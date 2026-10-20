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

// shared sortable behavior
function sortableList(listKey, sortable) {
  return {
    sortable,
    dragging: false,
    renderVersion: 0,

    rowKey(row) {
      return `${row.uid}:${this.renderVersion}`;
    },

    moveRow(uid, position) {
      const rows = [...this[listKey]];
      const from = rows.findIndex((row) => row.uid === uid);
      if (from === -1 || from === position) return;
      const [moved] = rows.splice(from, 1);
      rows.splice(position, 0, moved);
      this[listKey] = rows;
      this.renderVersion += 1;
    },
  };
}


// config ontop of searchPicker. What this does is
// it adds a context field for each inserted search result and lets
// user add a new row not in db
function detailPicker(config) {
  return extendComponent(
    extendComponent(searchPicker(config), sortableList('items', !!config.sortable)),
    {
      newRow: config.newRow || {},
      insertKind: config.insertKind || null,
      allowExternal: !!config.allowExternal,
      externalLabel: config.externalLabel || 'Add manually',
      searchLabel: config.searchLabel || config.title || 'Search',
      contextPlaceholder: config.contextPlaceholder || 'Context',
      showVersion: !!config.showVersion,
      emptyListText: config.emptyListText || 'Nothing added yet.',

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
        this.items.push({ uid: nextRowUid(), kind: 'external', value: '', title: '', url: '', ...this.newRow });
        this.$nextTick(() => {
          const inputs = this.$root.querySelectorAll('[data-first-input]');
          inputs[inputs.length - 1]?.focus();
        });
      },

      removeRow(uid) {
        this.items = this.items.filter((row) => row.uid !== uid);
      },

      serialized() {
        return JSON.stringify(withoutUid(this.items));
      },
    }
  );
}

// config for a table of rows, each with a uid. The rows can be added/removed and serialized to JSON.
function rowTable(config) {
  return extendComponent(sortableList('rows', !!config.sortable), {
    name: config.name,
    rows: (config.rows || []).map((row) => ({ uid: nextRowUid(), ...row })),
    blank: config.blank || {},
    presets: config.presets || {},
    addLabel: config.addLabel || 'Add row',
    emptyText: config.emptyText || 'Nothing added yet.',
    maxRows: config.maxRows || 30,

    add() {
      if (this.rows.length >= this.maxRows) return;
      this.rows.push({ uid: nextRowUid(), ...this.blank });
      this.$nextTick(() => {
        const inputs = this.$root.querySelectorAll('[data-first-input]');
        inputs[inputs.length - 1]?.focus();
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

    /** After a URL is typed, pick the matching preset (e.g. discord.gg -> Discord) if none was chosen. */
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
  });
}
