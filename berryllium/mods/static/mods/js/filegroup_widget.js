function textFieldExpand({ trimLen = 20, content = "" }) {
    return {
        focused: false, // textfield is focused
        content: content, // textfield content

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
        }
        
    }
}

function toggleGroupManager({ toggled = false }) {
    return {
        toggled,
    }
}