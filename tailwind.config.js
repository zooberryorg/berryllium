// tailwind.config.js
export default {
  content: [
    "./templates/**/*.html",          // project-level templates
    "./**/templates/**/*.html",       // all app templates
    "./**/*.py",                      // for class names in Python
    "./**/*.js",                      // JS that contains class strings
  ],
  theme: {
    extend: {},
  },
  plugins: [],
};
