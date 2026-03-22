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
    updateCurrentElementVisibility(event) {
        const currentElement = event.currentTarget;
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
    
    onDragStart(event, fileId) {
        Alpine.store('dnd').isDragging = true;
        Alpine.store('dnd').draggedId = fileId;
        event.dataTransfer.effectAllowed = 'move';
        event.dataTransfer.setData('text/plain', String(fileId));
        setTimeout(() => {
            this.updateCurrentElementVisibility(event);     
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

            this.updateCurrentElementVisibility(event);
        },

        handleFileDrop(event, targetId) {
            event.preventDefault();
            const draggedId = Alpine.store('dnd').draggedId;
        }
    }
}