function textFieldExpand({ trimLen = 0, content = "", ref = null }) {
    return {
        focused: false, // textfield is focused
        content: content, // textfield content
        trimLen: trimLen, // number of characters to show when not focused
        ref: ref,

        expand() {
            this.focused = true;
        },

        collapse() {
            this.focused = false;
        },
    }
}

function toggleGroupManager({ toggled = false }) {
    return {
        toggled,
    }
}

function fileDragAndDrop() {
    return {
        updateCurrentElementVisibility(event, el = null) {
            console.log("Updating visibility for element: ", el);
            const currentElement = el || event.currentTarget;

            for (const child of currentElement.children) {
                child.classList.add('text-gold-400/50', 'border-gold-400/50', 'cursor-grabbing');
            }
            
            if (event.type === 'dragstart') {
                currentElement.classList.add('text-gold-400/50', 'border-gold-400/50', 'cursor-grabbing');
            } else {
                currentElement.classList.remove('text-gold-400/50', 'border-gold-400/50', 'cursor-grabbing');
            }
        },

        onDragStart(event, fileId) {
            Alpine.store('dnd').isDragging = true;
            Alpine.store('dnd').draggedFileId = fileId;
            event.dataTransfer.effectAllowed = 'move';
            event.dataTransfer.setData('text/plain', String(fileId));
            const currentElement = event.currentTarget;

            // ghost customization (default class="sortable-ghost" with opacity: 0.5)
            // select based on class
            this.updateCurrentElementVisibility(event, currentElement);
        },

        onDragOver(event) {
            event.preventDefault();
            event.dataTransfer.dropEffect = 'move';
        },

        onDragEnd(event) {
            this.isDragging = false;
            this.target = null;
            Alpine.store('dnd').isDragging = false;
            Alpine.store('dnd').draggedFileId = null;

            this.updateCurrentElementVisibility(event, event.currentTarget);
        },

        handleFileDrop(event, targetId) {
            event.preventDefault();
            const draggedFileId = Alpine.store('dnd').draggedFileId;
        }
    }
}