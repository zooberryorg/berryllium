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

        init() {
            this.updateTrimLength(this.ref.offsetWidth);
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
        isDragging: false,

        onDragStart(event) {
            this.isDragging = true;
            event.dataTransfer.effectAllowed = 'move';
            // for firefox compatibility
            event.dataTransfer.setData('text/html', 'event.target.outerHTML');
        }
    }
}