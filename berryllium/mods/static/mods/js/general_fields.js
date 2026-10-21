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
    mode: 'now',
    timeZone: Intl.DateTimeFormat().resolvedOptions().timeZone,
    picker: null,

    init() {
      const prefs = datePreferences();
      const iso = this.$refs.publishValue.value;
      const saved = iso ? new Date(iso) : null;
      const hasFutureDate = saved && !isNaN(saved) && saved.getTime() > Date.now() + 60 * 1000;
      this.mode = hasFutureDate ? 'schedule' : 'now';

      this.$refs.display.placeholder = prefs.datetime_placeholder;
      this.picker = flatpickr(this.$refs.display, {
        enableTime: true,
        time_24hr: prefs.time_24hr,
        dateFormat: prefs.picker_datetime,
        defaultDate: hasFutureDate ? saved : this.nextHour(),
        minDate: 'today',
        allowInput: true,
        disableMobile: true, // keep the chosen format on phones too
        locale: { firstDayOfWeek: prefs.week_start },
        onChange: (dates) => {
          if (this.mode === 'schedule' && dates[0]) this.sync(dates[0]);
        },
      });

      this.sync(hasFutureDate ? saved : new Date());
    },

    destroy() {
      this.picker?.destroy();
    },

    nextHour() {
      const date = new Date();
      date.setHours(date.getHours() + 1, 0, 0, 0);
      return date;
    },

    sync(date) {
      this.$refs.publishValue.value = date.toISOString();
    },

    publishOnFinish() {
      this.mode = 'now';
      this.sync(new Date());
    },

    schedule() {
      this.mode = 'schedule';
      const date = this.picker.selectedDates[0] || this.nextHour();
      this.picker.setDate(date, false);
      this.sync(date);
      this.$nextTick(() => this.picker.open());
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

//logo picker with a square, cropped live preview.
function logoPicker({ initialUrl = '' }) {
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