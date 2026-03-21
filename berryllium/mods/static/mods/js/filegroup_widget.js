function textFieldExpand({ trimLen = 20 }) {
    return {
        focused: false, // textfield is focused
        content: "", // textfield content

        expand() {
            this.focused = true;
        },

        collapse() {
            this.focused = false;
        },

        trimDisplayedContent() {
            if (this.content.length > trimLen) {
                return this.content.slice(0, trimLen) + "...";
            }
        }
        
    }
}

function toggleGroupManager({ toggled = false }) {
    return {
        toggled,
    }
}