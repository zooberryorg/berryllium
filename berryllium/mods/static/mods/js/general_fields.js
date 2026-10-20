function datePreferences() {
  const defaults = {
    picker_date: 'd/m/Y',
    picker_datetime: 'd/m/Y H:i',
    time_24hr: true,
    week_start: 1,
    date_placeholder: 'DD/MM/YYYY',
    datetime_placeholder: 'DD/MM/YYYY HH:MM',
  };
  try {
    const element = document.getElementById('date-preferences');
    return { ...defaults, ...JSON.parse(element.textContent) };
  } catch {
    return defaults;
  }
}


function publishDatePicker() {
  return {
    timeZone: Intl.DateTimeFormat().resolvedOptions().timeZone,
    picker: null,

    init() {
      const prefs = datePreferences();
      const iso = this.$refs.publishValue.value;
      let initial = iso ? new Date(iso) : new Date();
      if (isNaN(initial)) initial = new Date();

      this.$refs.display.placeholder = prefs.datetime_placeholder;
      this.picker = flatpickr(this.$refs.display, {
        enableTime: true,
        time_24hr: prefs.time_24hr,
        dateFormat: prefs.picker_datetime,
        defaultDate: initial,
        allowInput: true,
        disableMobile: true, // keep the chosen format on phones too
        locale: { firstDayOfWeek: prefs.week_start },
        onChange: (dates) => this.sync(dates[0]),
      });
      this.sync(initial);
    },

    destroy() {
      this.picker?.destroy();
    },

    sync(date) {
      if (date) this.$refs.publishValue.value = date.toISOString();
    },

    setNow() {
      const now = new Date();
      this.picker.setDate(now, false);
      this.sync(now);
    },
  };
}

function datePicker({ max = null } = {}) {
  return {
    picker: null,

    init() {
      const prefs = datePreferences();
      this.$el.placeholder = prefs.date_placeholder;
      this.picker = flatpickr(this.$el, {
        dateFormat: 'Y-m-d',          // submitted value
        altInput: true,               // visible input
        altFormat: prefs.picker_date,
        allowInput: true,
        maxDate: max || undefined,
        disableMobile: true,
        locale: { firstDayOfWeek: prefs.week_start },
      });
    },

    destroy() {
      this.picker?.destroy();
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