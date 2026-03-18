

def init_context(current_index, form):
    """
    Initializes the multi-step form context with navigation information and progress.
    """
    context = {
        "form": form,
    }
    progress_bar = generate_progress_bar(current_index, total_steps=len(NAVIGATION))

    return context | progress_bar

def generate_progress_bar(current_index, total_steps):
    """
    Generates progress bar data for the upload steps.
    """

    title = f"Step {current_index + 1} of {total_steps}: {NAVIGATION[current_index]['name']}"

    completed_range = list(range(current_index + 1))
    remaining_range = list(range(current_index + 1, total_steps))

    return {
        "title": title,
        "completed": completed_range,
        "remaining": remaining_range,
        "total_steps": total_steps,
    }

