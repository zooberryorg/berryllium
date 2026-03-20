function fileGroups({ toggled = false }) {
    return {
        toggled: toggled, // default state for group mgr toggle
        focused: false, // textfield is focused

        expand() {
            this.focused = true;
        },

        collapse() {
            this.focused = false;
        }
        
    }
}