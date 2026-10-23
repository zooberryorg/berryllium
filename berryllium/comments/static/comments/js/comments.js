document.addEventListener('commentPosted', (event) => {
    const id = event.detail && event.detail.id;
    // wait for htmx to finish swapping the new markup in
    setTimeout(() => {
        const card = document.getElementById('comment-' + id);
        if (!card) return;
        card.scrollIntoView({ behavior: 'smooth', block: 'center' });
        card.classList.add('comment-flash');
        setTimeout(() => card.classList.remove('comment-flash'), 2000);
    }, 100);
});
