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
