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

        trimDisplayedContent() {
            if (this.content.length > trimLen) {
                return this.content.slice(0, trimLen) + "...";
            } else {
                return this.content;
            }
        },

        updateTrimLength(elwidth) {
            // average width of a character in pixels
            const avgCharWidth = 8;
            this.trimLen = Math.floor(elwidth / avgCharWidth);
            console.log("Updated trim length to: " + this.trimLen);
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
            const visibility = event.type === 'dragstart' ? 'hidden' : 'visible';
            for (const child of currentElement.children) {
                child.style.visibility = visibility;
            }
            if (event.type === 'dragstart') {
                currentElement.classList.add('bg-gray-200/50', 'border-gray-400/50', 'pointer-events-none');
            } else {
                currentElement.classList.remove('bg-gray-200/50', 'border-gray-400/50', 'pointer-events-none');
            }
        },

        isNeighboring(targetId, draggedId) {
            if (targetId === draggedId) return true;

            const draggedRow = document.getElementById(`file-row-${draggedId}`);
            const targetDropZone = document.getElementById(`file-drop-target-${targetId}`);
            if (!draggedRow || !targetDropZone) return false;

            return draggedRow.nextElementSibling === targetDropZone;
        },

        onDragStart(event, fileId) {
            Alpine.store('dnd').isDragging = true;
            Alpine.store('dnd').draggedId = fileId;
            event.dataTransfer.effectAllowed = 'move';
            event.dataTransfer.setData('text/plain', String(fileId));
            const currentElement = event.currentTarget;

            // ghost customization
            const ghost = currentElement.cloneNode(true);
            ghost.style.position = 'fixed';
            ghost.style.top = '100px';
            ghost.style.left = '100px';
            ghost.style.opacity = '1.0';
            ghost.style.width = currentElement.offsetWidth + 'px';
            ghost.classList.add('cursor-grabbing');
            ghost.classList.add('w-full');
            ghost.style.zIndex = '9999';
            document.body.appendChild(ghost);
            event.dataTransfer.setDragImage(ghost, ghost.offsetWidth / 2, 20);

            setTimeout(() => {
                this.updateCurrentElementVisibility(event, currentElement);
            }, 0);
        },

        onDragOver(event) {
            event.preventDefault();
            event.dataTransfer.dropEffect = 'move';
        },

        onDragEnd(event) {
            this.isDragging = false;
            this.target = null;
            Alpine.store('dnd').isDragging = false;
            Alpine.store('dnd').draggedId = null;

            this.updateCurrentElementVisibility(event, event.currentTarget);
        },

        handleFileDrop(event, targetId) {
            event.preventDefault();
            const draggedId = Alpine.store('dnd').draggedId;
        }
    }
}