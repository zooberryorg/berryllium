function exploreClearFilter(name, value) {
    const form = document.getElementById('explore-filters');
    if (!form) return;
    window.dispatchEvent(new CustomEvent('explore-clear', { detail: { name: name || '', value: value || '' } }));
    // pickers and dropdowns (hidden inputs) clear themselves on this event
    const controls = Array.from(form.elements).filter(
        (el) => el.name && el.type !== 'hidden' && (!name || el.name === name)
    );            
    for (const el of controls) {
        if (el.type === 'radio') {
            if (el.value === '' && !el.checked) {
                el.checked = true;
                el.dispatchEvent(new Event('change', { bubbles: true }));
            }
        } else if (el.type === 'checkbox') {
            if (el.checked && (value === undefined || value === '' || el.value === value)) {
                el.checked = false;
                el.dispatchEvent(new Event('change', { bubbles: true }));
            }
        } else if (el.value !== '') {
            // text search: an input event updates x-model and the search trigger
            el.value = '';
            el.dispatchEvent(new Event('input', { bubbles: true }));
        }
    }
}
