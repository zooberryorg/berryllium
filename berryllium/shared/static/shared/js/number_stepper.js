(function () {
    const CHEVRON = {
        1: '<svg viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="2.25" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M4 10l4-4 4 4"/></svg>',
        '-1': '<svg viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="2.25" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M4 6l4 4 4-4"/></svg>',
    };
    function step(input, direction) {
        if (input.disabled || input.readOnly) return;
        if (input.value === '') input.value = input.min !== '' ? input.min : 0;
        else if (direction > 0) input.stepUp(); else input.stepDown();
        input.dispatchEvent(new Event('input', { bubbles: true }));
        input.dispatchEvent(new Event('change', { bubbles: true }));
        update(input);
    }

    function update(input) {
        const wrapper = input.parentElement;
        const value = parseFloat(input.value);
        wrapper.querySelector('[data-step="-1"]').disabled = input.min !== '' && !isNaN(value) && value <= parseFloat(input.min);
        wrapper.querySelector('[data-step="1"]').disabled = input.max !== '' && !isNaN(value) && value >= parseFloat(input.max);
    }

    function button(input, direction) {
        const el = document.createElement('button');
        el.type = 'button';
        el.className = 'zb-stepper-button';
        el.dataset.step = String(direction);
        el.setAttribute('aria-label', direction > 0 ? 'Increase' : 'Decrease');
        el.tabIndex = -1;
        el.innerHTML = CHEVRON[direction];
        el.addEventListener('click', () => step(input, direction));
        return el;
    }

    function enhance(root) {
        root.querySelectorAll('input[type="number"]:not([data-no-stepper])').forEach((input) => {
            if (input.parentElement.classList.contains('zb-stepper')) return;
            const wrapper = document.createElement('span');
            wrapper.className = 'zb-stepper';
            [...input.classList].filter((c) => /^(sm:|md:|lg:)?w-/.test(c)).forEach((c) => wrapper.classList.add(c));
            const arrows = document.createElement('span');
            arrows.className = 'zb-stepper-arrows';
            arrows.append(button(input, 1), button(input, -1));
            input.parentNode.insertBefore(wrapper, input);
            wrapper.append(input, arrows);
            input.addEventListener('input', () => update(input));
            update(input);
        });
    }

    document.addEventListener('DOMContentLoaded', () => enhance(document));
    document.addEventListener('htmx:load', (event) => enhance(event.target));
})();
