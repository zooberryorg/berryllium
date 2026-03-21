function textFieldExpand() {
    return {
        focused: false, // textfield is focused

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